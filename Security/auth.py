from __future__ import annotations

import base64
import hmac
import hashlib
import os
import time
from typing import Dict, Optional, Tuple

from core.config import get_config


def _secret() -> bytes:
    s = os.environ.get("ASTRA_AUTH_SECRET") or "astra-local-secret-change-me"
    return s.encode("utf-8")


def issue_token(user_id: int, username: str, roles: list[str], ttl_s: int = 3600) -> str:
    exp = int(time.time()) + int(ttl_s)
    payload = f"{user_id}:{username}:{','.join(roles)}:{exp}"
    sig = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode((payload + '|' + base64.urlsafe_b64encode(sig).decode('ascii')).encode('utf-8')).decode('ascii')
    return token


def verify_token(token: str) -> Optional[Dict[str, str]]:
    try:
        raw = base64.urlsafe_b64decode(token.encode('ascii')).decode('utf-8')
        if '|' not in raw:
            return None
        payload, sig_b64 = raw.split('|', 1)
        expected = hmac.new(_secret(), payload.encode('utf-8'), hashlib.sha256).digest()
        sig = base64.urlsafe_b64decode(sig_b64.encode('ascii'))
        if not hmac.compare_digest(expected, sig):
            return None
        parts = payload.split(':')
        if len(parts) != 4:
            return None
        user_id, username, roles_str, exp_str = parts
        if int(exp_str) < int(time.time()):
            return None
        return {"user_id": user_id, "username": username, "roles": roles_str}
    except Exception:
        return None
