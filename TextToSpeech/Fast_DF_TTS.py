"""Local-first Text-to-Speech engine.

Primary path uses Windows SAPI through COM and works offline.
Fallback to pyttsx3 if COM fails.
Remote StreamElements voice can optionally be enabled by setting
ASTRA_TTS_REMOTE=1, but only when an internet connection is confirmed.
"""

import os
import time
import threading
import queue
import logging
from typing import Union

from Brain.logger import logger

_speech_queue = queue.Queue(maxsize=8)
_speaking = threading.Event()
_cancel_speech = threading.Event()
_speaker_lock = threading.RLock()
_current_speaker = None
_worker_thread = None

# Remote TTS is opt-in to keep latency low by default.
REMOTE_TTS_ENABLED = os.environ.get("ASTRA_TTS_REMOTE", "0") == "1"

# Preferred voice order (case-insensitive substrings)
VOICE_PREFERENCE = [
    "david",     # Microsoft David - clear male
    "mark",      # Microsoft Mark
    "zira",      # Microsoft Zira - female fallback
    "hazel",     # Microsoft Hazel
]


def _speak_offline_com(message: str, voice_rate: int = 0) -> bool:
    """Speak locally through Windows SAPI COM. Returns True on success."""
    global _current_speaker
    pythoncom = None
    speaker = None
    try:
        import pythoncom as com_runtime
        import comtypes.client

        pythoncom = com_runtime
        pythoncom.CoInitialize()
        speaker = comtypes.client.CreateObject("SAPI.SpVoice")
        speaker.Volume = 100
        speaker.Rate = max(-10, min(10, int(voice_rate)))

        # Select preferred voice
        tokens = speaker.GetVoices()
        voices = [tokens.Item(index) for index in range(tokens.Count)]
        selected = None

        # Check env override first
        requested = os.environ.get("ASTRA_SAPI_VOICE", "").strip().casefold()
        if requested:
            selected = next(
                (v for v in voices if requested in (v.GetDescription() + " " + v.Id).casefold()),
                None,
            )

        # Try preferred voices
        if selected is None:
            for marker in VOICE_PREFERENCE:
                selected = next(
                    (v for v in voices if marker in (v.GetDescription() + " " + v.Id).casefold()),
                    None,
                )
                if selected:
                    break

        # Fallback to first available
        if selected is None and voices:
            selected = voices[0]

        if selected is not None:
            speaker.Voice = selected
            logger.info(f"TTS using voice: {selected.GetDescription()}")
        else:
            logger.warning("TTS: No SAPI voices available")
            return False

        with _speaker_lock:
            _current_speaker = speaker

        # Speak synchronously (flag 0 = SVSFDefault = synchronous)
        speaker.Speak(str(message), 0)

        return True

    except Exception as exc:
        logger.error(f"COM TTS Error: {exc}")
        return False

    finally:
        with _speaker_lock:
            if _current_speaker is speaker:
                _current_speaker = None
        if speaker is not None:
            try:
                speaker.Speak("", 3)  # SVSFPurgeBeforeSpeak
            except Exception:
                pass
        if pythoncom is not None:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def _speak_offline_pyttsx3(message: str, voice_rate: int = 175) -> bool:
    """Fallback to pyttsx3 if COM fails."""
    try:
        import pyttsx3

        engine = pyttsx3.init("sapi5")
        engine.setProperty("rate", max(50, min(300, int(voice_rate))))
        engine.setProperty("volume", 1.0)

        # Try to find a good voice
        voices = engine.getProperty("voices")
        selected = None
        for marker in VOICE_PREFERENCE:
            selected = next(
                (v for v in voices if marker in (v.name + " " + v.id).casefold()),
                None,
            )
            if selected:
                break

        if selected:
            engine.setProperty("voice", selected.id)
            logger.info(f"TTS (pyttsx3) using voice: {selected.name}")

        engine.say(str(message))
        engine.runAndWait()
        engine.stop()
        return True

    except Exception as exc:
        logger.error(f"pyttsx3 TTS Error: {exc}")
        return False


def _speak_offline(message: str, voice_rate: int = 0):
    """Speak locally with COM first, fallback to pyttsx3."""
    logger.info(f"Speaking: {message[:80]}{'...' if len(message) > 80 else ''}")

    # Try COM SAPI first (more reliable on Windows)
    if _speak_offline_com(message, voice_rate):
        return

    # Fallback to pyttsx3
    logger.warning("COM TTS failed, falling back to pyttsx3")
    _speak_offline_pyttsx3(message, voice_rate)


def _generate_remote_audio(message: str, voice: str = "Matthew") -> bytes | None:
    """Fetch audio from StreamElements. Returns None on failure."""
    import requests

    url = f"https://api.streamelements.com/kappa/v2/speech?voice={voice}&text={message}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        result = requests.get(url=url, headers=headers, timeout=8)
        if result.status_code == 200:
            return result.content
        logger.warning(f"Remote TTS HTTP {result.status_code}")
        return None
    except Exception as exc:
        logger.error(f"Remote TTS Error: {exc}")
        return None


def _play_audio_file(file_path: str):
    """Play an MP3 file via pygame and clean up afterwards."""
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not _cancel_speech.is_set():
            time.sleep(0.02)
        if _cancel_speech.is_set():
            pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception as exc:
        logger.error(f"Playback error: {exc}")
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


def _speak_remote(message: str, voice: str = "Matthew"):
    """Play a remote TTS voice. Falls back to local if unavailable."""
    content = _generate_remote_audio(message, voice)
    if _cancel_speech.is_set():
        return
    if not content:
        _speak_offline(message)
        return
    file_path = os.path.join(os.getcwd(), f"temp_tts_{int(time.time() * 1000)}.mp3")
    try:
        with open(file_path, "wb") as file:
            file.write(content)
        _play_audio_file(file_path)
    except Exception as exc:
        logger.error(f"Remote TTS playback error: {exc}")
        _speak_offline(message)


def _speech_worker():
    """Background worker that processes the speech queue."""
    while True:
        message = _speech_queue.get()
        if message is None:
            return
        _cancel_speech.clear()
        _speaking.set()
        try:
            if REMOTE_TTS_ENABLED:
                _speak_remote(message)
            else:
                _speak_offline(message)
        finally:
            _speaking.clear()
            _speech_queue.task_done()


# Start background speech worker
_worker_thread = threading.Thread(target=_speech_worker, name="astra-tts", daemon=True)
_worker_thread.start()


def is_speaking() -> bool:
    """Check if TTS is currently speaking."""
    return _speaking.is_set()


def stop_speaking():
    """Cancel current speech and discard stale queued replies after barge-in."""
    import os
    _cancel_speech.set()
    while True:
        try:
            _speech_queue.get_nowait()
        except queue.Empty:
            break
        else:
            _speech_queue.task_done()
    try:
        import pygame
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass


def Co_speak(message: str, voice: str = "Matthew", folder: str = "") -> Union[None, str]:
    """Speak the message using the fastest available method (synchronous)."""
    if not message:
        return None
    if REMOTE_TTS_ENABLED:
        _speak_remote(message, voice)
    else:
        _speak_offline(message)
    return None


def speak(text):
    """Queue speech without blocking the voice listener or UI."""
    if not text:
        return
    logger.info(f"Speaking: {text}")
    try:
        _speech_queue.put_nowait(str(text))
    except queue.Full:
        logger.warning("TTS queue full; skipped speech.")


if __name__ == "__main__":
    import sys
    speak(" ".join(sys.argv[1:]) or "Text to speech test.")
    # Wait for speech to finish
    while is_speaking():
        time.sleep(0.1)