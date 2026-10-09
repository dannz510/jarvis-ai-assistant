"""Text-based integration test for the full ASTRA pipeline (English)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis_runtime import get_runtime
from TextToSpeech.Fast_DF_TTS import speak

TEST_QUERIES = [
    "Hello ASTRA, how are you today?",
    "What time is it?",
    "Can you open Chrome for me?",
]

def main():
    print("=== ASTRA English Text Pipeline Test ===")
    r = get_runtime()
    
    for query in TEST_QUERIES:
        print(f"\n--- Testing: {query} ---")
        start = time.time()
        result = r.ask_full(query, model="qwen2.5:1.5b", agent="simple", tools=[])
        elapsed = time.time() - start
        response = result.get("content", "")
        print(f"Elapsed: {elapsed:.1f}s")
        print(f"ASTRA: {response}")
        
        if response:
            print("Playing audio...")
            speak(response)
    
    print("\n=== Test complete ===")

if __name__ == "__main__":
    main()