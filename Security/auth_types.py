"""
Core authentication types and data structures for ASTRA Security Module.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class AuthMethod(Enum):
    """Supported authentication methods."""
    FACE = "face"
    FINGERPRINT = "fingerprint"
    PIN = "pin"
    PASSWORD = "password"
    DEVICE_CREDENTIAL = "device_credential"  # Windows Hello / system credentials


class AuthStatus(Enum):
    """Authentication attempt status."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    ERROR = "error"
    REQUIRES_ENROLLMENT = "requires_enrollment"
    LIVENESS_FAILED = "liveness_failed"
    HARDWARE_UNAVAILABLE = "hardware_unavailable"


@dataclass(frozen=True)
class AuthenticationResult:
    """Result of an authentication attempt."""
    success: bool
    method: AuthMethod
    status: AuthStatus
    user_id: Optional[str] = None
    username: Optional[str] = None
    confidence: float = 0.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_token: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        return self.success and self.status == AuthStatus.SUCCESS


@dataclass
class UserProfile:
    """User profile with biometric enrollments."""
    user_id: str
    username: str
    display_name: str
    created_at: datetime
    last_login: Optional[datetime] = None
    face_enrolled: bool = False
    fingerprint_enrolled: bool = False
    pin_set: bool = False
    password_hash: Optional[str] = None
    face_embeddings: List[List[float]] = field(default_factory=list)
    fingerprint_templates: List[bytes] = field(default_factory=list)
    security_level: int = 1  # 1=PIN only, 2=Biometric, 3=Multi-factor
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_new(cls, username: str, display_name: str) -> "UserProfile":
        return cls(
            user_id=uuid.uuid4().hex[:16],
            username=username.lower().strip(),
            display_name=display_name.strip(),
            created_at=datetime.now(),
        )


@dataclass
class AuthSession:
    """Active authentication session."""
    session_token: str
    user_id: str
    username: str
    authenticated_methods: List[AuthMethod]
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at

    def touch(self, extend_minutes: int = 30) -> None:
        self.last_activity = datetime.now()
        from datetime import timedelta
        self.expires_at = datetime.now() + timedelta(minutes=extend_minutes)


class SecurityPolicy:
    """Security policy configuration."""
    
    def __init__(self):
        # Face recognition thresholds
        self.face_match_threshold: float = 0.65  # Cosine similarity threshold
        self.face_liveness_threshold: float = 0.7
        self.face_min_enrollment_samples: int = 5
        self.face_max_enrollment_samples: int = 20
        
        # Fingerprint settings
        self.fp_match_threshold: int = 40  # Windows BSP score threshold
        
        # PIN/Password settings
        self.pin_min_length: int = 6
        self.pin_max_length: int = 12
        self.password_min_length: int = 10
        self.max_failed_attempts: int = 5
        self.lockout_duration_minutes: int = 15
        
        # Session settings
        self.session_timeout_minutes: int = 30
        self.session_extend_minutes: int = 30
        self.require_reauth_on_wake: bool = True
        
        # Multi-factor requirements
        self.require_mfa_for_sensitive: bool = True
        self.allowed_methods: List[AuthMethod] = list(AuthMethod)
        
        # Hardware requirements
        self.require_tpm_for_keys: bool = True
        self.allow_software_fallback: bool = True


# Default security policy
DEFAULT_POLICY = SecurityPolicy()