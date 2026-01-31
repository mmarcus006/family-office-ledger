"""Structured logging configuration using structlog.

Provides consistent logging across the application with:
- Development: Colored console output with pretty printing
- Production: JSON-formatted structured logs
- Request context binding (correlation IDs, user IDs)
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import Processor

from family_office_ledger.config import Settings, get_settings


def _add_log_level(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add log level to event dict for JSON output."""
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def _add_app_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application context to all log events."""
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["environment"] = settings.environment.value
    return event_dict


def get_console_processors() -> list[Processor]:
    """Get processors for console (development) output."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        ),
    ]


def get_json_processors() -> list[Processor]:
    """Get processors for JSON (production) output."""
    return [
        structlog.contextvars.merge_contextvars,
        _add_log_level,
        _add_app_context,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structured logging based on settings.

    Args:
        settings: Application settings. If None, loads from environment.

    Call this once at application startup before any logging occurs.
    """
    if settings is None:
        settings = get_settings()

    # Convert our LogLevel enum to Python logging level
    log_level = getattr(logging, settings.log_level.value)

    # Choose processors based on format setting
    if settings.log_format == "json":
        processors = get_json_processors()
    else:
        processors = get_console_processors()

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set up file handler if configured
    if settings.log_file:
        _setup_file_handler(settings.log_file, log_level)

    # Quiet noisy third-party loggers
    _configure_third_party_loggers(log_level)


def _setup_file_handler(log_file: Path, level: int) -> None:
    """Set up a file handler for logging."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(file_handler)


def _configure_third_party_loggers(level: int) -> None:
    """Configure log levels for third-party libraries."""
    # These can be noisy at DEBUG level
    noisy_loggers = [
        "httpcore",
        "httpx",
        "uvicorn.access",
        "sqlalchemy.engine",
        "urllib3",
        "asyncio",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(max(level, logging.INFO))

    # SQLAlchemy echoing should be controlled separately
    if level > logging.DEBUG:
        logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the calling module's name.

    Returns:
        Configured structlog BoundLogger.

    Example:
        logger = get_logger(__name__)
        logger.info("transaction_created", transaction_id=str(txn.id), amount=100.50)
    """
    return structlog.stdlib.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables for all subsequent log calls in this context.

    Useful for adding request-scoped context like correlation IDs.

    Args:
        **kwargs: Key-value pairs to bind to the logging context.

    Example:
        bind_context(request_id="abc123", user_id="user456")
        logger.info("processing_request")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """Remove context variables from the logging context.

    Args:
        *keys: Keys to remove from the context.
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all context variables from the logging context."""
    structlog.contextvars.clear_contextvars()


class LogContext:
    """Context manager for temporary log context binding.

    Example:
        with LogContext(transaction_id=str(txn.id)):
            logger.info("starting_transaction")
            process_transaction(txn)
            logger.info("transaction_complete")
        # Context automatically cleared after the with block
    """

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self._token: Any = None

    def __enter__(self) -> "LogContext":
        bind_context(**self.kwargs)
        return self

    def __exit__(self, *args: Any) -> None:
        unbind_context(*self.kwargs.keys())
