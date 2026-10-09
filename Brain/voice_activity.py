"""Voice activity detection for microphone frames used by ASTRA's listener.

WebRTC VAD is the preferred detector. A smoothed adaptive RMS gate keeps the
voice pipeline usable when the optional native wheel is unavailable.
"""

import array
import math
import os
import time


class VoiceActivityDetector:
    def __init__(self, sample_rate=16000, frame_ms=20, mode=None, vad_engine=None,
                 hangover_seconds=0.45):
        self.sample_rate = int(sample_rate)
        self.frame_ms = int(frame_ms)
        self.frame_bytes = self.sample_rate * self.frame_ms // 1000 * 2
        self.hangover_seconds = float(hangover_seconds)
        self._last_voice_at = 0.0
        self._noise_floor = 180.0
        self._active = False

        if mode is None:
            try:
                mode = int(os.environ.get("ASTRA_VAD_MODE", "2"))
            except ValueError:
                mode = 2
        self.mode = max(0, min(3, int(mode)))
        self._vad = vad_engine
        if self._vad is None:
            try:
                import webrtcvad

                self._vad = webrtcvad.Vad(self.mode)
            except (ImportError, AttributeError, RuntimeError):
                self._vad = None

    @property
    def using_webrtc(self):
        return self._vad is not None

    def process(self, pcm_data, now=None):
        """Return whether speech is active, including a short end-of-speech hangover."""
        timestamp = time.monotonic() if now is None else float(now)
        data = bytes(pcm_data or b"")
        speech = self._contains_speech(data)
        if speech:
            self._last_voice_at = timestamp
        self._active = speech or timestamp - self._last_voice_at < self.hangover_seconds
        return self._active

    def _contains_speech(self, data):
        if self._vad is not None:
            frame_count = len(data) // self.frame_bytes
            if frame_count:
                voiced = 0
                for offset in range(0, frame_count * self.frame_bytes, self.frame_bytes):
                    frame = data[offset:offset + self.frame_bytes]
                    try:
                        voiced += bool(self._vad.is_speech(frame, self.sample_rate))
                    except (ValueError, TypeError):
                        self._vad = None
                        break
                if self._vad is not None:
                    # A short majority threshold tolerates consonant gaps while
                    # rejecting isolated clicks in a 256 ms microphone chunk.
                    return voiced >= max(2, math.ceil(frame_count * 0.18))

        sample_count = len(data) // 2
        if not sample_count:
            return False
        samples = array.array("h")
        samples.frombytes(data[:sample_count * 2])
        rms = math.sqrt(sum(sample * sample for sample in samples) / sample_count)
        threshold = max(360.0, self._noise_floor * 2.25)
        speech = rms >= threshold
        if not speech:
            # Follow changing room noise slowly, while never letting the floor
            # rise quickly enough to swallow a quiet speaker.
            self._noise_floor = min(1400.0, self._noise_floor * 0.98 + rms * 0.02)
        return speech

