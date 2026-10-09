"""
Main authentication manager orchestrating all auth methods.
"""

import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from Security.auth_types import (
    AuthMethod, AuthStatus, AuthenticationResult, UserProfile,
    AuthSession, DEFAULT_POLICY
)
from Security.secure_storage import SecureStorage
from Security.face_recognition import FaceRecognizer
from Security.fingerprint import FingerprintAuth
from Security.pin_auth import PINAuth
from Security.liveness import LivenessDetector

logger = logging.getLogger(__name__)


class AuthManager:
    """Central authentication management."""

    def __init__(self, policy=None, storage_dir=None):
        self.policy = policy or DEFAULT_POLICY
        self.storage = SecureStorage(storage_dir)
        self.face_recognizer = FaceRecognizer(self.policy)
        self.fingerprint_auth = FingerprintAuth(self.policy)
        self.pin_auth = PINAuth(self.policy)
        self.liveness_detector = LivenessDetector()

        self._active_session: Optional[AuthSession] = None
        self._sessions: List[AuthSession] = []

    @property
    def has_active_session(self) -> bool:
        if self._active_session and self._active_session.is_valid():
            return True
        return False

    @property
    def current_user(self) -> Optional[UserProfile]:
        if self.has_active_session:
            return self.storage.load_profile(self._active_session.user_id)
        return None

    def register_user(self, username: str, display_name: str, pin: Optional[str] = None,
                      password: Optional[str] = None) -> Optional[UserProfile]:
        """Register a new user."""
        import base64

        # Check if user exists
        existing = self.storage.get_user_by_username(username)
        if existing:
            logger.error(f"User {username} already exists")
            return None
        # Create profile
        profile = UserProfile.create_new(username, display_name)
        # Set PIN/Password if provided
        if pin:
            if len(pin) >= self.policy.pin_min_length:
                pin_hash, salt = self.pin_auth.hash_pin(pin)
                # Store in metadata
                profile.metadata['pin_hash'] = base64.b64encode(pin_hash).decode()
                profile.metadata['pin_salt'] = base64.b64encode(salt).decode()
                profile.pin_set = True
                profile.security_level = max(profile.security_level, 1)
        if password:
            if len(password) >= self.policy.password_min_length:
                pwd_hash, salt = self.pin_auth.hash_password(password)
                profile.metadata['pwd_hash'] = base64.b64encode(pwd_hash).decode()
                profile.metadata['pwd_salt'] = base64.b64encode(salt).decode()
                profile.password_hash = base64.b64encode(pwd_hash).decode()
                profile.security_level = max(profile.security_level, 1)
        if self.storage.save_profile(profile):
            return profile
        return None

    def enroll_face(self, username: str, frames: List) -> bool:
        """Enroll face for user."""
        profile = self.storage.get_user_by_username(username)
        if not profile:
            return False
        if self.face_recognizer.enroll_face(profile.user_id, frames):
            profile.face_enrolled = True
            profile.security_level = max(profile.security_level, 2)
            self.storage.save_profile(profile)
            return True
        return False

    def authenticate_pin(self, username: str, pin: str) -> AuthenticationResult:
        """Authenticate with PIN."""
        profile = self.storage.get_user_by_username(username)
        if not profile:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.PIN,
                status=AuthStatus.FAILED,
                message="User not found",
            )

        if not self.pin_auth.check_rate_limit(profile):
            self.storage.save_profile(profile)
            return AuthenticationResult(
                success=False,
                method=AuthMethod.PIN,
                status=AuthStatus.FAILED,
                message="Account locked",
            )

        if not profile.pin_set or 'pin_hash' not in profile.metadata:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.PIN,
                status=AuthStatus.REQUIRES_ENROLLMENT,
                message="PIN not set",
            )

        try:
            import base64
            pin_hash = base64.b64decode(profile.metadata['pin_hash'])
            pin_salt = base64.b64decode(profile.metadata['pin_salt'])

            if self.pin_auth.verify_pin(pin, pin_hash, pin_salt):
                self.pin_auth.record_success(profile)
                profile.last_login = datetime.now()
                self.storage.save_profile(profile)
                session = self._create_session(profile, [AuthMethod.PIN])
                return AuthenticationResult(
                    success=True,
                    method=AuthMethod.PIN,
                    status=AuthStatus.SUCCESS,
                    user_id=profile.user_id,
                    username=profile.username,
                    session_token=session.session_token,
                    message="Authentication successful",
                )
            else:
                self.pin_auth.record_failed_attempt(profile)
                self.storage.save_profile(profile)
                return AuthenticationResult(
                    success=False,
                    method=AuthMethod.PIN,
                    status=AuthStatus.FAILED,
                    message="Invalid PIN",
                )
        except Exception as e:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.PIN,
                status=AuthStatus.ERROR,
                message=str(e),
            )

    def authenticate_face(self, username: str, frame) -> AuthenticationResult:
        """Authenticate with face recognition."""
        profile = self.storage.get_user_by_username(username)
        if not profile:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.FAILED,
                message="User not found",
            )

        # Check liveness
        if not self.liveness_detector.is_live(frame):
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FACE,
                status=AuthStatus.LIVENESS_FAILED,
                message="Liveness check failed",
            )

        result = self.face_recognizer.verify_face(frame, profile)
        if result.success:
            profile.last_login = datetime.now()
            self.storage.save_profile(profile)
            session = self._create_session(profile, [AuthMethod.FACE])
            result.session_token = session.session_token
        return result

    def authenticate_fingerprint(self, username: str) -> AuthenticationResult:
        """Authenticate with fingerprint."""
        profile = self.storage.get_user_by_username(username)
        if not profile:
            return AuthenticationResult(
                success=False,
                method=AuthMethod.FINGERPRINT,
                status=AuthStatus.FAILED,
                message="User not found",
            )

        result = self.fingerprint_auth.verify_fingerprint(profile)
        if result.success:
            profile.last_login = datetime.now()
            self.storage.save_profile(profile)
            session = self._create_session(profile, [AuthMethod.FINGERPRINT])
            result.session_token = session.session_token
        return result

    def _create_session(self, profile: UserProfile, methods: List[AuthMethod]) -> AuthSession:
        """Create a new session."""
        import base64
        session_token = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip('=')[:32]
        expires_at = datetime.now() + timedelta(minutes=self.policy.session_timeout_minutes)

        session = AuthSession(
            session_token=session_token,
            user_id=profile.user_id,
            username=profile.username,
            authenticated_methods=methods,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            expires_at=expires_at,
        )
        self._active_session = session
        self._sessions.append(session)
        return session

    def logout(self) -> None:
        """Logout and invalidate session."""
        self._active_session = None

    def verify_session(self, token: str) -> bool:
        """Verify a session token."""
        if self._active_session and self._active_session.session_token == token:
            return self._active_session.is_valid()
        return False

