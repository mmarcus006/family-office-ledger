"""Domain models for authentication and authorization.

Provides:
- User management with secure password hashing
- Role-based access control (RBAC)
- Entity-level permissions
- JWT token management
- Session tracking
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


class UserRole(str, Enum):
    """User roles with hierarchical permissions."""

    OWNER = "owner"  # Full access to everything
    ADMIN = "admin"  # Manage users, settings, full data access
    ADVISOR = "advisor"  # View all, limited write access
    ACCOUNTANT = "accountant"  # Transaction entry, reconciliation
    VIEWER = "viewer"  # Read-only access
    API = "api"  # API-only access (for integrations)


class Permission(str, Enum):
    """Granular permissions for RBAC."""

    # Entity management
    ENTITY_CREATE = "entity:create"
    ENTITY_READ = "entity:read"
    ENTITY_UPDATE = "entity:update"
    ENTITY_DELETE = "entity:delete"

    # Account management
    ACCOUNT_CREATE = "account:create"
    ACCOUNT_READ = "account:read"
    ACCOUNT_UPDATE = "account:update"
    ACCOUNT_DELETE = "account:delete"

    # Transaction management
    TRANSACTION_CREATE = "transaction:create"
    TRANSACTION_READ = "transaction:read"
    TRANSACTION_UPDATE = "transaction:update"
    TRANSACTION_DELETE = "transaction:delete"
    TRANSACTION_VOID = "transaction:void"
    TRANSACTION_APPROVE = "transaction:approve"

    # Reports
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"
    REPORT_CREATE_TEMPLATE = "report:create_template"

    # Reconciliation
    RECONCILIATION_VIEW = "reconciliation:view"
    RECONCILIATION_PERFORM = "reconciliation:perform"
    RECONCILIATION_APPROVE = "reconciliation:approve"

    # Tax & QSBS
    TAX_VIEW = "tax:view"
    TAX_MANAGE = "tax:manage"
    QSBS_VIEW = "qsbs:view"
    QSBS_MANAGE = "qsbs:manage"

    # Private investments
    PRIVATE_INVESTMENT_VIEW = "private_investment:view"
    PRIVATE_INVESTMENT_MANAGE = "private_investment:manage"
    CAPITAL_CALL_APPROVE = "capital_call:approve"

    # Real estate
    REAL_ESTATE_VIEW = "real_estate:view"
    REAL_ESTATE_MANAGE = "real_estate:manage"

    # Crypto
    CRYPTO_VIEW = "crypto:view"
    CRYPTO_MANAGE = "crypto:manage"

    # User management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"

    # System settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_MANAGE = "settings:manage"

    # Audit
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

    # API
    API_KEY_MANAGE = "api_key:manage"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.OWNER: set(Permission),  # All permissions
    UserRole.ADMIN: {
        # All except some dangerous operations
        Permission.ENTITY_CREATE,
        Permission.ENTITY_READ,
        Permission.ENTITY_UPDATE,
        Permission.ACCOUNT_CREATE,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_UPDATE,
        Permission.TRANSACTION_CREATE,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_UPDATE,
        Permission.TRANSACTION_VOID,
        Permission.TRANSACTION_APPROVE,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.REPORT_CREATE_TEMPLATE,
        Permission.RECONCILIATION_VIEW,
        Permission.RECONCILIATION_PERFORM,
        Permission.RECONCILIATION_APPROVE,
        Permission.TAX_VIEW,
        Permission.TAX_MANAGE,
        Permission.QSBS_VIEW,
        Permission.QSBS_MANAGE,
        Permission.PRIVATE_INVESTMENT_VIEW,
        Permission.PRIVATE_INVESTMENT_MANAGE,
        Permission.CAPITAL_CALL_APPROVE,
        Permission.REAL_ESTATE_VIEW,
        Permission.REAL_ESTATE_MANAGE,
        Permission.CRYPTO_VIEW,
        Permission.CRYPTO_MANAGE,
        Permission.USER_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.API_KEY_MANAGE,
    },
    UserRole.ADVISOR: {
        Permission.ENTITY_READ,
        Permission.ACCOUNT_READ,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.RECONCILIATION_VIEW,
        Permission.TAX_VIEW,
        Permission.QSBS_VIEW,
        Permission.PRIVATE_INVESTMENT_VIEW,
        Permission.REAL_ESTATE_VIEW,
        Permission.CRYPTO_VIEW,
        Permission.AUDIT_VIEW,
    },
    UserRole.ACCOUNTANT: {
        Permission.ENTITY_READ,
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_CREATE,
        Permission.ACCOUNT_UPDATE,
        Permission.TRANSACTION_CREATE,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_UPDATE,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.RECONCILIATION_VIEW,
        Permission.RECONCILIATION_PERFORM,
        Permission.TAX_VIEW,
        Permission.QSBS_VIEW,
        Permission.PRIVATE_INVESTMENT_VIEW,
        Permission.REAL_ESTATE_VIEW,
        Permission.CRYPTO_VIEW,
    },
    UserRole.VIEWER: {
        Permission.ENTITY_READ,
        Permission.ACCOUNT_READ,
        Permission.TRANSACTION_READ,
        Permission.REPORT_VIEW,
        Permission.RECONCILIATION_VIEW,
        Permission.TAX_VIEW,
        Permission.QSBS_VIEW,
        Permission.PRIVATE_INVESTMENT_VIEW,
        Permission.REAL_ESTATE_VIEW,
        Permission.CRYPTO_VIEW,
    },
    UserRole.API: {
        # Limited permissions for API integrations
        Permission.ENTITY_READ,
        Permission.ACCOUNT_READ,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.REPORT_VIEW,
    },
}


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"  # Email verification pending
    LOCKED = "locked"  # Too many failed attempts
    SUSPENDED = "suspended"  # Admin action


class MFAMethod(str, Enum):
    """Multi-factor authentication methods."""

    NONE = "none"
    TOTP = "totp"  # Time-based OTP (Google Authenticator)
    SMS = "sms"
    EMAIL = "email"
    WEBAUTHN = "webauthn"  # Hardware keys


@dataclass
class User:
    """A user account."""

    email: str
    role: UserRole
    id: UUID = field(default_factory=uuid4)
    name: str | None = None
    status: UserStatus = UserStatus.PENDING

    # Password (hashed)
    password_hash: str | None = None
    password_changed_at: datetime | None = None
    must_change_password: bool = False

    # MFA
    mfa_method: MFAMethod = MFAMethod.NONE
    mfa_secret: str | None = None  # Encrypted TOTP secret
    mfa_verified: bool = False

    # Email verification
    email_verified: bool = False
    email_verification_token: str | None = None
    email_verification_sent_at: datetime | None = None

    # Login tracking
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    failed_login_attempts: int = 0
    locked_until: datetime | None = None

    # Entity access (if restricted)
    entity_ids: list[UUID] | None = None  # None = all entities

    # Preferences
    timezone: str = "UTC"
    locale: str = "en-US"
    theme: str = "light"

    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    created_by: UUID | None = None

    @property
    def is_active(self) -> bool:
        """Whether user can log in."""
        return self.status == UserStatus.ACTIVE and self.email_verified

    @property
    def is_locked(self) -> bool:
        """Whether account is locked."""
        if self.status == UserStatus.LOCKED:
            return True
        if self.locked_until and self.locked_until > _utc_now():
            return True
        return False

    @property
    def permissions(self) -> set[Permission]:
        """Get all permissions for this user's role."""
        return ROLE_PERMISSIONS.get(self.role, set())

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_any_permission(self, permissions: list[Permission]) -> bool:
        """Check if user has any of the given permissions."""
        return bool(self.permissions & set(permissions))

    def has_all_permissions(self, permissions: list[Permission]) -> bool:
        """Check if user has all of the given permissions."""
        return set(permissions) <= self.permissions

    def can_access_entity(self, entity_id: UUID) -> bool:
        """Check if user can access a specific entity."""
        if self.entity_ids is None:
            return True  # Has access to all entities
        return entity_id in self.entity_ids

    def record_login(self, ip_address: str | None = None) -> None:
        """Record a successful login."""
        self.last_login_at = _utc_now()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 30) -> None:
        """Record a failed login attempt."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = _utc_now() + timedelta(minutes=lockout_minutes)
            self.status = UserStatus.LOCKED


@dataclass
class EntityPermission:
    """Explicit permission override for a user on a specific entity."""

    user_id: UUID
    entity_id: UUID
    id: UUID = field(default_factory=uuid4)
    permissions: set[Permission] = field(default_factory=set)
    deny_permissions: set[Permission] = field(default_factory=set)  # Explicit denies
    granted_by: UUID | None = None
    granted_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime | None = None
    notes: str | None = None

    @property
    def is_expired(self) -> bool:
        """Whether the permission grant has expired."""
        if self.expires_at is None:
            return False
        return self.expires_at < _utc_now()

    def has_permission(self, permission: Permission) -> bool | None:
        """Check if this grant allows/denies a permission.

        Returns:
            True if explicitly allowed
            False if explicitly denied
            None if not specified (fall back to role)
        """
        if permission in self.deny_permissions:
            return False
        if permission in self.permissions:
            return True
        return None


@dataclass
class Session:
    """A user session."""

    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    token_hash: str | None = None  # Hashed JWT ID for revocation
    refresh_token_hash: str | None = None

    # Session info
    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime | None = None
    last_activity_at: datetime = field(default_factory=_utc_now)

    # Client info
    ip_address: str | None = None
    user_agent: str | None = None
    device_type: str | None = None  # "web", "mobile", "api"
    device_name: str | None = None

    # Status
    is_active: bool = True
    revoked_at: datetime | None = None
    revoked_reason: str | None = None

    def revoke(self, reason: str | None = None) -> None:
        """Revoke this session."""
        self.is_active = False
        self.revoked_at = _utc_now()
        self.revoked_reason = reason

    @property
    def is_valid(self) -> bool:
        """Whether session is still valid."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < _utc_now():
            return False
        return True

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = _utc_now()


