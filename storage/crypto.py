import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover
    Fernet = None
    InvalidToken = Exception

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except Exception:  # pragma: no cover
    hashes = None
    PBKDF2HMAC = None

from core.config import get_config


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    if PBKDF2HMAC is None or hashes is None:
        return hashlib.sha256(passphrase.encode("utf-8")).digest()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


@dataclass
class KeyMaterial:
    key_id: str
    key: bytes  # urlsafe base64 (32 bytes raw -> fernet needs urlsafe)
    salt: bytes


class CryptoManager:
    """Field-level + blob encryption with keyring/file fallback (local-first)."""

    def __init__(self) -> None:
        self.cfg = get_config()
        self.cfg.ensure_dirs()
        self._master_key: Optional[bytes] = None
        self._key_id: str = "default"
        self._fernet: Optional[Fernet] = None
        self._load_or_create()

    def _load_or_create(self):
        key_file = self.cfg.keys_dir / "master.key"
        salt_file = self.cfg.keys_dir / "master.salt"
        try:
            if key_file.exists() and salt_file.exists():
                enc = key_file.read_bytes()
                salt = salt_file.read_bytes()
                passphrase = os.environ.get("ASTRA_MASTER_PASSPHRASE", "")
                if passphrase:
                    derived = derive_key_from_passphrase(passphrase, salt)
                else:
                    derived = hashlib.sha256(salt).digest()
                self._master_key = base64.urlsafe_b64encode(derived)
                self._key_id = sha256_bytes(salt)[:16]
            else:
                salt = os.urandom(32)
                passphrase = os.environ.get("ASTRA_MASTER_PASSPHRASE", "")
                if passphrase:
                    derived = derive_key_from_passphrase(passphrase, salt)
                else:
                    derived = hashlib.sha256(salt + os.urandom(16)).digest()
                self._master_key = base64.urlsafe_b64encode(derived)
                self._key_id = sha256_bytes(salt)[:16]
                salt_file.write_bytes(salt)
                key_file.write_bytes(self._master_key)
                try:
                    os.chmod(key_file, 0o600)
                    os.chmod(salt_file, 0o600)
                except Exception:
                    pass
        except Exception:
            salt = os.urandom(32)
            derived = hashlib.sha256(salt).digest()
            self._master_key = base64.urlsafe_b64encode(derived)
            self._key_id = sha256_bytes(salt)[:16]

        if Fernet is not None and self._master_key:
            try:
                self._fernet = Fernet(self._master_key)
            except Exception:
                self._fernet = None

    @property
    def key_id(self) -> str:
        return self._key_id

    def encrypt_text(self, text: str) -> Tuple[Optional[bytes], str, bool]:
        if not text:
            return None, "", False
        if not self._fernet:
            return None, text, False
        try:
            token = self._fernet.encrypt(text.encode("utf-8"))
            return token, "", True
        except Exception:
            return None, text, False

    def decrypt_text(self, enc_bytes: Optional[bytes], plain_fallback: Optional[str] = None) -> str:
        if not enc_bytes:
            return plain_fallback or ""
        if not self._fernet:
            return plain_fallback or enc_bytes.decode("utf-8", errors="replace")
        try:
            return self._fernet.decrypt(enc_bytes).decode("utf-8", errors="replace")
        except (InvalidToken, Exception):
            return plain_fallback or ""

    def encrypt_bytes(self, data: bytes) -> Tuple[bytes, bool]:
        if not data:
            return b"", False
        if not self._fernet:
            return data, False
        try:
            return self._fernet.encrypt(data), True
        except Exception:
            return data, False

    def decrypt_bytes(self, data: bytes, was_encrypted: bool = True) -> bytes:
        if not data:
            return b""
        if not was_encrypted or not self._fernet:
            return data
        try:
            return self._fernet.decrypt(data)
        except Exception:
            return data

    def encrypt_json(self, obj: Any) -> Tuple[Optional[bytes], str, bool]:
        s = json.dumps(obj, ensure_ascii=False)
        return self.encrypt_text(s)

    def decrypt_json(self, enc_bytes: Optional[bytes], plain_fallback: Optional[str] = None, default: Any = None) -> Any:
        s = self.decrypt_text(enc_bytes, plain_fallback)
        if not s:
            return default
        try:
            return json.loads(s)
        except Exception:
            return default
