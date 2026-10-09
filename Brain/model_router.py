"""Route requests between configured local models using lightweight heuristics."""

from dataclasses import dataclass
import os
import re


_REASONING_CUES = re.compile(
    r"\b(analy[sz]e|debug|refactor|design|compare|prove|derive|explain in detail|"
    r"step by step|plan|architecture|review|multi[- ]step|research|phân tích|"
    r"giải thích|so sánh|chứng minh|lập kế hoạch|kiến trúc|đánh giá)\b",
    re.I,
)
_CODING_CUES = re.compile(r"\b(code|python|javascript|typescript|function|class|bug|exception|stack trace|mã nguồn|lỗi)\b", re.I)


@dataclass(frozen=True)
class ModelChoice:
    model: str
    tier: str
    reason: str


class ModelRouter:
    """Keep model policy separate from the chat and UI layers."""

    def __init__(self, fast_model=None, reasoning_model=None):
        self.fast_model = fast_model or os.environ.get("ASTRA_FAST_MODEL", "qwen2.5:1.5b")
        self.reasoning_model = reasoning_model or os.environ.get(
            "ASTRA_REASONING_MODEL",
            os.environ.get("ASTRA_MODEL", "qwen2.5-coder:7b"),
        )
        self.available_models = None

    def set_available_models(self, models):
        self.available_models = {str(model) for model in models or []}

    def route(self, prompt, explicit_model=None):
        if explicit_model:
            return ModelChoice(explicit_model, "manual", "User-selected model")
        text = str(prompt or "").strip()
        if len(text) > 320 or _REASONING_CUES.search(text) or _CODING_CUES.search(text):
            preferred = ModelChoice(self.reasoning_model, "reasoning", "Complex, coding, or analysis request")
            alternate = ModelChoice(self.fast_model, "fast", "Reasoning model unavailable; using fast model")
        else:
            preferred = ModelChoice(self.fast_model, "fast", "Short conversational request")
            alternate = ModelChoice(self.reasoning_model, "reasoning", "Fast model unavailable; using reasoning model")
        if self.available_models is not None and preferred.model not in self.available_models:
            if alternate.model in self.available_models:
                return alternate
            if self.available_models:
                fallback = sorted(self.available_models)[0]
                return ModelChoice(fallback, "fallback", "Configured models are unavailable")
        return preferred
