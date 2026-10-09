import json
from pathlib import Path
from typing import Any, Dict

from core.config import get_config
from core.db.session import session_scope, init_db
from core.models.entities import Message, Session
from datetime import datetime


def _parse_history_txt(p: Path) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return items
    blocks = re_split(t)
    for b in blocks:
        u, a = split_ua(b)
        if u or a:
            items.append(("app", u, a))
    return items


def re_split(t: str) -> list[str]:
    import re

    return re.split(r"(?m)^Current Datetime\s*:.*$", t)


def split_ua(b: str) -> tuple[str, str]:
    u = ""
    a = ""
    import re

    m_u = re.search(r"(?m)^User\s*:\s*(.*)$", b)
    m_a = re.search(r"(?m)^LLM\s*:\s*(.*)$", b)
    if not m_a:
        m_a = re.search(r"(?m)^AI\s*:\s*(.*)$", b)
    if m_u:
        u = m_u.group(1).strip()
    if m_a:
        a = m_a.group(1).strip()
    return u, a


def _parse_conv_txt(p: Path) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return items
    import re

    pairs = re.split(r"(?m)(?=^User:|^AI:)", t)
    i = 0
    while i + 1 < len(pairs):
        left = pairs[i].strip()
        right = pairs[i + 1].strip()
        if left.startswith("User:") and (right.startswith("AI:")):
            u = left.replace("User:", "", 1).strip()
            a = right.replace("AI:", "", 1).strip()
            items.append(("app", u, a))
            i += 2
            continue
        i += 1
    return items


def _parse_chat_hystory(p: Path) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return items
    import re

    chunks = re.split(r"\n{2,}", t)
    for c in chunks:
        s = c.strip()
        if len(s) < 10:
            continue
        items.append(("app", "", s))
    return items


def migrate_all() -> Dict[str, Any]:
    cfg = get_config()
    init_db()
    root = Path(".")
    files = [
        root / "history.txt",
        root / "conv_history.txt",
        root / "chat_hystory.txt",
    ]
    total = 0
    sessions_created = 0
    from core.db.session import session_scope
    from core.models.entities import Message, Session, User
    from api.services.chat_service import get_or_create_user

    with session_scope() as s:
        u = s.query(User).filter(User.username == "default").first()
        if not u:
            u = User(username="default", display_name="default")
            s.add(u)
            s.flush()
        user_id = u.id
    for f in files:
        if not f.exists():
            continue
        items: list[tuple[str, str, str]] = []
        if f.name == "history.txt":
            items = _parse_history_txt(f)
        elif f.name == "conv_history.txt":
            items = _parse_conv_txt(f)
        elif f.name == "chat_hystory.txt":
            items = _parse_chat_hystory(f)
        if not items:
            continue
        with session_scope() as s:
            sess = Session(user_id=user_id, title=f"Migrated {f.name}", state="closed", agent="migrated")
            s.add(sess)
            s.flush()
            sid = sess.id
            sessions_created += 1
            for src, u_txt, a_txt in items:
                if u_txt:
                    m = Message(session_id=sid, user_id=user_id, role="user", content=u_txt, source="migrated", hash=__import__("hashlib").sha256(u_txt.encode()).hexdigest())
                    s.add(m)
                    total += 1
                if a_txt:
                    m = Message(session_id=sid, user_id=user_id, role="assistant", content=a_txt, source="migrated", hash=__import__("hashlib").sha256(a_txt.encode()).hexdigest())
                    s.add(m)
                    total += 1
    return {"sessions_created": sessions_created, "messages_migrated": total}
