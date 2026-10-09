import hashlib
import json
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from core.config import get_config


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> datetime:
    return utcnow()


class CacheEntry:
    def __init__(self, ns: str, key: str, data: bytes, ttl_s: int, size: int, sha: str):
        self.ns = ns
        self.key = key
        self.data = data
        self.size = size
        self.sha256 = sha
        self.ttl_s = ttl_s
        self.created_at = _now()
        self.accessed_at = self.created_at
        self.expires_at = self.created_at + timedelta(seconds=ttl_s) if ttl_s > 0 else self.created_at + timedelta(days=36500)
        self.hits = 0
        self.misses = 0
        self.evicted = False
        self.evicted_at: Optional[datetime] = None
        self.reason = ""


class CacheManager:
    """LRU + TTL + stats, in-memory (local-first). Can persist stats later to DB."""

    def __init__(self) -> None:
        self.cfg = get_config()
        self._lock = Lock()
        self._store: Dict[Tuple[str, str], CacheEntry] = {}
        self._lru: List[Tuple[str, str]] = []
        self._hits = 0
        self._misses = 0
        self._bytes = 0
        self._max_bytes = self.cfg.max_cache_bytes

    @staticmethod
    def _key(ns: str, key: str) -> Tuple[str, str]:
        return (ns or "default", key)

    def _touch(self, k: Tuple[str, str]):
        try:
            self._lru.remove(k)
        except ValueError:
            pass
        self._lru.append(k)

    def _evict_if_needed(self):
        while self._bytes > self._max_bytes and self._lru:
            oldest = self._lru.pop(0)
            e = self._store.pop(oldest, None)
            if e:
                self._bytes -= e.size
                e.evicted = True
                e.evicted_at = _now()
                e.reason = "lru_size"
        now = _now()
        expired: List[Tuple[str, str]] = []
        for k, e in self._store.items():
            if not e.evicted and e.expires_at < now:
                expired.append(k)
        for k in expired:
            e = self._store.pop(k, None)
            if e:
                try:
                    self._lru.remove(k)
                except ValueError:
                    pass
                self._bytes -= e.size
                e.evicted = True
                e.evicted_at = now
                e.reason = "ttl"

    def get(self, ns: str, key: str) -> Optional[bytes]:
        with self._lock:
            self._evict_if_needed()
            k = self._key(ns, key)
            e = self._store.get(k)
            if not e or e.evicted:
                self._misses += 1
                return None
            now = _now()
            if e.expires_at < now:
                self._store.pop(k, None)
                try:
                    self._lru.remove(k)
                except ValueError:
                    pass
                self._bytes -= e.size
                e.evicted = True
                e.evicted_at = now
                e.reason = "ttl"
                self._misses += 1
                return None
            e.accessed_at = now
            e.hits += 1
            self._hits += 1
            self._touch(k)
            return e.data

    def set(self, ns: str, key: str, data: bytes, ttl_s: int = 300) -> str:
        with self._lock:
            k = self._key(ns, key)
            if k in self._store:
                old = self._store.pop(k, None)
                if old:
                    self._bytes -= old.size
                    try:
                        self._lru.remove(k)
                    except ValueError:
                        pass
            size = len(data)
            sha = hashlib.sha256(data).hexdigest()
            e = CacheEntry(ns, key, data, ttl_s, size, sha)
            self._store[k] = e
            self._bytes += size
            self._touch(k)
            self._evict_if_needed()
            return sha

    def delete(self, ns: str, key: str) -> bool:
        with self._lock:
            k = self._key(ns, key)
            e = self._store.pop(k, None)
            if e:
                self._bytes -= e.size
                try:
                    self._lru.remove(k)
                except ValueError:
                    pass
                e.evicted = True
                e.evicted_at = _now()
                e.reason = "manual"
                return True
            return False

    def clear(self, ns: Optional[str] = None):
        with self._lock:
            if ns is None:
                for e in self._store.values():
                    e.evicted = True
                    e.evicted_at = _now()
                    e.reason = "clear_all"
                self._store.clear()
                self._lru.clear()
                self._bytes = 0
                return
            remove = [k for k in list(self._store.keys()) if k[0] == ns]
            for k in remove:
                e = self._store.pop(k, None)
                if e:
                    self._bytes -= e.size
                    e.evicted = True
                    e.evicted_at = _now()
                    e.reason = "clear_ns"
                try:
                    self._lru.remove(k)
                except ValueError:
                    pass

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = (self._hits / total) if total else 0.0
            entries = []
            for k, e in self._store.items():
                entries.append(
                    {
                        "ns": k[0],
                        "key": k[1],
                        "size_bytes": e.size,
                        "hits": e.hits,
                        "ttl_s": e.ttl_s,
                        "expires_at": e.expires_at.isoformat(),
                        "accessed_at": e.accessed_at.isoformat(),
                        "created_at": e.created_at.isoformat(),
                    }
                )
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(hit_ratio, 4),
                "bytes": self._bytes,
                "max_bytes": self._max_bytes,
                "entries": len(entries),
                "items": entries,
            }
