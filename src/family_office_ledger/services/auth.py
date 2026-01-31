"""Authentication and authorization service.

Provides:
- User registration and login
- JWT token generation and validation
- Password hashing and verification
- Session management
- Permission checking
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from family_office_ledger.config import get_settings
from family_office_ledger.domain.auth import (
    MFAMethod,
    PasswordResetToken,
    Permission,
    Session,
    TokenPayload,
    User,
    UserRole,
    UserStatus,
)
from family_office_ledger.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    ValidationError,
)
from family_office_ledger.logging_config import get_logger

logger = get_logger(__name__)


class PasswordHasher:
    """Secure password hashing using PBKDF2."""

    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 600_000  # OWASP 2023 recommendation
    SALT_LENGTH = 32

    @classmethod
    def hash(cls, password: str) -> str:
        """Hash a password securely.

        Args:
            password: Plain text password

        Returns:
            Hash string in format: algorithm$iterations$salt$hash
        """
        salt = secrets.token_hex(cls.SALT_LENGTH)
        hash_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.ITERATIONS,
        )
        hash_hex = hash_bytes.hex()
        return f"{cls.ALGORITHM}${cls.ITERATIONS}${salt}${hash_hex}"

    @classmethod
    def verify(cls, password: str, hash_string: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password to verify
            hash_string: Stored hash string

        Returns:
            True if password matches
        """
        try:
            algorithm, iterations, salt, stored_hash = hash_string.split("$")
            if algorithm != cls.ALGORITHM:
                return False

            hash_bytes = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            )
            computed_hash = hash_bytes.hex()

            # Constant-time comparison to prevent timing attacks
            return secrets.compare_digest(computed_hash, stored_hash)
        except (ValueError, AttributeError):
            return False

    @classmethod
    def needs_rehash(cls, hash_string: str) -> bool:
        """Check if hash needs to be upgraded (e.g., more iterations)."""
        try:
            _, iterations, _, _ = hash_string.split("$")
            return int(iterations) < cls.ITERATIONS
        except (ValueError, AttributeError):
            return True


