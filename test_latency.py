"""Quick latency test for the ASTRA runtime."""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis_runtime import get_runtime

def test_model(model, prompt="Xin chao, ban ten gi?"):
    print(f"\n=== Testing model: {model} ===")
    r = get_runtime()
    start = time.time()
    result = r.ask_full(prompt, model=model, agent="simple", tools=[])
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Content: {result.get('content', '')[:300]}")
    if "error" in result:
        print(f"Error: {result['error']}")
    return elapsed

if __name__ == "__main__":
    test_model("qwen2.5:1.5b")
    test_model("qwen2.5:1.5b", "Gio cua hien tai la gi?")