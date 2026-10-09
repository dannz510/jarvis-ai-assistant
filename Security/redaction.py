import re
from typing import Any, Dict, List, Optional

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]?){8,15}(?!\d)")
_TOKEN = re.compile(r"(?:\b(api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|secret|password|passphrase|private[_-]?key)\b\s*[:=]\s*\S+)", re.I)
_BEARER = re.compile(r"(?:bearer\s+[a-zA-Z0-9._-]+)", re.I)
_PII_PATTERNS = [_EMAIL, _PHONE, _TOKEN, _BEARER]


def redact_text(text: str, placeholder: str = "[REDACTED]") -> str:
    if not text:
        return text
    s = str(text)
    for p in _PII_PATTERNS:
        s = p.sub(placeholder, s)
    return s


def redact_dict(d: Dict[str, Any], sensitive_keys: Optional[List[str]] = None, placeholder: str = "[REDACTED]") -> Dict[str, Any]:
    keys = {k.lower() for k in (sensitive_keys or ["password", "secret", "token", "key", "api_key", "access_token", "refresh_token", "auth_token", "private_key", "ssn", "email", "phone"])}
    out: Dict[str, Any] = {}
    for k, v in d.items():
        kl = str(k).lower()
        if kl in keys:
            out[k] = placeholder
            continue
        if isinstance(v, dict):
            out[k] = redact_dict(v, sensitive_keys, placeholder)
        elif isinstance(v, list):
            out[k] = [redact_dict(x, sensitive_keys, placeholder) if isinstance(x, dict) else (redact_text(str(x), placeholder) if isinstance(x, str) else x) for x in v]
        elif isinstance(v, str):
            out[k] = redact_text(v, placeholder)
        else:
            out[k] = v
    return out


def needs_redaction(text: str) -> bool:
    if not text:
        return False
    s = str(text)
    for p in _PII_PATTERNS:
        if p.search(s):
            return True
    return False
