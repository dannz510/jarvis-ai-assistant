from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Set


class Permission(str, Enum):
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    STORAGE_READ = "storage:read"
    STORAGE_WRITE = "storage:write"
    METRICS_READ = "metrics:read"
    AUDIT_READ = "audit:read"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    USERS_MANAGE = "users:manage"
    SYSTEM_ADMIN = "system:admin"


ROLE_PERMS: Dict[str, List[Permission]] = {
    "user": [
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.STORAGE_READ,
        Permission.METRICS_READ,
        Permission.SETTINGS_READ,
    ],
    "admin": list(Permission),
}


def get_role_perms(role: str) -> Set[Permission]:
    return set(ROLE_PERMS.get(role, ROLE_PERMS["user"]))


def require_perm(user_roles: List[str], perm: Permission) -> bool:
    for r in user_roles:
        if perm in get_role_perms(r):
            return True
    return False
