"""
PIN/Password authentication module with secure hashing and rate limiting.
"""

import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from Security.auth_types import UserProfile, DEFAULT_POLICY


class PINAuth:
    """PIN and Password authentication."""
    
    def __init__(self, policy=None):
        self.policy = policy or DEFAULT_POLICY
    
    def hash_pin(self, pin: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """Hash PIN with PBKDF2."""
        if len(pin) < self.policy.pin_min_length or len(pin) > self.policy.pin_max_length:
            raise ValueError(f"PIN must be between {self.policy.pin_min_length} and {self.policy.pin_max_length} digits")
        
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
        )
        key = kdf.derive(pin.encode('utf-8'))
        return key, salt
    
    def verify_pin(self, pin: str, stored_hash: bytes, salt: bytes) -> bool:
        """Verify PIN against stored hash."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=200_000,
            )
            kdf.verify(pin.encode('utf-8'), stored_hash)
            return True
        except Exception:
            return False
    
    def hash_password(self, password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """Hash password with PBKDF2."""
        if len(password) < self.policy.password_min_length:
            raise ValueError(f"Password must be at least {self.policy.password_min_length} characters")
        
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=64,
            salt=salt,
            iterations=300_000,  # Stronger for passwords
        )
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def verify_password(self, password: str, stored_hash: bytes, salt: bytes) -> bool:
        """Verify password against stored hash."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=64,
                salt=salt,
                iterations=300_000,
            )
            kdf.verify(password.encode('utf-8'), stored_hash)
            return True
        except Exception:
            return False
    
    def check_rate_limit(self, profile: UserProfile) -> bool:
        """Check if user is locked out due to failed attempts."""
        if profile.locked_until and datetime.now() < profile.locked_until:
            return False
        # Reset lock if expired
        if profile.locked_until and datetime.now() >= profile.locked_until:
            profile.failed_attempts = 0
            profile.locked_until = None
        return True
    
    def record_failed_attempt(self, profile: UserProfile) -> None:
        """Record failed authentication attempt."""
        profile.failed_attempts += 1
        if profile.failed_attempts >= self.policy.max_failed_attempts:
            profile.locked_until = datetime.now() + timedelta(minutes=self.policy.lockout_duration_minutes)
    
    def record_success(self, profile: UserProfile) -> None:
        """Record successful authentication attempt."""
        profile.failed_attempts = 0
        profile.locked_until = None
        profile.last_login = datetime.now()