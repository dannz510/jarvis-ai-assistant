"""Run all capability scenarios with the coder model, sequentially."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Brain.agent_loop import ReActAgent, AgentJournal

SCENARIOS = [
    ("FILE OPS", "Create a file named report_notes.md with 3 bullet points about ASTRA, then read it back to verify the content is correct."),
    ("FILE EDIT", "Create a file named config.txt with the line 'version=1', then edit it to change 'version=1' to 'version=2', then read it back to confirm."),
    ("OS CONTROL", "List all files and folders in the current directory using a shell command, then tell me how many files are there."),
    ("WEB SEARCH", "Search the web for what Ollama is, then write a 3-sentence summary into ollama_summary.txt, then read it back."),
    ("DATA COLLECTION", "Use fetch_url to read https://example.com and tell me the main heading text found on that page."),
    ("APP INTERACTION", "List the running processes on this Windows machine using a shell command and count how many are running."),
]

WORK = tempfile.mkdtemp(prefix="astra_cap_all_")
os.chdir(WORK)
journal = AgentJournal(db_path=os.path.join(WORK, "journal.sqlite3"))
passed = 0
failed = 0

for name, goal in SCENARIOS:
    print(f"\n{'='*60}\n[{name}] {goal}\n{'='*60}", flush=True)
    agent = ReActAgent(
        model="qwen2.5-coder:7b",
        journal=journal,
        on_step=lambda e, n=name: print(f"  [{n}] {e.get('type'):12s} {e.get('action', '')}", flush=True),
    )
    try:
        summary = agent.run(goal)
        print(f"  RESULT: {summary[:400]}", flush=True)
        passed += 1
    except Exception as exc:
        print(f"  FAILED: {exc}", flush=True)
        failed += 1

print(f"\n{'='*60}\nSUMMARY: {passed} passed, {failed} failed", flush=True)
shutil.rmtree(WORK, ignore_errors=True)