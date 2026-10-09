"""
Fingerprint authentication using Windows Biometric Framework (WBF) via WinBio API.
"""

import ctypes
from ctypes import wintypes
from typing import Optional, List
import logging

from Security.auth_types import UserProfile, DEFAULT_POLICY, AuthenticationResult, AuthStatus, AuthMethod

logger = logging.getLogger(__name__)

# Windows Biometric API constants
WINBIO_TYPE_FINGERPRINT = 0x00000001
WINBIO_POOL_SYSTEM = 0x00000001
WINBIO_SESSION_DEFAULT = 0x00000001
WINBIO_FLAG_DEFAULT = 0x00000000
WINBIO_E_NO_MATCH = 0x80098005


class FingerprintAuth:
    """Fingerprint authentication via Windows Biometric Framework."""
    
    def __init__(self, policy=None):
        self.policy = policy or DEFAULT_POLICY
        self._session_handle = None
        self._available = self._check_biometric_availability()
    
    def _check_biometric_availability(self) -> bool:
        """Check if Windows Biometric Framework is available and has fingerprint sensor."""
        try:
            # Try to load WinBio library
            winbio = ctypes.windll.WinBio
            return True
        except (AttributeError, OSError):
            logger.warning("Windows Biometric Framework not available")
            return False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def enroll_fingerprint(self, user_profile: UserProfile) -> bool:
        """Enroll fingerprint for user (requires user interaction)."""
        if not self._available:
            return False
        try:
            # Note: Full WinBio enrollment requires complex API calls
            # This is a simplified placeholder
            # In production, use winbio_api.h via ctypes
            logger.info("Fingerprint enrollment requires Windows Hello/Windows Biometric setup")
            return False  # Requires proper WinBio implementation
        except Exception as e:
            logger.error(f"Fingerprint enrollment error: {e}")
            return False
    
    def verify_fingerprint(self, user_profile: UserProfile) -> AuthenticationResult:
        """Verify fingerprint against enrolled templates."""
        if not self._available:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FINGERPRINT,
                status=AuthStatus.HARDWARE_UNAVAILABLE,
                message="Fingerprint sensor not available",
            )
        
        if not user_profile.fingerprint_enrolled:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FINGERPRINT,
                status=AuthStatus.REQUIRES_ENROLLMENT,
                message="Fingerprint not enrolled",
            )
        
        try:
            # Simplified - would call WinBioIdentify or WinBioVerifyWithTemplate
            # For demo purposes, indicate hardware available but need enrollment
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FINGERPRINT,
                status=AuthStatus.REQUIRES_ENROLLMENT,
                message="Fingerprint verification requires enrollment via Windows Hello",
            )
        except Exception as e:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FINGERPRINT,
                status=AuthStatus.ERROR,
                message=str(e),
            )