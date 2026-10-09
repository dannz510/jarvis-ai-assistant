"""Single comprehensive scenario test with coder:7b."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Brain.agent_loop import ReActAgent, AgentJournal

WORK = tempfile.mkdtemp(prefix="astra_final_")
os.chdir(WORK)
journal = AgentJournal(db_path=os.path.join(WORK, "journal.sqlite3"))

goal = (
    "Create a file named final_report.txt with 3 bullet points about ASTRA, "
    "then use a shell command to list all files in the current directory, "
    "then read the file back to verify."
)

print(f"Goal: {goal}", flush=True)
agent = ReActAgent(
    model="qwen2.5-coder:7b",
    journal=journal,
    on_step=lambda e: print(f"  {e.get('type'):12s} {e.get('action', '')} {str(e.get('action_input'))[:80]}", flush=True),
)
summary = agent.run(goal)
print(f"\nRESULT: {summary}", flush=True)
shutil.rmtree(WORK, ignore_errors=True)