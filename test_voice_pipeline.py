"""Integration test: Vosk STT -> Brain -> pyttsx3 TTS.

Run this, speak into the microphone for ~10 seconds, then see the result.
"""
import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from NetHyTechSTT.listen import Listener, _recog_file
from TextToSpeech.Fast_DF_TTS import speak
from jarvis_runtime import get_runtime

INPUT_FILE = _recog_file
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")

def clear_file():
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.write("")

def main():
    print("=== ASTRA Voice Pipeline Test ===")
    print("Bắt đầu lắng nghe trong 10 giây. Hãy nói something bằng tiếng Việt.")
    
    clear_file()
    
    listener = Listener(INPUT_FILE)
    listener.start()
    
    time.sleep(10)
    
    listener.stop()
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        recognized = f.read().strip()
    
    print(f"\nNhận diện được: '{recognized}'")
    
    if not recognized:
        print("Không nhận diện được gì. Kiểm tra mic.")
        return
    
    print("Đang gọi model...")
    r = get_runtime()
    start = time.time()
    result = r.ask_full(recognized, model="qwen2.5:1.5b", agent="simple", tools=[])
    elapsed = time.time() - start
    print(f"Model mất {elapsed:.1f}s")
    
    response = result.get("content", "")
    print(f"ASTRA: {response}")
    
    print("\nĐang phát âm thanh...")
    speak(response)
    
    print("\n=== Test hoàn thành ===")

if __name__ == "__main__":
    main()