class TokenService:
    """JWT token generation and validation.

    Note: In production, use python-jose or PyJWT for actual JWT.
    This is a simplified implementation for the domain model.
    """

    def __init__(self, secret_key: str | None = None) -> None:
        settings = get_settings()
        self.secret_key = secret_key or settings.secret_key
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days

    def create_access_token(
        self,
        user: User,
        session_id: UUID | None = None,
    ) -> tuple[str, TokenPayload]:
        """Create an access token for a user.

        Args:
            user: User to create token for
            session_id: Optional session ID to include

        Returns:
            Tuple of (token string, payload)
        """
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=self.access_token_expire_minutes)
        jti = secrets.token_urlsafe(32)

        payload = TokenPayload(
            sub=str(user.id),
            exp=expires,
            iat=now,
            jti=jti,
            role=user.role.value,
            permissions=[p.value for p in user.permissions],
            entity_ids=[str(e) for e in user.entity_ids] if user.entity_ids else None,
            session_id=str(session_id) if session_id else None,
            type="access",
        )

        # ============================================================================
        # SECURITY WARNING: PLACEHOLDER IMPLEMENTATION - NOT FOR PRODUCTION USE
        # ============================================================================
        # This token format is INSECURE and exposes the user ID directly.
        # Before production deployment, replace with proper JWT encoding using
        # python-jose or PyJWT:
        #
        #   from jose import jwt
        #   token = jwt.encode(payload.model_dump(), self.secret_key, algorithm="HS256")
        #
        # The current format allows anyone to:
        # 1. Extract the user ID from the token
        # 2. Forge tokens for any user (no signature verification)
        # ============================================================================
        token = f"access.{jti}.{user.id}"

        logger.debug(
            "access_token_created",
            user_id=str(user.id),
            expires=expires.isoformat(),
        )

        return token, payload

    def create_refresh_token(
        self,
        user: User,
        session_id: UUID,
    ) -> tuple[str, TokenPayload]:
        """Create a refresh token for a user.

        Args:
            user: User to create token for
            session_id: Session ID to associate with token

        Returns:
            Tuple of (token string, payload)
        """
        now = datetime.now(UTC)
        expires = now + timedelta(days=self.refresh_token_expire_days)
        jti = secrets.token_urlsafe(32)

        payload = TokenPayload(
            sub=str(user.id),
            exp=expires,
            iat=now,
            jti=jti,
            role=user.role.value,
            permissions=[],  # Refresh tokens don't carry permissions
            session_id=str(session_id),
            type="refresh",
        )

        # SECURITY WARNING: Placeholder token - see access token warning above
        token = f"refresh.{jti}.{user.id}"

        logger.debug(
            "refresh_token_created",
            user_id=str(user.id),
            session_id=str(session_id),
        )

        return token, payload

    def verify_token(self, token: str) -> TokenPayload | None:
        """Verify and decode a token.

        Args:
            token: Token string to verify

        Returns:
            TokenPayload if valid, None if invalid

        Note: This is a placeholder. In production, use proper JWT verification.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            token_type, jti, user_id = parts

            # ============================================================================
            # SECURITY WARNING: AUTHENTICATION BYPASS - NOT FOR PRODUCTION USE
            # ============================================================================
            # This placeholder implementation DOES NOT verify tokens and will
            # accept ANY token that matches the format "type.jti.user_id".
            #
            # CRITICAL VULNERABILITIES:
            # 1. No signature verification - attackers can forge tokens
            # 2. No expiration checking - tokens never expire
            # 3. User ID extracted directly from token - trivial impersonation
            # 4. Permissions hardcoded to empty - broken authorization
            #
            # Before production, implement proper JWT verification:
            #
            #   from jose import jwt, JWTError
            #   try:
            #       payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            #       return TokenPayload(**payload)
            #   except JWTError:
            #       return None
            # ============================================================================
            return TokenPayload(
                sub=user_id,
                exp=datetime.now(UTC) + timedelta(hours=1),
                iat=datetime.now(UTC),
                jti=jti,
                role="viewer",
                permissions=[],
                type=token_type,
            )
        except Exception:
            return None

    def hash_token(self, token: str) -> str:
        """Hash a token for storage (for revocation checking)."""
        return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Main authentication and authorization service."""

    def __init__(
        self,
        user_repository: Any = None,  # Would be UserRepository in full impl
        session_repository: Any = None,
    ) -> None:
        self.users = user_repository
        self.sessions = session_repository
        self.password_hasher = PasswordHasher()
        self.token_service = TokenService()

    def register_user(
        self,
        email: str,
        password: str,
        name: str | None = None,
        role: UserRole = UserRole.VIEWER,
        created_by: UUID | None = None,
    ) -> User:
        """Register a new user.

        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            name: User's display name
            role: User's role
            created_by: ID of user creating this account

        Returns:
            Created User object

        Raises:
            ValidationError: If email is invalid or already exists
        """
        # Validate email format
        if "@" not in email or "." not in email:
            raise ValidationError("Invalid email format", context={"email": email})

        # Validate password strength
        self._validate_password_strength(password)

        # Hash password
        password_hash = self.password_hasher.hash(password)

        user = User(
            email=email.lower().strip(),
            name=name,
            role=role,
            password_hash=password_hash,
            password_changed_at=datetime.now(UTC),
            status=UserStatus.PENDING,
            created_by=created_by,
        )

        logger.info(
            "user_registered",
            user_id=str(user.id),
            email=user.email,
            role=role.value,
        )

        return user

    def _validate_password_strength(self, password: str) -> None:
        """Validate password meets minimum requirements."""
        if len(password) < 12:
            raise ValidationError(
                "Password must be at least 12 characters",
                context={"requirement": "min_length"},
            )

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        # has_special could be used for stricter requirements in the future
        _ = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit):
            raise ValidationError(
                "Password must contain uppercase, lowercase, and numbers",
                context={"requirement": "complexity"},
            )

    def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, Session, str, str]:
        """Authenticate a user and create a session.

        Args:
            email: User's email
            password: User's password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (user, session, access_token, refresh_token)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # In full implementation, would fetch user from repository
        # This is a placeholder for the pattern
        user: User | None = None  # self.users.get_by_email(email)

        if user is None:
            logger.warning("login_failed_user_not_found", email=email)
            raise AuthenticationError("Invalid credentials")

        if user.is_locked:
            logger.warning("login_failed_account_locked", user_id=str(user.id))
            raise AuthenticationError("Account is locked. Please try again later.")

        if not user.is_active:
            logger.warning("login_failed_account_inactive", user_id=str(user.id))
            raise AuthenticationError("Account is not active")

        if not self.password_hasher.verify(password, user.password_hash or ""):
            user.record_failed_login()
            logger.warning(
                "login_failed_invalid_password",
                user_id=str(user.id),
                attempts=user.failed_login_attempts,
            )
            raise AuthenticationError("Invalid credentials")

        # Check if MFA is required
        if user.mfa_method != MFAMethod.NONE and user.mfa_verified:
            # Would return partial auth state requiring MFA
            pass

        # Create session
        session = Session(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type="web",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        # Generate tokens
        access_token, _ = self.token_service.create_access_token(user, session.id)
        refresh_token, _ = self.token_service.create_refresh_token(user, session.id)

        # Store token hashes for revocation
        session.token_hash = self.token_service.hash_token(access_token)
        session.refresh_token_hash = self.token_service.hash_token(refresh_token)

        # Update user login info
        user.record_login(ip_address)

        logger.info(
            "user_authenticated",
            user_id=str(user.id),
            session_id=str(session.id),
        )

        return user, session, access_token, refresh_token

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> tuple[str, TokenPayload]:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Tuple of (new_access_token, payload)

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        payload = self.token_service.verify_token(refresh_token)
        if payload is None or payload.type != "refresh":
            raise AuthenticationError("Invalid refresh token")

        # In full implementation, verify session is still valid
        # and user hasn't been deactivated

        # Would fetch user from repository
        user: User | None = None

        if user is None:
            raise AuthenticationError("User not found")

        session_id = UUID(payload.session_id) if payload.session_id else None
        access_token, new_payload = self.token_service.create_access_token(
            user, session_id
        )

        logger.debug("access_token_refreshed", user_id=payload.sub)

        return access_token, new_payload

    def logout(self, session_id: UUID, reason: str = "user_logout") -> None:
        """Logout a user by revoking their session.

        Args:
            session_id: Session to revoke
            reason: Reason for logout
        """
        # In full implementation, would fetch and update session
        logger.info("user_logged_out", session_id=str(session_id), reason=reason)

    def logout_all_sessions(self, user_id: UUID, reason: str = "logout_all") -> int:
        """Logout all sessions for a user.

        Args:
            user_id: User whose sessions to revoke
            reason: Reason for logout

        Returns:
            Number of sessions revoked
        """
        # In full implementation, would revoke all sessions
        logger.info("all_sessions_revoked", user_id=str(user_id), reason=reason)
        return 0

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change a user's password.

        Args:
            user: User changing password
            current_password: Current password for verification
            new_password: New password

        Raises:
            AuthenticationError: If current password is wrong
            ValidationError: If new password is weak
        """
        if not self.password_hasher.verify(current_password, user.password_hash or ""):
            raise AuthenticationError("Current password is incorrect")

        self._validate_password_strength(new_password)

        user.password_hash = self.password_hasher.hash(new_password)
        user.password_changed_at = datetime.now(UTC)
        user.must_change_password = False

        # Optionally revoke all other sessions
        self.logout_all_sessions(user.id, reason="password_changed")

        logger.info("password_changed", user_id=str(user.id))

    def request_password_reset(self, email: str) -> PasswordResetToken | None:
        """Request a password reset token.

        Args:
            email: User's email address

        Returns:
            Reset token if user exists, None otherwise
            (Always returns None to external callers to prevent enumeration)
        """
        # In full implementation, would look up user
        # and create reset token if found
        logger.info("password_reset_requested", email=email)
        return None

    def reset_password(
        self,
        token: str,
        new_password: str,
    ) -> bool:
        """Reset password using a reset token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            True if successful

        Raises:
            AuthenticationError: If token is invalid
            ValidationError: If password is weak
        """
        # In full implementation, would verify token and update password
        self._validate_password_strength(new_password)
        logger.info("password_reset_completed")
        return True


