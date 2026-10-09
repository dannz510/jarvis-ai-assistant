"""Local offline Speech-to-Text engine using Vosk + PyAudio.

Replaces the previous Selenium + remote-browser approach so that speech
recognition starts in under a second and works without internet access.
"""

import os
import json
import array
import math
import threading
import time
import warnings

warnings.filterwarnings("ignore")

from vosk import Model, KaldiRecognizer
import pyaudio
from Brain.speech_turn import SpeechTurnBuffer
from Brain.voice_activity import VoiceActivityDetector
from Brain.logger import logger

# Resolve model paths relative to the project root.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIETNAMESE_MODEL_PATH = os.path.join(PROJECT_ROOT, "vosk-model-small-vn-0.4")
ENGLISH_MODEL_PATH = os.path.join(PROJECT_ROOT, "vosk-model-small-en-us-0.15")

# Allow override via environment variable.
MODEL_PATH = os.environ.get("ASTRA_VOSK_MODEL", "").strip()

# Audio parameters.
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


def _find_model_path():
    """Prefer English by default; honor explicit model path, then Vietnamese."""
    candidates = ([MODEL_PATH] if MODEL_PATH else []) + [
        ENGLISH_MODEL_PATH,
        VIETNAMESE_MODEL_PATH,
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    return None


def _load_model():
    """Load the Vosk model, downloading guidance if missing."""
    path = _find_model_path()
    if path is None:
        logger.error(
            "Vosk model not found. Download one, e.g.:\n"
            "  python download_vosk_model.py small-vn-0.4\n"
            "  python download_vosk_model.py small-en-us-0.15\n"
            "Place the folder inside the project root."
        )
        return None
    try:
        return Model(path)
    except Exception as exc:
        logger.error(f"Failed to load Vosk model at {path}: {exc}")
        return None


_model = _load_model()


class Listener:
    """Continuous listening thread that writes recognized text to a file."""

    INTERRUPT_PREFIXES = (
        "wait", "stop", "hold on", "no i mean", "i mean", "actually",
        "khoan", "đợi", "dừng", "không ý mình", "ý mình là", "ý tôi là",
    )

    def __init__(self, output_file, on_text=None, stop_event=None, status_callback=None,
                 on_transcript=None, on_audio_level=None, on_speech_activity=None):
        self.output_file = output_file
        self.on_text = on_text
        self.status_callback = status_callback
        self.on_transcript = on_transcript
        self.on_audio_level = on_audio_level
        self.on_speech_activity = on_speech_activity
        self._stop_event = stop_event or threading.Event()
        self._thread = None
        self._turn_buffer = SpeechTurnBuffer()
        self._vad = VoiceActivityDetector(sample_rate=RATE)
        self._speech_active = False
        self._barge_in_active = False

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        # Do not clear a stop request that arrived while this listener was
        # being started on a worker thread.
        if self._stop_event.is_set():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self):
        if _model is None:
            message = "Không tìm thấy model Vosk. Hãy cài model tiếng Việt hoặc tiếng Anh."
            logger.error(message)
            self._report(message, "error")
            return

        audio = None
        stream = None
        try:
            audio = pyaudio.PyAudio()
            device_setting = os.environ.get("ASTRA_MIC_DEVICE", "").strip()
            device_index = int(device_setting) if device_setting else None
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=device_index,
            )
            recognizer = KaldiRecognizer(_model, RATE)
            recognizer.SetWords(False)
            self._report("Micro đã kết nối · ASTRA đang lắng nghe", "listening")

            while not self._stop_event.is_set():
                data = stream.read(CHUNK, exception_on_overflow=False)
                self._report_audio_level(self._measure_level(data))
                self._report_speech_activity(self._vad.process(data))
                try:
                    from TextToSpeech.Fast_DF_TTS import is_speaking, stop_speaking
                    speaking = is_speaking()
                except Exception:
                    speaking = False
                    stop_speaking = lambda: None

                now = time.monotonic()
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    recognized = result.get("text", "").strip()
                    if recognized:
                        if speaking and not self._barge_in_active:
                            if self._is_interrupt(recognized):
                                stop_speaking()
                                self._barge_in_active = True
                                preview = self._turn_buffer.add_final(recognized, now)
                                recognizer.Reset()
                                self._report_transcript(preview, self._turn_buffer.confirmed_transcript)
                            else:
                                recognizer.Reset()
                        else:
                            preview = self._turn_buffer.add_final(recognized, now)
                            self._report_transcript(preview, self._turn_buffer.confirmed_transcript)
                else:
                    partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                    if partial:
                        if speaking and not self._barge_in_active:
                            if self._is_interrupt(partial):
                                stop_speaking()
                                self._barge_in_active = True
                                preview = self._turn_buffer.add_final(partial, now)
                                recognizer.Reset()
                                self._report_transcript(preview, self._turn_buffer.confirmed_transcript)
                        else:
                            self._turn_buffer.update_partial(partial)
                            self._report_transcript(
                                self._turn_buffer.preview,
                                self._turn_buffer.confirmed_transcript,
                            )

                if self._turn_buffer.should_finalize(now, speech_active=self._speech_active):
                    recognized = self._turn_buffer.consume()
                    self._emit(recognized)
                    self._barge_in_active = False
                    self._report_transcript("", "")
        except Exception as exc:
            if not self._stop_event.is_set():
                message = f"Không thể chạy nhận dạng giọng nói: {exc}"
                logger.error(message)
                self._report(message, "error")
        finally:
            pending = self._turn_buffer.consume()
            if pending:
                self._emit(pending)
                self._report_transcript("", "")
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if audio is not None:
                audio.terminate()

    def _report(self, message, mode):
        if self.status_callback:
            try:
                self.status_callback(message, mode)
            except Exception:
                pass

    @classmethod
    def _is_interrupt(cls, text):
        normalized = " ".join(str(text or "").casefold().strip().split())
        return any(normalized.startswith(prefix) for prefix in cls.INTERRUPT_PREFIXES)

    def _report_transcript(self, preview, confirmed):
        if self.on_transcript:
            try:
                self.on_transcript(preview, confirmed)
            except Exception:
                pass

    @staticmethod
    def _measure_level(data):
        samples = array.array("h")
        samples.frombytes(data)
        if not samples:
            return 0.0
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        return max(0.0, min(1.0, rms / 7000.0))

    def _report_audio_level(self, value):
        if self.on_audio_level:
            try:
                self.on_audio_level(value)
            except Exception:
                pass

    def _report_speech_activity(self, active):
        active = bool(active)
        if active == self._speech_active:
            return
        self._speech_active = active
        if self.on_speech_activity:
            try:
                self.on_speech_activity(active)
            except Exception:
                pass

    def _emit(self, text, partial=False):
        if not text:
            return
        try:
            with open(self.output_file, "w", encoding="utf-8") as file:
                file.write(text.lower())
        except OSError:
            pass
        if self.on_text:
            try:
                self.on_text(text, partial)
            except Exception:
                pass


_recog_file = os.path.join(PROJECT_ROOT, "input.txt")
_listener = None


def listen(output_file=None, on_text=None, stop_event=None, status_callback=None,
           on_transcript=None, on_audio_level=None, on_speech_activity=None):
    """Block until interrupted; continuously transcribe microphone input."""
    global _listener
    output_file = output_file or _recog_file
    _listener = Listener(
        output_file,
        on_text=on_text,
        stop_event=stop_event,
        status_callback=status_callback,
        on_transcript=on_transcript,
        on_audio_level=on_audio_level,
        on_speech_activity=on_speech_activity,
    )
    _listener.start()
    logger.info("ASTRA: Đang lắng nghe... (Nhấn Ctrl+C để dừng)")
    try:
        while _listener._thread and _listener._thread.is_alive():
            if stop_event is not None and stop_event.is_set():
                break
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("ASTRA: Dừng lắng nghe...")
    finally:
        _listener.stop()


if __name__ == "__main__":
    listen()
