"""Fast capability test using qwen2.5:1.5b (fast model)."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Brain.agent_loop import ReActAgent, AgentJournal

SCENARIOS = [
    ("FILE", "Create a file named test_marker.txt with the line 'ASTRA works', then read it back to verify."),
    ("CMD", "List the files in the current directory using a shell command, then count how many files there are."),
    ("WEB", "Search the web for what Ollama is, then write a 2-sentence summary into ollama_summary.txt, then read it back."),
]

WORK = tempfile.mkdtemp(prefix="astra_fast_")
os.chdir(WORK)
journal = AgentJournal(db_path=os.path.join(WORK, "journal.sqlite3"))
passed = 0
failed = 0

for name, goal in SCENARIOS:
    print(f"\n[{name}] {goal}", flush=True)
    agent = ReActAgent(
        model="qwen2.5:1.5b",
        journal=journal,
        on_step=lambda e, n=name: print(f"  {e.get('type'):12s} {e.get('action', '')}", flush=True),
    )
    try:
        summary = agent.run(goal)
        print(f"  RESULT: {summary[:300]}", flush=True)
        passed += 1
    except Exception as exc:
        print(f"  FAILED: {exc}", flush=True)
        failed += 1

print(f"\nSUMMARY: {passed} passed, {failed} failed", flush=True)
shutil.rmtree(WORK, ignore_errors=True)