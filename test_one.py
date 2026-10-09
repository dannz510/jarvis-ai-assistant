"""Run remaining capability scenarios with coder:7b, one per invocation."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Brain.agent_loop import ReActAgent, AgentJournal

SCENARIOS = {
    "FILE EDIT": "Create a file named config.txt with the line 'version=1', then edit it to change 'version=1' to 'version=2', then read it back to confirm.",
    "OS CONTROL": "List all files and folders in the current directory using a shell command, then tell me how many files are there.",
    "WEB SEARCH": "Search the web for what Ollama is, then write a 3-sentence summary into ollama_summary.txt, then read it back.",
    "DATA COLLECTION": "Use fetch_url to read https://example.com and tell me the main heading text found on that page.",
    "APP INTERACTION": "List the running processes on this Windows machine using a shell command and count how many are running.",
}
name = sys.argv[1]
goal = SCENARIOS[name]
WORK = tempfile.mkdtemp(prefix="astra_cap_")
os.chdir(WORK)
journal = AgentJournal(db_path=os.path.join(WORK, "journal.sqlite3"))
agent = ReActAgent(
    model="qwen2.5-coder:7b",
    journal=journal,
    on_step=lambda e: print(f"  {e.get('type'):12s} {e.get('action', '')}", flush=True),
)
summary = agent.run(goal)
print(f"\nRESULT: {summary}")
shutil.rmtree(WORK, ignore_errors=True)