@dataclass
class APIKey:
    """An API key for programmatic access."""

    user_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    key_prefix: str | None = None  # First 8 chars for identification
    key_hash: str | None = None  # Hashed full key

    # Permissions (subset of user's permissions)
    permissions: set[Permission] = field(default_factory=set)
    entity_ids: list[UUID] | None = None  # Restrict to specific entities

    # Limits
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10000

    # Usage tracking
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    total_requests: int = 0

    # Status
    is_active: bool = True
    expires_at: datetime | None = None

    created_at: datetime = field(default_factory=_utc_now)
    created_by: UUID | None = None
    revoked_at: datetime | None = None
    revoked_by: UUID | None = None

    @property
    def is_valid(self) -> bool:
        """Whether API key is valid."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < _utc_now():
            return False
        return True

    def record_usage(self, ip_address: str | None = None) -> None:
        """Record API key usage."""
        self.last_used_at = _utc_now()
        self.last_used_ip = ip_address
        self.total_requests += 1


@dataclass
class PasswordResetToken:
    """A password reset token."""

    user_id: UUID
    token_hash: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime = field(
        default_factory=lambda: _utc_now() + timedelta(hours=24)
    )
    used_at: datetime | None = None
    ip_address: str | None = None

    @property
    def is_valid(self) -> bool:
        """Whether token is still valid."""
        if self.used_at is not None:
            return False
        if self.expires_at < _utc_now():
            return False
        return True

    def use(self) -> None:
        """Mark token as used."""
        self.used_at = _utc_now()


@dataclass
class AuditLogEntry:
    """An audit log entry for security tracking."""

    user_id: UUID | None
    action: str
    resource_type: str
    id: UUID = field(default_factory=uuid4)
    resource_id: UUID | None = None
    timestamp: datetime = field(default_factory=_utc_now)

    # Request context
    ip_address: str | None = None
    user_agent: str | None = None
    session_id: UUID | None = None
    api_key_id: UUID | None = None

    # Change details
    old_value: str | None = None  # JSON of old value
    new_value: str | None = None  # JSON of new value
    metadata: dict | None = None

    # Status
    success: bool = True
    error_message: str | None = None


@dataclass
class TokenPayload:
    """JWT token payload for serialization."""

    sub: str  # User ID
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    jti: str  # JWT ID (for revocation)
    role: str
    permissions: list[str]
    entity_ids: list[str] | None = None
    session_id: str | None = None
    type: str = "access"  # "access" or "refresh"