class AuthorizationService:
    """Service for checking user permissions."""

    def __init__(
        self,
        entity_permission_repository: Any = None,
    ) -> None:
        self.entity_permissions = entity_permission_repository

    def check_permission(
        self,
        user: User,
        permission: Permission,
        entity_id: UUID | None = None,
    ) -> bool:
        """Check if user has a permission.

        Args:
            user: User to check
            permission: Permission required
            entity_id: Optional entity to check against

        Returns:
            True if user has permission
        """
        # Check role-based permission
        if not user.has_permission(permission):
            return False

        # If entity-specific, check entity access
        # Note: Keeping explicit structure for future entity-specific override checks
        if entity_id is not None and not user.can_access_entity(entity_id):  # noqa: SIM103
            return False

        # TODO: Check for entity-specific overrides from repository

        return True

    def require_permission(
        self,
        user: User,
        permission: Permission,
        entity_id: UUID | None = None,
        resource: str = "resource",
    ) -> None:
        """Require a permission, raising if not met.

        Args:
            user: User to check
            permission: Permission required
            entity_id: Optional entity to check against
            resource: Resource name for error message

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        if not self.check_permission(user, permission, entity_id):
            logger.warning(
                "permission_denied",
                user_id=str(user.id),
                permission=permission.value,
                entity_id=str(entity_id) if entity_id else None,
            )
            raise PermissionDeniedError(
                action=permission.value,
                resource=resource,
            )

    def get_accessible_entity_ids(self, user: User) -> list[UUID] | None:
        """Get list of entity IDs the user can access.

        Args:
            user: User to check

        Returns:
            List of entity IDs, or None if user has access to all
        """
        return user.entity_ids

    def filter_entities(
        self,
        user: User,
        entity_ids: list[UUID],
    ) -> list[UUID]:
        """Filter a list of entity IDs to only those user can access.

        Args:
            user: User to check
            entity_ids: List of entity IDs to filter

        Returns:
            Filtered list of accessible entity IDs
        """
        if user.entity_ids is None:
            return entity_ids  # Has access to all

        return [eid for eid in entity_ids if eid in user.entity_ids]
