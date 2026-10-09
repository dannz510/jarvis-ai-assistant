"""Central configuration for ASTRA (local-first, closed-loop)."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _expand_path(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


def _appdata_root() -> Path:
    app_data = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    root = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
    return root / "ASTRA"


DEFAULT_CONFIG: Dict[str, Any] = {
    "data_dir": str(_appdata_root() / "data"),
    "db_path": str(_appdata_root() / "data" / "astra.db"),
    "cache_dir": str(_appdata_root() / "cache"),
    "logs_dir": str(_appdata_root() / "logs"),
    "storage_dir": str(_appdata_root() / "storage"),
    "keys_dir": str(_appdata_root() / "keys"),
    "audit_dir": str(_appdata_root() / "audit"),
    "web_host": "127.0.0.1",
    "web_port": 8787,
    "api_prefix": "/api",
    "local_only": True,
    "encrypt_at_rest": True,
    "encrypt_fields": True,
    "pii_redaction": True,
    "audit_immutable": True,
    "retention_days_chat": 90,
    "retention_days_metrics": 365,
    "retention_days_audit": 3650,
    "max_storage_bytes": 5 * 1024**3,
    "max_cache_bytes": 512 * 1024**2,
    "max_messages_per_session": 10000,
    "max_sessions_per_user": 500,
    "embedding_model": os.environ.get("ASTRA_EMBEDDING_MODEL", "").strip(),
    "ollama_host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"),
    "memory_policy": os.environ.get("ASTRA_MEMORY_POLICY", "explicit").strip().casefold(),
}


@dataclass
class AppConfig:
    data_dir: Path
    db_path: Path
    cache_dir: Path
    logs_dir: Path
    storage_dir: Path
    keys_dir: Path
    audit_dir: Path
    web_host: str = "127.0.0.1"
    web_port: int = 8787
    api_prefix: str = "/api"
    local_only: bool = True
    encrypt_at_rest: bool = True
    encrypt_fields: bool = True
    pii_redaction: bool = True
    audit_immutable: bool = True
    retention_days_chat: int = 90
    retention_days_metrics: int = 365
    retention_days_audit: int = 3650
    max_storage_bytes: int = 5 * 1024**3
    max_cache_bytes: int = 512 * 1024**2
    max_messages_per_session: int = 10000
    max_sessions_per_user: int = 500
    embedding_model: str = ""
    ollama_host: str = "http://127.0.0.1:11434"
    memory_policy: str = "explicit"
    env: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AppConfig":
        def p(k, default):
            v = d.get(k, default)
            if isinstance(v, str) and ("dir" in k or k.endswith("_path")):
                return _expand_path(v)
            return v
        return cls(
            data_dir=p("data_dir", DEFAULT_CONFIG["data_dir"]),
            db_path=p("db_path", DEFAULT_CONFIG["db_path"]),
            cache_dir=p("cache_dir", DEFAULT_CONFIG["cache_dir"]),
            logs_dir=p("logs_dir", DEFAULT_CONFIG["logs_dir"]),
            storage_dir=p("storage_dir", DEFAULT_CONFIG["storage_dir"]),
            keys_dir=p("keys_dir", DEFAULT_CONFIG["keys_dir"]),
            audit_dir=p("audit_dir", DEFAULT_CONFIG["audit_dir"]),
            web_host=d.get("web_host", DEFAULT_CONFIG["web_host"]),
            web_port=int(d.get("web_port", DEFAULT_CONFIG["web_port"])),
            api_prefix=d.get("api_prefix", DEFAULT_CONFIG["api_prefix"]),
            local_only=bool(d.get("local_only", DEFAULT_CONFIG["local_only"])),
            encrypt_at_rest=bool(d.get("encrypt_at_rest", DEFAULT_CONFIG["encrypt_at_rest"])),
            encrypt_fields=bool(d.get("encrypt_fields", DEFAULT_CONFIG["encrypt_fields"])),
            pii_redaction=bool(d.get("pii_redaction", DEFAULT_CONFIG["pii_redaction"])),
            audit_immutable=bool(d.get("audit_immutable", DEFAULT_CONFIG["audit_immutable"])),
            retention_days_chat=int(d.get("retention_days_chat", DEFAULT_CONFIG["retention_days_chat"])),
            retention_days_metrics=int(d.get("retention_days_metrics", DEFAULT_CONFIG["retention_days_metrics"])),
            retention_days_audit=int(d.get("retention_days_audit", DEFAULT_CONFIG["retention_days_audit"])),
            max_storage_bytes=int(d.get("max_storage_bytes", DEFAULT_CONFIG["max_storage_bytes"])),
            max_cache_bytes=int(d.get("max_cache_bytes", DEFAULT_CONFIG["max_cache_bytes"])),
            max_messages_per_session=int(d.get("max_messages_per_session", DEFAULT_CONFIG["max_messages_per_session"])),
            max_sessions_per_user=int(d.get("max_sessions_per_user", DEFAULT_CONFIG["max_sessions_per_user"])),
            embedding_model=d.get("embedding_model", DEFAULT_CONFIG["embedding_model"]),
            ollama_host=d.get("ollama_host", DEFAULT_CONFIG["ollama_host"]),
            memory_policy=d.get("memory_policy", DEFAULT_CONFIG["memory_policy"]),
            env={k: v for k, v in os.environ.items() if k.startswith("ASTRA_")},
        )

    def ensure_dirs(self):
        for p in (self.data_dir, self.cache_dir, self.logs_dir, self.storage_dir, self.keys_dir, self.audit_dir):
            p.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_dir": str(self.data_dir),
            "db_path": str(self.db_path),
            "cache_dir": str(self.cache_dir),
            "logs_dir": str(self.logs_dir),
            "storage_dir": str(self.storage_dir),
            "keys_dir": str(self.keys_dir),
            "audit_dir": str(self.audit_dir),
            "web_host": self.web_host,
            "web_port": self.web_port,
            "api_prefix": self.api_prefix,
            "local_only": self.local_only,
            "encrypt_at_rest": self.encrypt_at_rest,
            "encrypt_fields": self.encrypt_fields,
            "pii_redaction": self.pii_redaction,
            "audit_immutable": self.audit_immutable,
            "retention_days_chat": self.retention_days_chat,
            "retention_days_metrics": self.retention_days_metrics,
            "retention_days_audit": self.retention_days_audit,
            "max_storage_bytes": self.max_storage_bytes,
            "max_cache_bytes": self.max_cache_bytes,
            "max_messages_per_session": self.max_messages_per_session,
            "max_sessions_per_user": self.max_sessions_per_user,
            "embedding_model": self.embedding_model,
            "ollama_host": self.ollama_host,
            "memory_policy": self.memory_policy,
        }


def load_config(path: Optional[Path] = None) -> AppConfig:
    cfg_path = path or _appdata_root() / "config.json"
    data = dict(DEFAULT_CONFIG)
    try:
        if cfg_path.exists():
            loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
    except Exception:
        pass
    cfg = AppConfig.from_dict(data)
    cfg.ensure_dirs()
    return cfg


_config = load_config()
get_config = lambda: _config
