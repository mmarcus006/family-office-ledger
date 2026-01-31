"""Tests for authentication and authorization services."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from family_office_ledger.domain.auth import (
    Permission,
    Session,
    User,
    UserRole,
    UserStatus,
)
from family_office_ledger.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    ValidationError,
)
from family_office_ledger.services.auth import (
    AuthorizationService,
    AuthService,
    PasswordHasher,
    TokenService,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def password_hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def token_service() -> TokenService:
    return TokenService(secret_key="test-secret-key-for-testing-only")


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService()


@pytest.fixture
def authorization_service() -> AuthorizationService:
    return AuthorizationService()


@pytest.fixture
def owner_user() -> User:
    return User(
        email="owner@example.com",
        role=UserRole.OWNER,
        name="Owner User",
        status=UserStatus.ACTIVE,
        email_verified=True,
        password_hash="pbkdf2_sha256$600000$" + "a" * 64 + "$" + "b" * 64,
    )


@pytest.fixture
def admin_user() -> User:
    return User(
        email="admin@example.com",
        role=UserRole.ADMIN,
        name="Admin User",
        status=UserStatus.ACTIVE,
        email_verified=True,
        password_hash="pbkdf2_sha256$600000$" + "a" * 64 + "$" + "b" * 64,
    )


@pytest.fixture
def viewer_user() -> User:
    return User(
        email="viewer@example.com",
        role=UserRole.VIEWER,
        name="Viewer User",
        status=UserStatus.ACTIVE,
        email_verified=True,
    )


@pytest.fixture
def restricted_user() -> User:
    """User with access to specific entities only."""
    entity_id_1 = uuid4()
    entity_id_2 = uuid4()
    return User(
        email="restricted@example.com",
        role=UserRole.VIEWER,
        name="Restricted User",
        status=UserStatus.ACTIVE,
        email_verified=True,
        entity_ids=[entity_id_1, entity_id_2],
    )


# =============================================================================
# TestPasswordHasherHash
# =============================================================================


class TestPasswordHasherHash:
    def test_hash_returns_formatted_string(self, password_hasher: PasswordHasher):
        password = "SecurePassword123"
        hashed = password_hasher.hash(password)

        parts = hashed.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert parts[1] == "600000"
        assert len(parts[2]) == 64  # Salt is 32 bytes hex = 64 chars
        assert len(parts[3]) == 64  # Hash is 32 bytes hex = 64 chars

    def test_hash_produces_different_hashes_for_same_password(
        self, password_hasher: PasswordHasher
    ):
        password = "SecurePassword123"
        hash1 = password_hasher.hash(password)
        hash2 = password_hasher.hash(password)

        # Different salts should produce different hashes
        assert hash1 != hash2

    def test_hash_handles_empty_password(self, password_hasher: PasswordHasher):
        hashed = password_hasher.hash("")

        parts = hashed.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"

    def test_hash_handles_unicode_password(self, password_hasher: PasswordHasher):
        password = "SecurePassword123"
        hashed = password_hasher.hash(password)

        parts = hashed.split("$")
        assert len(parts) == 4

    def test_hash_handles_long_password(self, password_hasher: PasswordHasher):
        password = "A" * 10000
        hashed = password_hasher.hash(password)

        parts = hashed.split("$")
        assert len(parts) == 4


class TestPasswordHasherVerify:
    def test_verify_returns_true_for_correct_password(
        self, password_hasher: PasswordHasher
    ):
        password = "SecurePassword123"
        hashed = password_hasher.hash(password)

        assert password_hasher.verify(password, hashed) is True

    def test_verify_returns_false_for_wrong_password(
        self, password_hasher: PasswordHasher
    ):
        password = "SecurePassword123"
        hashed = password_hasher.hash(password)

        assert password_hasher.verify("WrongPassword123", hashed) is False

    def test_verify_returns_false_for_invalid_hash_format(
        self, password_hasher: PasswordHasher
    ):
        assert password_hasher.verify("password", "invalid-hash") is False

    def test_verify_returns_false_for_wrong_algorithm(
        self, password_hasher: PasswordHasher
    ):
        bad_hash = "bcrypt$600000$salt$hash"
        assert password_hasher.verify("password", bad_hash) is False

    def test_verify_returns_false_for_empty_hash(self, password_hasher: PasswordHasher):
        assert password_hasher.verify("password", "") is False

    def test_verify_returns_false_for_none_hash(self, password_hasher: PasswordHasher):
        # Should handle AttributeError gracefully
        assert password_hasher.verify("password", None) is False  # type: ignore

    def test_verify_handles_empty_password(self, password_hasher: PasswordHasher):
        hashed = password_hasher.hash("")
        assert password_hasher.verify("", hashed) is True
        assert password_hasher.verify("nonempty", hashed) is False


class TestPasswordHasherNeedsRehash:
    def test_needs_rehash_returns_false_for_current_iterations(
        self, password_hasher: PasswordHasher
    ):
        hashed = password_hasher.hash("password")
        assert password_hasher.needs_rehash(hashed) is False

    def test_needs_rehash_returns_true_for_fewer_iterations(
        self, password_hasher: PasswordHasher
    ):
        old_hash = "pbkdf2_sha256$100000$salt$hash"
        assert password_hasher.needs_rehash(old_hash) is True

    def test_needs_rehash_returns_true_for_invalid_format(
        self, password_hasher: PasswordHasher
    ):
        assert password_hasher.needs_rehash("invalid") is True

    def test_needs_rehash_returns_true_for_empty_string(
        self, password_hasher: PasswordHasher
    ):
        assert password_hasher.needs_rehash("") is True

    def test_needs_rehash_returns_true_for_none(self, password_hasher: PasswordHasher):
        # Should handle AttributeError gracefully
        assert password_hasher.needs_rehash(None) is True  # type: ignore


# =============================================================================
# TestTokenService
# =============================================================================


class TestTokenServiceCreateAccessToken:
    def test_creates_token_with_correct_format(
        self, token_service: TokenService, owner_user: User
    ):
        token, payload = token_service.create_access_token(owner_user)

        assert token.startswith("access.")
        parts = token.split(".")
        assert len(parts) == 3
        assert parts[0] == "access"
        assert parts[2] == str(owner_user.id)

    def test_creates_payload_with_user_info(
        self, token_service: TokenService, owner_user: User
    ):
        token, payload = token_service.create_access_token(owner_user)

        assert payload.sub == str(owner_user.id)
        assert payload.role == owner_user.role.value
        assert payload.type == "access"
        assert payload.jti is not None

    def test_creates_payload_with_expiration(
        self, token_service: TokenService, owner_user: User
    ):
        before = datetime.now(UTC)
        token, payload = token_service.create_access_token(owner_user)
        after = datetime.now(UTC)

        assert payload.exp > before
        expected_min = before + timedelta(
            minutes=token_service.access_token_expire_minutes - 1
        )
        expected_max = after + timedelta(
            minutes=token_service.access_token_expire_minutes + 1
        )
        assert expected_min < payload.exp < expected_max

    def test_creates_payload_with_permissions(
        self, token_service: TokenService, owner_user: User
    ):
        token, payload = token_service.create_access_token(owner_user)

        assert len(payload.permissions) > 0
        assert all(isinstance(p, str) for p in payload.permissions)

    def test_includes_session_id_when_provided(
        self, token_service: TokenService, owner_user: User
    ):
        session_id = uuid4()
        token, payload = token_service.create_access_token(owner_user, session_id)

        assert payload.session_id == str(session_id)

    def test_session_id_is_none_when_not_provided(
        self, token_service: TokenService, owner_user: User
    ):
        token, payload = token_service.create_access_token(owner_user)

        assert payload.session_id is None

    def test_includes_entity_ids_when_user_has_restrictions(
        self, token_service: TokenService, restricted_user: User
    ):
        token, payload = token_service.create_access_token(restricted_user)

        assert payload.entity_ids is not None
        assert len(payload.entity_ids) == 2

    def test_entity_ids_none_for_unrestricted_user(
        self, token_service: TokenService, owner_user: User
    ):
        token, payload = token_service.create_access_token(owner_user)

        assert payload.entity_ids is None


class TestTokenServiceCreateRefreshToken:
    def test_creates_token_with_correct_format(
        self, token_service: TokenService, owner_user: User
    ):
        session_id = uuid4()
        token, payload = token_service.create_refresh_token(owner_user, session_id)

        assert token.startswith("refresh.")
        parts = token.split(".")
        assert len(parts) == 3
        assert parts[0] == "refresh"
        assert parts[2] == str(owner_user.id)

    def test_creates_payload_with_refresh_type(
        self, token_service: TokenService, owner_user: User
    ):
        session_id = uuid4()
        token, payload = token_service.create_refresh_token(owner_user, session_id)

        assert payload.type == "refresh"

    def test_creates_payload_with_longer_expiration(
        self, token_service: TokenService, owner_user: User
    ):
        session_id = uuid4()
        before = datetime.now(UTC)
        token, payload = token_service.create_refresh_token(owner_user, session_id)

        expected_min = before + timedelta(
            days=token_service.refresh_token_expire_days - 1
        )
        assert payload.exp > expected_min

    def test_includes_session_id(self, token_service: TokenService, owner_user: User):
        session_id = uuid4()
        token, payload = token_service.create_refresh_token(owner_user, session_id)

        assert payload.session_id == str(session_id)

    def test_refresh_token_has_empty_permissions(
        self, token_service: TokenService, owner_user: User
    ):
        session_id = uuid4()
        token, payload = token_service.create_refresh_token(owner_user, session_id)

        assert payload.permissions == []


class TestTokenServiceVerifyToken:
    def test_verifies_valid_access_token(
        self, token_service: TokenService, owner_user: User
    ):
        token, _ = token_service.create_access_token(owner_user)
        payload = token_service.verify_token(token)

        assert payload is not None
        assert payload.sub == str(owner_user.id)
        assert payload.type == "access"

    def test_verifies_valid_refresh_token(
        self, token_service: TokenService, owner_user: User
    ):
        session_id = uuid4()
        token, _ = token_service.create_refresh_token(owner_user, session_id)
        payload = token_service.verify_token(token)

        assert payload is not None
        assert payload.type == "refresh"

    def test_returns_none_for_invalid_format(self, token_service: TokenService):
        assert token_service.verify_token("invalid") is None

    def test_returns_none_for_empty_string(self, token_service: TokenService):
        assert token_service.verify_token("") is None

    def test_returns_none_for_wrong_part_count(self, token_service: TokenService):
        assert token_service.verify_token("only.two") is None
        assert token_service.verify_token("too.many.parts.here") is None


class TestTokenServiceHashToken:
    def test_hash_token_returns_sha256_hex(self, token_service: TokenService):
        token = "test-token"
        hashed = token_service.hash_token(token)

        assert len(hashed) == 64  # SHA256 hex length
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_is_deterministic(self, token_service: TokenService):
        token = "test-token"
        hash1 = token_service.hash_token(token)
        hash2 = token_service.hash_token(token)

        assert hash1 == hash2

    def test_different_tokens_produce_different_hashes(
        self, token_service: TokenService
    ):
        hash1 = token_service.hash_token("token1")
        hash2 = token_service.hash_token("token2")

        assert hash1 != hash2


# =============================================================================
# TestAuthServiceRegisterUser
# =============================================================================


class TestAuthServiceRegisterUser:
    def test_registers_user_with_valid_data(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="newuser@example.com",
            password="SecurePassword123",
            name="New User",
        )

        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.role == UserRole.VIEWER  # Default role
        assert user.status == UserStatus.PENDING

    def test_normalizes_email_to_lowercase(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="  NewUser@EXAMPLE.COM  ",
            password="SecurePassword123",
        )

        assert user.email == "newuser@example.com"

    def test_hashes_password_securely(self, auth_service: AuthService):
        password = "SecurePassword123"
        user = auth_service.register_user(
            email="user@example.com",
            password=password,
        )

        assert user.password_hash is not None
        assert password not in user.password_hash
        assert user.password_hash.startswith("pbkdf2_sha256$")

    def test_sets_password_changed_at(self, auth_service: AuthService):
        before = datetime.now(UTC)
        user = auth_service.register_user(
            email="user@example.com",
            password="SecurePassword123",
        )
        after = datetime.now(UTC)

        assert user.password_changed_at is not None
        assert before <= user.password_changed_at <= after

    def test_assigns_specified_role(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="admin@example.com",
            password="SecurePassword123",
            role=UserRole.ADMIN,
        )

        assert user.role == UserRole.ADMIN

    def test_tracks_creator(self, auth_service: AuthService):
        creator_id = uuid4()
        user = auth_service.register_user(
            email="user@example.com",
            password="SecurePassword123",
            created_by=creator_id,
        )

        assert user.created_by == creator_id

    def test_raises_for_invalid_email_no_at(self, auth_service: AuthService):
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(
                email="invalidemail.com",
                password="SecurePassword123",
            )

        assert "Invalid email format" in str(exc_info.value)

    def test_raises_for_invalid_email_no_dot(self, auth_service: AuthService):
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(
                email="invalid@emailcom",
                password="SecurePassword123",
            )

        assert "Invalid email format" in str(exc_info.value)

    def test_raises_for_password_too_short(self, auth_service: AuthService):
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(
                email="user@example.com",
                password="Short1",  # Less than 12 characters
            )

        assert "at least 12 characters" in str(exc_info.value)

    def test_raises_for_password_no_uppercase(self, auth_service: AuthService):
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(
                email="user@example.com",
                password="lowercaseonly123",
            )

        assert "uppercase" in str(exc_info.value)

    def test_raises_for_password_no_lowercase(self, auth_service: AuthService):
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(
                email="user@example.com",
                password="UPPERCASEONLY123",
            )

        assert "lowercase" in str(exc_info.value)

    def test_raises_for_password_no_digit(self, auth_service: AuthService):
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(
                email="user@example.com",
                password="NoDigitsHere!",
            )

        assert "numbers" in str(exc_info.value)


# =============================================================================
# TestAuthServiceChangePassword
# =============================================================================


class TestAuthServiceChangePassword:
    def test_changes_password_with_valid_current_password(
        self, auth_service: AuthService
    ):
        current_password = "OldSecurePassword123"
        new_password = "NewSecurePassword456"

        user = auth_service.register_user(
            email="user@example.com",
            password=current_password,
        )

        auth_service.change_password(user, current_password, new_password)

        # Verify new password works
        assert auth_service.password_hasher.verify(
            new_password, user.password_hash or ""
        )
        # Verify old password no longer works
        assert not auth_service.password_hasher.verify(
            current_password, user.password_hash or ""
        )

    def test_updates_password_changed_at(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="user@example.com",
            password="OldSecurePassword123",
        )
        original_changed_at = user.password_changed_at

        auth_service.change_password(
            user, "OldSecurePassword123", "NewSecurePassword456"
        )

        assert user.password_changed_at > original_changed_at  # type: ignore

    def test_clears_must_change_password_flag(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="user@example.com",
            password="OldSecurePassword123",
        )
        user.must_change_password = True

        auth_service.change_password(
            user, "OldSecurePassword123", "NewSecurePassword456"
        )

        assert user.must_change_password is False

    def test_raises_for_wrong_current_password(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="user@example.com",
            password="OldSecurePassword123",
        )

        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.change_password(
                user, "WrongPassword123", "NewSecurePassword456"
            )

        assert "Current password is incorrect" in str(exc_info.value)

    def test_raises_for_weak_new_password(self, auth_service: AuthService):
        user = auth_service.register_user(
            email="user@example.com",
            password="OldSecurePassword123",
        )

        with pytest.raises(ValidationError):
            auth_service.change_password(user, "OldSecurePassword123", "weak")


# =============================================================================
# TestAuthorizationService
# =============================================================================


class TestAuthorizationServiceCheckPermission:
    def test_returns_true_for_owner_with_any_permission(
        self, authorization_service: AuthorizationService, owner_user: User
    ):
        assert (
            authorization_service.check_permission(owner_user, Permission.ENTITY_DELETE)
            is True
        )
        assert (
            authorization_service.check_permission(
                owner_user, Permission.USER_MANAGE_ROLES
            )
            is True
        )

    def test_returns_true_for_admin_with_allowed_permission(
        self, authorization_service: AuthorizationService, admin_user: User
    ):
        assert (
            authorization_service.check_permission(admin_user, Permission.ENTITY_CREATE)
            is True
        )
        assert (
            authorization_service.check_permission(admin_user, Permission.USER_CREATE)
            is True
        )

    def test_returns_false_for_admin_without_permission(
        self, authorization_service: AuthorizationService, admin_user: User
    ):
        # Admin cannot delete entities or delete users
        assert (
            authorization_service.check_permission(admin_user, Permission.ENTITY_DELETE)
            is False
        )
        assert (
            authorization_service.check_permission(admin_user, Permission.USER_DELETE)
            is False
        )

    def test_returns_true_for_viewer_with_read_permission(
        self, authorization_service: AuthorizationService, viewer_user: User
    ):
        assert (
            authorization_service.check_permission(viewer_user, Permission.ENTITY_READ)
            is True
        )
        assert (
            authorization_service.check_permission(viewer_user, Permission.REPORT_VIEW)
            is True
        )

    def test_returns_false_for_viewer_with_write_permission(
        self, authorization_service: AuthorizationService, viewer_user: User
    ):
        assert (
            authorization_service.check_permission(
                viewer_user, Permission.ENTITY_CREATE
            )
            is False
        )
        assert (
            authorization_service.check_permission(
                viewer_user, Permission.TRANSACTION_CREATE
            )
            is False
        )

    def test_returns_true_for_accessible_entity(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        # User can access their restricted entities
        accessible_entity_id = restricted_user.entity_ids[0]  # type: ignore
        assert (
            authorization_service.check_permission(
                restricted_user, Permission.ENTITY_READ, accessible_entity_id
            )
            is True
        )

    def test_returns_false_for_inaccessible_entity(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        # User cannot access entities not in their list
        other_entity_id = uuid4()
        assert (
            authorization_service.check_permission(
                restricted_user, Permission.ENTITY_READ, other_entity_id
            )
            is False
        )

    def test_unrestricted_user_can_access_any_entity(
        self, authorization_service: AuthorizationService, owner_user: User
    ):
        random_entity_id = uuid4()
        assert (
            authorization_service.check_permission(
                owner_user, Permission.ENTITY_READ, random_entity_id
            )
            is True
        )


class TestAuthorizationServiceRequirePermission:
    def test_does_not_raise_when_user_has_permission(
        self, authorization_service: AuthorizationService, owner_user: User
    ):
        # Should not raise
        authorization_service.require_permission(
            owner_user, Permission.ENTITY_DELETE, resource="entities"
        )

    def test_raises_permission_denied_when_lacking_permission(
        self, authorization_service: AuthorizationService, viewer_user: User
    ):
        with pytest.raises(PermissionDeniedError) as exc_info:
            authorization_service.require_permission(
                viewer_user, Permission.ENTITY_CREATE, resource="entities"
            )

        assert "entity:create" in str(exc_info.value)
        assert "entities" in str(exc_info.value)

    def test_raises_permission_denied_for_inaccessible_entity(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        other_entity_id = uuid4()
        with pytest.raises(PermissionDeniedError):
            authorization_service.require_permission(
                restricted_user,
                Permission.ENTITY_READ,
                entity_id=other_entity_id,
                resource="entity",
            )


class TestAuthorizationServiceGetAccessibleEntityIds:
    def test_returns_none_for_unrestricted_user(
        self, authorization_service: AuthorizationService, owner_user: User
    ):
        result = authorization_service.get_accessible_entity_ids(owner_user)
        assert result is None

    def test_returns_entity_ids_for_restricted_user(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        result = authorization_service.get_accessible_entity_ids(restricted_user)

        assert result is not None
        assert len(result) == 2
        assert result == restricted_user.entity_ids


class TestAuthorizationServiceFilterEntities:
    def test_returns_all_entities_for_unrestricted_user(
        self, authorization_service: AuthorizationService, owner_user: User
    ):
        entity_ids = [uuid4(), uuid4(), uuid4()]
        result = authorization_service.filter_entities(owner_user, entity_ids)

        assert result == entity_ids

    def test_filters_to_accessible_entities_for_restricted_user(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        accessible_id = restricted_user.entity_ids[0]  # type: ignore
        inaccessible_id = uuid4()
        entity_ids = [accessible_id, inaccessible_id]

        result = authorization_service.filter_entities(restricted_user, entity_ids)

        assert accessible_id in result
        assert inaccessible_id not in result
        assert len(result) == 1

    def test_returns_empty_list_when_no_accessible_entities(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        entity_ids = [uuid4(), uuid4()]  # None are accessible
        result = authorization_service.filter_entities(restricted_user, entity_ids)

        assert result == []

    def test_preserves_order_of_accessible_entities(
        self, authorization_service: AuthorizationService, restricted_user: User
    ):
        id1 = restricted_user.entity_ids[0]  # type: ignore
        id2 = restricted_user.entity_ids[1]  # type: ignore
        other = uuid4()
        entity_ids = [id1, other, id2]

        result = authorization_service.filter_entities(restricted_user, entity_ids)

        assert result == [id1, id2]


# =============================================================================
# TestSessionDomain
# =============================================================================


class TestSessionDomain:
    def test_session_created_with_defaults(self):
        user_id = uuid4()
        session = Session(user_id=user_id)

        assert session.user_id == user_id
        assert session.is_active is True
        assert session.revoked_at is None

    def test_session_revoke(self):
        session = Session(user_id=uuid4())
        session.revoke(reason="logout")

        assert session.is_active is False
        assert session.revoked_at is not None
        assert session.revoked_reason == "logout"

    def test_session_is_valid_when_active_and_not_expired(self):
        session = Session(
            user_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert session.is_valid is True

    def test_session_is_invalid_when_revoked(self):
        session = Session(user_id=uuid4())
        session.revoke()

        assert session.is_valid is False

    def test_session_is_invalid_when_expired(self):
        session = Session(
            user_id=uuid4(),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        assert session.is_valid is False

    def test_session_touch_updates_last_activity(self):
        session = Session(user_id=uuid4())
        original = session.last_activity_at

        session.touch()

        assert session.last_activity_at >= original


# =============================================================================
# TestUserDomain
# =============================================================================


class TestUserDomain:
    def test_user_is_active_when_status_active_and_email_verified(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
            email_verified=True,
        )

        assert user.is_active is True

    def test_user_is_not_active_when_pending(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.PENDING,
            email_verified=True,
        )

        assert user.is_active is False

    def test_user_is_not_active_when_email_not_verified(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
            email_verified=False,
        )

        assert user.is_active is False

    def test_user_is_locked_when_status_locked(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.LOCKED,
        )

        assert user.is_locked is True

    def test_user_is_locked_when_locked_until_future(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
            locked_until=datetime.now(UTC) + timedelta(hours=1),
        )

        assert user.is_locked is True

    def test_user_is_not_locked_when_locked_until_past(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
            locked_until=datetime.now(UTC) - timedelta(hours=1),
        )

        assert user.is_locked is False

    def test_record_login_updates_fields(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            failed_login_attempts=3,
            locked_until=datetime.now(UTC) + timedelta(hours=1),
        )

        user.record_login(ip_address="192.168.1.1")

        assert user.last_login_at is not None
        assert user.last_login_ip == "192.168.1.1"
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_record_failed_login_increments_counter(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
        )

        user.record_failed_login()

        assert user.failed_login_attempts == 1

    def test_record_failed_login_locks_after_max_attempts(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            failed_login_attempts=4,
        )

        user.record_failed_login(max_attempts=5)

        assert user.failed_login_attempts == 5
        assert user.status == UserStatus.LOCKED
        assert user.locked_until is not None

    def test_has_permission_returns_true_for_role_permission(self):
        user = User(
            email="viewer@example.com",
            role=UserRole.VIEWER,
        )

        assert user.has_permission(Permission.ENTITY_READ) is True

    def test_has_permission_returns_false_for_missing_permission(self):
        user = User(
            email="viewer@example.com",
            role=UserRole.VIEWER,
        )

        assert user.has_permission(Permission.ENTITY_CREATE) is False

    def test_can_access_entity_returns_true_when_unrestricted(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            entity_ids=None,
        )

        assert user.can_access_entity(uuid4()) is True

    def test_can_access_entity_returns_true_for_allowed_entity(self):
        entity_id = uuid4()
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            entity_ids=[entity_id],
        )

        assert user.can_access_entity(entity_id) is True

    def test_can_access_entity_returns_false_for_disallowed_entity(self):
        user = User(
            email="user@example.com",
            role=UserRole.VIEWER,
            entity_ids=[uuid4()],
        )

        assert user.can_access_entity(uuid4()) is False
