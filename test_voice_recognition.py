"""Test voice recognition pipeline."""
import threading
import time
import os

from NetHyTechSTT.listen import listen

clear_file = lambda: None
INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.txt")

if os.path.exists(INPUT_FILE):
    os.remove(INPUT_FILE)

stop_event = threading.Event()

def run_listener():
    try:
        listen(stop_event=stop_event)
    except Exception as e:
        print(f"Listener error: {e}")
        stop_event.set()

t = threading.Thread(target=run_listener, daemon=True)
t.start()

print("Listening for 5 seconds... Speak now!")
time.sleep(5)
stop_event.set()
t.join(timeout=2)

if os.path.exists(INPUT_FILE):
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    print(f"Recognized: '{content}'")
else:
    print("No input.txt created")