"""Acoustic barge-in detector for full-duplex interruption support.

When ASTRA is speaking and the user starts talking, this module detects the
incoming speech and triggers an immediate interruption so the assistant can
stop TTS and switch to listening.
"""

import math
import threading
import time
from typing import Callable, Optional

from Brain.logger import get_logger

logger = get_logger(__name__)

# Default RMS threshold (0-32768 scale). Calibrated for typical USB mics.
DEFAULT_RMS_THRESHOLD = 400.0
# Number of consecutive high-RMS frames required to trigger.
DEFAULT_TRIGGER_FRAMES = 3
# Cooldown in seconds to prevent re-triggering immediately after stopping.
DEFAULT_COOLDOWN_SECONDS = 1.5


class AcousticBargeInDetector:
    """Detects user speech while ASTRA is speaking and fires an interrupt."""

    def __init__(
        self,
        on_barge_in: Optional[Callable[[], None]] = None,
        rms_threshold: float = DEFAULT_RMS_THRESHOLD,
        trigger_frames: int = DEFAULT_TRIGGER_FRAMES,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ):
        self.on_barge_in = on_barge_in
        self.rms_threshold = float(rms_threshold)
        self.trigger_frames = max(1, int(trigger_frames))
        self.cooldown_seconds = float(cooldown_seconds)
        self._lock = threading.RLock()
        self._active = False
        self._consecutive = 0
        self._last_trigger_at = 0.0
        self._pyaudio = None
        self._stream = None

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        """Begin monitoring the microphone for barge-in speech."""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024,
            )
            self._active = True
            logger.info("Acoustic barge-in detector started.")
        except Exception as exc:
            logger.warning("Could not start barge-in detector: %s", exc)
            self._active = False

    def stop(self) -> None:
        self._active = False
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

    def poll(self) -> bool:
        """Read one audio chunk and return True if barge-in was detected."""
        if not self._active or self._stream is None:
            return False
        now = time.monotonic()
        if now - self._last_trigger_at < self.cooldown_seconds:
            return False
        try:
            data = self._stream.read(1024, exception_on_overflow=False)
        except Exception as exc:
            logger.warning("Barge-in read failed: %s", exc)
            return False

        # Compute RMS of the 16-bit PCM samples.
        count = len(data) // 2
        if count == 0:
            return False
        try:
            import array
            samples = array.array("h", data[:count * 2])
            sq_sum = sum(s * s for s in samples)
            rms = math.sqrt(sq_sum / count)
        except Exception:
            return False

        if rms >= self.rms_threshold:
            self._consecutive += 1
            if self._consecutive >= self.trigger_frames:
                self._consecutive = 0
                self._last_trigger_at = now
                logger.info("Barge-in detected (RMS=%.0f).", rms)
                if self.on_barge_in is not None:
                    try:
                        self.on_barge_in()
                    except Exception as exc:
                        logger.warning("Barge-in callback raised: %s", exc)
                return True
        else:
            self._consecutive = max(0, self._consecutive - 1)
        return False

    def run_loop(self, interval: float = 0.05) -> None:
        """Block while actively monitoring. Use in a dedicated thread."""
        while self._active:
            self.poll()
            time.sleep(interval)


class FakeBargeInDetector(AcousticBargeInDetector):
    """Test stub that never opens real audio hardware."""

    def start(self) -> None:
        self._active = True

    def poll(self) -> bool:
        return False