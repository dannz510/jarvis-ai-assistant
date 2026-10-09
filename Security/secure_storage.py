"""
Secure encrypted storage for biometric templates, keys, and user credentials.
Uses Windows DPAPI (CryptProtectData) for key storage and Fernet for data encryption.
"""

import os
import json
import base64
from pathlib import Path
from typing import Any, Dict, Optional, List
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, kdf
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import win32crypt
    DPAPI_AVAILABLE = True
except ImportError:
    DPAPI_AVAILABLE = False

from Security.auth_types import UserProfile, DEFAULT_POLICY


class SecureStorage:
    """Secure storage for user profiles and biometric data."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            app_data = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
            root = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
            storage_dir = root / "ASTRA" / "security"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir = self.storage_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir = self.storage_dir / "keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Secure file permissions on Windows
        try:
            os.chmod(self.storage_dir, 0o700)
            os.chmod(self.profiles_dir, 0o700)
            os.chmod(self.keys_dir, 0o700)
        except (OSError, AttributeError):
            pass
        
        self._key_cache: Dict[str, bytes] = {}
    
    def _get_master_key(self, user_id: str) -> bytes:
        """Get or create a master encryption key for a user."""
        if user_id in self._key_cache:
            return self._key_cache[user_id]
        
        key_path = self.keys_dir / f"{user_id}.key.enc"
        
        if key_path.exists():
            # Decrypt key using DPAPI
            try:
                encrypted_key = key_path.read_bytes()
                if DPAPI_AVAILABLE:
                    decrypted = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)
                    master_key = decrypted[1]
                else:
                    # Fallback: use machine-specific data
                    master_key = self._derive_fallback_key(user_id)
            except Exception:
                master_key = self._derive_fallback_key(user_id)
        else:
            # Generate new master key
            master_key = os.urandom(32)
            # Encrypt with DPAPI
            try:
                if DPAPI_AVAILABLE:
                    encrypted = win32crypt.CryptProtectData(master_key, None, None, None, win32crypt.CRYPTPROTECT_LOCAL_MACHINE | win32crypt.CRYPTPROTECT_UI_FORBIDDEN)
                    key_path.write_bytes(encrypted)
                    try:
                        os.chmod(key_path, 0o600)
                    except OSError:
                        pass
                else:
                    # Store derived fallback (less secure but functional)
                    pass
            except Exception:
                pass
        
        self._key_cache[user_id] = master_key
        return master_key
    
    def _derive_fallback_key(self, user_id: str) -> bytes:
        """Fallback key derivation when DPAPI unavailable."""
        salt = hashlib.sha256(f"{user_id}:{os.environ.get('COMPUTERNAME', 'astra')}".encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(salt))
    
    def _encrypt_data(self, data: bytes, user_id: str) -> bytes:
        """Encrypt data for a specific user."""
        master_key = self._get_master_key(user_id)
        fernet = Fernet(base64.urlsafe_b64encode(master_key))
        return fernet.encrypt(data)
    
    def _decrypt_data(self, encrypted: bytes, user_id: str) -> bytes:
        """Decrypt data for a specific user."""
        master_key = self._get_master_key(user_id)
        fernet = Fernet(base64.urlsafe_b64encode(master_key))
        return fernet.decrypt(encrypted)
    
    def save_profile(self, profile: UserProfile) -> bool:
        """Save user profile securely."""
        try:
            profile_dict = {
                "user_id": profile.user_id,
                "username": profile.username,
                "display_name": profile.display_name,
                "created_at": profile.created_at.isoformat(),
                "last_login": profile.last_login.isoformat() if profile.last_login else None,
                "face_enrolled": profile.face_enrolled,
                "fingerprint_enrolled": profile.fingerprint_enrolled,
                "pin_set": profile.pin_set,
                "password_hash": profile.password_hash,
                "face_embeddings": profile.face_embeddings,
                "fingerprint_templates": [
                    base64.b64encode(t).decode('utf-8') for t in profile.fingerprint_templates
                ],
                "security_level": profile.security_level,
                "failed_attempts": profile.failed_attempts,
                "locked_until": profile.locked_until.isoformat() if profile.locked_until else None,
                "metadata": profile.metadata,
            }
            data = json.dumps(profile_dict).encode('utf-8')
            encrypted = self._encrypt_data(data, profile.user_id)
            profile_path = self.profiles_dir / f"{profile.user_id}.profile.enc"
            profile_path.write_bytes(encrypted)
            try:
                os.chmod(profile_path, 0o600)
            except OSError:
                pass
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
    
    def load_profile(self, user_id: str) -> Optional[UserProfile]:
        """Load user profile."""
        try:
            profile_path = self.profiles_dir / f"{user_id}.profile.enc"
            if not profile_path.exists():
                return None
            encrypted = profile_path.read_bytes()
            decrypted = self._decrypt_data(encrypted, user_id)
            profile_dict = json.loads(decrypted.decode('utf-8'))
            
            from datetime import datetime
            profile = UserProfile(
                user_id=profile_dict["user_id"],
                username=profile_dict["username"],
                display_name=profile_dict["display_name"],
                created_at=datetime.fromisoformat(profile_dict["created_at"]),
                last_login=datetime.fromisoformat(profile_dict["last_login"]) if profile_dict["last_login"] else None,
                face_enrolled=profile_dict["face_enrolled"],
                fingerprint_enrolled=profile_dict["fingerprint_enrolled"],
                pin_set=profile_dict["pin_set"],
                password_hash=profile_dict["password_hash"],
                face_embeddings=profile_dict["face_embeddings"],
                fingerprint_templates=[
                    base64.b64decode(t.encode('utf-8')) for t in profile_dict["fingerprint_templates"]
                ],
                security_level=profile_dict["security_level"],
                failed_attempts=profile_dict["failed_attempts"],
                locked_until=datetime.fromisoformat(profile_dict["locked_until"]) if profile_dict["locked_until"] else None,
                metadata=profile_dict.get("metadata", {}),
            )
            return profile
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all registered users."""
        users = []
        for profile_path in self.profiles_dir.glob("*.profile.enc"):
            user_id = profile_path.stem.replace(".profile", "")
            profile = self.load_profile(user_id)
            if profile:
                users.append({
                    "user_id": profile.user_id,
                    "username": profile.username,
                    "display_name": profile.display_name,
                    "face_enrolled": profile.face_enrolled,
                    "fingerprint_enrolled": profile.fingerprint_enrolled,
                    "pin_set": profile.pin_set,
                    "created_at": profile.created_at.isoformat(),
                    "last_login": profile.last_login.isoformat() if profile.last_login else None,
                })
        return sorted(users, key=lambda x: x["created_at"])
    
    def get_user_by_username(self, username: str) -> Optional[UserProfile]:
        """Get user by username."""
        for user in self.list_users():
            if user["username"] == username.lower().strip():
                return self.load_profile(user["user_id"])
        return None
    
    def delete_profile(self, user_id: str) -> bool:
        """Delete user profile and keys."""
        try:
            profile_path = self.profiles_dir / f"{user_id}.profile.enc"
            key_path = self.keys_dir / f"{user_id}.key.enc"
            if profile_path.exists():
                profile_path.unlink()
            if key_path.exists():
                key_path.unlink()
            if user_id in self._key_cache:
                del self._key_cache[user_id]
            return True
        except Exception:
            return False
    
    def clear_all(self) -> bool:
        """Clear all stored data (factory reset)."""
        try:
            import shutil
            shutil.rmtree(self.storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.profiles_dir.mkdir(parents=True, exist_ok=True)
            self.keys_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False