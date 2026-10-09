"""Durable multi-step planner with execution journaling and rollback support.

Decomposes complex user intents into ordered steps, executes them through the
tool registry, and maintains a persistent journal so execution can resume
after interruptions.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from Brain.logger import get_logger
from Brain.tool_registry import ToolRegistry, create_default_registry

logger = get_logger(__name__)


@dataclass
class PlanStep:
    id: int
    tool: str
    description: str
    params: dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None


@dataclass
class ExecutionJournal:
    task_id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "running"  # running, completed, failed, paused
    context: dict = field(default_factory=dict)


class MultistepPlanner:
    """Plan → Execute → Observe → Verify loop with durable journaling."""

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        journal_path: Optional[str] = None,
        max_retries: int = 2,
    ):
        self.registry = tool_registry or create_default_registry()
        self.journal_path = Path(journal_path) if journal_path else None
        self.max_retries = max(0, int(max_retries))
        self._current_journal: Optional[ExecutionJournal] = None

    def plan(self, goal: str, context: dict = None) -> list[PlanStep]:
        """Generate a step plan from a high-level goal.

        This is a rule-based planner. In production, this could call an LLM
        to generate more sophisticated plans.
        """
        goal_lower = goal.casefold()
        steps = []

        # Email/Calendar workflows
        if any(kw in goal_lower for kw in ("email", "mail", "thư", "gửi")):
            steps.append(PlanStep(
                id=1, tool="gmail_search", description="Tìm email liên quan",
                params={"query": goal[:100]}
            ))
            steps.append(PlanStep(
                id=2, tool="gmail_read", description="Đọc nội dung email",
                params={}
            ))

        if any(kw in goal_lower for kw in ("lịch", "calendar", "hẹn", "meeting", "họp")):
            steps.append(PlanStep(
                id=len(steps) + 1, tool="calendar_list", description="Kiểm tra lịch",
                params={"max_results": 10}
            ))
            steps.append(PlanStep(
                id=len(steps) + 1, tool="calendar_create", description="Tạo sự kiện mới",
                params={"summary": goal[:80], "start_time": datetime.now().isoformat()}
            ))

        # Document creation
        if any(kw in goal_lower for kw in ("tạo", "create", "viết", "write", "báo cáo", "report")):
            if "doc" in goal_lower or "google doc" in goal_lower:
                steps.append(PlanStep(
                    id=len(steps) + 1, tool="docs_create", description="Tạo Google Doc",
                    params={"title": goal[:80], "content": "Tự động tạo từ: " + goal}
                ))
            elif "sheet" in goal_lower or "excel" in goal_lower:
                steps.append(PlanStep(
                    id=len(steps) + 1, tool="sheets_create", description="Tạo Google Sheet",
                    params={"title": goal[:80], "rows": []}
                ))
            elif "slide" in goal_lower or "powerpoint" in goal_lower or "presentation" in goal_lower:
                steps.append(PlanStep(
                    id=len(steps) + 1, tool="slides_create", description="Tạo Google Slides",
                    params={"title": goal[:80], "content": goal}
                ))

        # File operations
        if any(kw in goal_lower for kw in ("tìm file", "find file", "search file")):
            steps.append(PlanStep(
                id=len(steps) + 1, tool="file_search", description="Tìm file cục bộ",
                params={"query": goal[:100]}
            ))

        # Web research
        if any(kw in goal_lower for kw in ("tìm kiếm", "search", "nghiên cứu", "research")):
            steps.append(PlanStep(
                id=len(steps) + 1, tool="web_search", description="Tìm kiếm web",
                params={"query": goal[:100]}
            ))

        # Default fallback
        if not steps:
            steps.append(PlanStep(
                id=1, tool="native_react", description="Xử lý bằng agent ngôn ngữ",
                params={"prompt": goal}
            ))

        return steps

    def execute(self, goal: str, context: dict = None) -> ExecutionJournal:
        """Execute a goal end-to-end with durable journaling."""
        if self._current_journal and self._current_journal.status == "running":
            logger.warning("Planner busy with existing task")
            return self._current_journal

        task_id = uuid.uuid4().hex[:12]
        steps = self.plan(goal, context or {})
        journal = ExecutionJournal(
            task_id=task_id,
            goal=goal,
            steps=steps,
            context=context or {},
        )
        self._current_journal = journal
        self._save_journal(journal)

        logger.info(f"Planner: Starting task {task_id} - {goal}")

        for step in journal.steps:
            if self._current_journal is not journal:
                break  # Interrupted by new task
            journal.status = "running"
            step.status = "running"
            step.started_at = time.time()
            self._save_journal(journal)
            logger.info(f"  Step {step.id}: {step.description} -> {step.tool}")

            attempt = 0
            while attempt <= self.max_retries:
                try:
                    result = self.registry.execute(step.tool, step.params)
                    if result.get("success"):
                        step.status = "completed"
                        step.result = result.get("result")
                        logger.info(f"    ✓ Step {step.id} completed")
                    else:
                        if result.get("confirmation_required"):
                            step.status = "waiting_confirmation"
                            step.error = "Cần xác nhận từ người dùng"
                            logger.warning(f"    ⚠ Step {step.id} requires confirmation")
                            break
                        else:
                            raise RuntimeError(result.get("error", "Unknown error"))
                    break
                except Exception as exc:
                    attempt += 1
                    if attempt > self.max_retries:
                        step.status = "failed"
                        step.error = str(exc)
                        logger.error(f"    ✗ Step {step.id} failed after {attempt} attempts: {exc}")
                    else:
                        logger.warning(f"    ↻ Step {step.id} retry {attempt}/{self.max_retries}: {exc}")
                        time.sleep(0.5 * attempt)
            step.finished_at = time.time()
            self._save_journal(journal)

        # Final status
        failed = any(s.status == "failed" for s in journal.steps)
        journal.status = "failed" if failed else "completed"
        journal.updated_at = time.time()
        self._save_journal(journal)

        if failed:
            logger.error(f"Planner: Task {task_id} completed with failures")
        else:
            logger.info(f"Planner: Task {task_id} completed successfully")

        return journal

    def resume(self, task_id: str) -> Optional[ExecutionJournal]:
        """Resume a previously interrupted task from its journal."""
        if not self.journal_path:
            return None
        journal_file = self.journal_path / f"journal_{task_id}.json"
        if not journal_file.exists():
            return None

        with open(journal_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        journal = ExecutionJournal(
            task_id=data["task_id"],
            goal=data["goal"],
            steps=[PlanStep(**s) for s in data["steps"]],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            status=data["status"],
            context=data.get("context", {}),
        )
        self._current_journal = journal

        # Resume from first incomplete step
        for step in journal.steps:
            if step.status in ("pending", "running", "waiting_confirmation"):
                journal.status = "running"
                return self.execute(journal.goal, journal.context)

        return journal

    def get_journal(self, task_id: Optional[str] = None) -> Optional[ExecutionJournal]:
        if task_id:
            if self._current_journal and self._current_journal.task_id == task_id:
                return self._current_journal
            if self.journal_path:
                journal_file = self.journal_path / f"journal_{task_id}.json"
                if journal_file.exists():
                    with open(journal_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return ExecutionJournal(
                        task_id=data["task_id"],
                        goal=data["goal"],
                        steps=[PlanStep(**s) for s in data["steps"]],
                        created_at=data["created_at"],
                        updated_at=data["updated_at"],
                        status=data["status"],
                        context=data.get("context", {}),
                    )
        return self._current_journal

    def _save_journal(self, journal: ExecutionJournal):
        if not self.journal_path:
            return
        self.journal_path.mkdir(parents=True, exist_ok=True)
        journal_file = self.journal_path / f"journal_{journal.task_id}.json"
        data = {
            "task_id": journal.task_id,
            "goal": journal.goal,
            "steps": [
                {
                    "id": s.id,
                    "tool": s.tool,
                    "description": s.description,
                    "params": s.params,
                    "status": s.status,
                    "result": s.result,
                    "error": s.error,
                    "started_at": s.started_at,
                    "finished_at": s.finished_at,
                }
                for s in journal.steps
            ],
            "created_at": journal.created_at,
            "updated_at": journal.updated_at,
            "status": journal.status,
            "context": journal.context,
        }
        try:
            with open(self.journal_path / f"journal_{journal.task_id}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning(f"Failed to save journal: {exc}")