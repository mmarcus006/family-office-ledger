"""Centralized configuration management using pydantic-settings.

Configuration is loaded from environment variables with sensible defaults.
All settings can be overridden via environment variables or a .env file.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseType(str, Enum):
    """Supported database backends."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings have sensible defaults for development. Override via
    environment variables (prefixed with FOL_) or .env file.

    Examples:
        FOL_DATABASE_TYPE=postgres
        FOL_DATABASE_URL=postgresql://user:pass@localhost/fol
        FOL_LOG_LEVEL=DEBUG
        FOL_ENVIRONMENT=production
    """

    model_config = SettingsConfigDict(
        env_prefix="FOL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Family Office Ledger"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database
    database_type: DatabaseType = DatabaseType.SQLITE
    database_url: str | None = Field(
        default=None,
        description="Full database URL (for Postgres). Takes precedence over sqlite_path.",
    )
    sqlite_path: Path = Field(
        default=Path("family_office_ledger.db"),
        description="SQLite database file path (when database_type=sqlite)",
    )

    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format: 'json' for production, 'console' for development",
    )
    log_file: Path | None = Field(default=None, description="Optional log file path")

    # API Server
    # SECURITY NOTE: Default "0.0.0.0" binds to ALL network interfaces.
    # This is appropriate for containerized deployments (Docker, K8s) where
    # network isolation is handled at the infrastructure level.
    #
    # For non-containerized production deployments, consider:
    # - FOL_API_HOST=127.0.0.1 (localhost only, use reverse proxy)
    # - Using a reverse proxy (nginx, caddy) with TLS termination
    # - Firewall rules to restrict access to trusted networks
    #
    # Never expose this directly to the internet without TLS and authentication.
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = Field(
        default=False, description="Enable auto-reload (development only)"
    )
    api_workers: int = Field(default=1, ge=1, le=32)

    # Security (Phase 3 prep)
    # SECURITY WARNING: The default secret key is for development only.
    # In production, this MUST be set via FOL_SECRET_KEY environment variable
    # to a cryptographically secure random value (e.g., `openssl rand -hex 32`).
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing. MUST be changed in production.",
    )

    @field_validator("secret_key", mode="after")
    @classmethod
    def validate_secret_key_in_production(cls, v: str, info) -> str:
        """Prevent use of default secret key in production/staging environments.

        SECURITY: Using the default secret key in production would allow attackers
        to forge JWT tokens, bypassing all authentication. This validator ensures
        a secure, unique secret key is configured for non-development environments.
        """
        default_key = "dev-secret-key-change-in-production"
        environment = info.data.get("environment")

        if v == default_key and environment in (
            Environment.PRODUCTION,
            Environment.STAGING,
        ):
            raise ValueError(
                f"SECURITY ERROR: Default secret key cannot be used in {environment.value}. "
                "Set FOL_SECRET_KEY to a secure random value (e.g., `openssl rand -hex 32`)."
            )
        return v

    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)

    # External Services (Phase 1 prep)
    polygon_api_key: str | None = Field(
        default=None, description="Polygon.io API key for market data"
    )
    yahoo_finance_enabled: bool = Field(
        default=True, description="Enable Yahoo Finance as fallback"
    )

    # Feature Flags
    enable_audit_log: bool = True
    enable_transaction_classification: bool = True
    enable_wash_sale_detection: bool = True

    @field_validator("debug", mode="before")
    @classmethod
    def set_debug_from_environment(cls, v: bool, info) -> bool:
        """Auto-enable debug in development environment."""
        if info.data.get("environment") == Environment.DEVELOPMENT:
            return True
        return v

    @field_validator("log_format", mode="before")
    @classmethod
    def set_log_format_from_environment(cls, v: str, info) -> str:
        """Default to JSON logging in production."""
        if v is None:
            env = info.data.get("environment")
            if env == Environment.PRODUCTION:
                return "json"
        return v or "console"

    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL based on configuration.

        Returns Postgres URL if set, otherwise constructs SQLite URL.
        """
        if self.database_type == DatabaseType.POSTGRES and self.database_url:
            return self.database_url
        return f"sqlite:///{self.sqlite_path}"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    Call get_settings.cache_clear() to reload settings.

    Returns:
        Configured Settings instance.
    """
    return Settings()
