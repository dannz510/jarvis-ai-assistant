"""Comprehensive capability test for the ASTRA agent loop.

Covers: file create/open/edit, deep OS control, web search + report,
data collection, and app interaction. Uses the fast 1.5B model.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Brain.agent_loop import ReActAgent, AgentJournal

WORK = tempfile.mkdtemp(prefix="astra_cap_test_")
os.chdir(WORK)

SCENARIOS = [
    (
        "FILE OPS",
        "Create a file named report_notes.md with 3 bullet points about ASTRA, "
        "then read it back to verify the content is correct.",
    ),
    (
        "FILE EDIT",
        "Create a file named config.txt with the line 'version=1', then edit it "
        "to change 'version=1' to 'version=2', then read it back to confirm.",
    ),
    (
        "OS CONTROL",
        "List all files and folders in the current directory using a shell command, "
        "then tell me how many files are there.",
    ),
    (
        "WEB SEARCH + REPORT",
        "Search the web for what Ollama is, then write a 3-sentence summary of what "
        "you found into a file named ollama_summary.txt, then read it back.",
    ),
    (
        "DATA COLLECTION",
        "Use fetch_url to read https://example.com and tell me the main heading "
        "text found on that page.",
    ),
    (
        "APP INTERACTION",
        "List the running processes on this Windows machine using a shell command "
        "and count how many are running.",
    ),
]

journal = AgentJournal(db_path=os.path.join(WORK, "journal.sqlite3"))
passed = 0
failed = 0

for name, goal in SCENARIOS:
    print(f"\n{'='*60}\n[{name}] {goal}\n{'='*60}")
    agent = ReActAgent(
        model="qwen2.5:1.5b",
        journal=journal,
        on_step=lambda e, n=name: print(f"  [{n}] {e.get('type'):12s} {e.get('action', '')}"),
    )
    try:
        summary = agent.run(goal)
        print(f"  RESULT: {summary[:300]}")
        passed += 1
    except Exception as exc:
        print(f"  FAILED: {exc}")
        failed += 1

print(f"\n{'='*60}\nSUMMARY: {passed} passed, {failed} failed")
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(0 if failed == 0 else 1)