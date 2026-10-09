"""Buffer Vosk segments until a complete conversational turn is likely."""

import re


_INCOMPLETE_ENDINGS = {
    "in", "at", "on", "with", "to", "for", "from", "of", "and", "or", "but",
    "because", "if", "while", "that", "which", "where", "when", "how", "the",
    "a", "an", "is", "are", "was", "were", "do", "does", "did", "can", "could",
    "would", "should", "will", "about", "into", "over", "under", "between",
    "ở", "tại", "trong", "với", "về", "đến", "tới", "của", "và", "hoặc", "là",
    "thì", "mà", "để", "cho", "trên", "dưới", "bằng", "như", "nếu", "vì", "với",
}
_SPACE = re.compile(r"\s+")


class SpeechTurnBuffer:
    """Join confirmed ASR segments and expose a live partial transcript."""

    def __init__(self, normal_timeout=0.85, incomplete_timeout=2.5):
        self.normal_timeout = float(normal_timeout)
        self.incomplete_timeout = float(incomplete_timeout)
        self.confirmed_transcript = ""
        self.partial_transcript = ""
        self.last_segment_at = None

    @staticmethod
    def _normalize(text):
        return _SPACE.sub(" ", str(text or "")).strip()

    @property
    def has_confirmed_text(self):
        return bool(self.confirmed_transcript)

    @property
    def preview(self):
        confirmed = self.confirmed_transcript
        partial = self.partial_transcript
        if not partial:
            return confirmed
        if partial.casefold().startswith(confirmed.casefold()):
            return partial
        if confirmed.casefold().endswith(partial.casefold()):
            return confirmed
        return self._normalize(f"{confirmed} {partial}")

    def update_partial(self, text):
        self.partial_transcript = self._normalize(text)

    def add_final(self, text, now):
        segment = self._normalize(text)
        if not segment:
            return self.preview
        current = self.confirmed_transcript
        if not current:
            current = segment
        elif segment.casefold().startswith(current.casefold()):
            current = segment
        elif not current.casefold().endswith(segment.casefold()):
            current = self._normalize(f"{current} {segment}")
        self.confirmed_transcript = current
        self.partial_transcript = ""
        self.last_segment_at = float(now)
        return self.preview

    def is_incomplete(self):
        text = self.confirmed_transcript
        if not text:
            return False
        final_word = text.casefold().split()[-1].strip(".,!?;:")
        return final_word in _INCOMPLETE_ENDINGS or text.rstrip().endswith(("...", "…", ","))

    def should_finalize(self, now, speech_active=False):
        if (not self.has_confirmed_text or self.last_segment_at is None
                or self.partial_transcript or speech_active):
            return False
        timeout = self.incomplete_timeout if self.is_incomplete() else self.normal_timeout
        return float(now) - self.last_segment_at >= timeout

    def consume(self):
        text = self.confirmed_transcript
        self.confirmed_transcript = ""
        self.partial_transcript = ""
        self.last_segment_at = None
        return text
