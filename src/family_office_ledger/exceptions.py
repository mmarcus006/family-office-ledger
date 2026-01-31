"""Domain exception hierarchy for Family Office Ledger.

All domain-specific exceptions inherit from FamilyOfficeLedgerError.
This allows catching all application errors with a single base class
while preserving specificity for individual error types.
"""

from typing import Any
from uuid import UUID


class FamilyOfficeLedgerError(Exception):
    """Base exception for all Family Office Ledger errors.

    All domain exceptions should inherit from this class.
    Includes optional error_code for API responses and extra context.
    """

    error_code: str = "FOL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "context": self.context,
        }


# =============================================================================
# Entity Errors
# =============================================================================


class EntityError(FamilyOfficeLedgerError):
    """Base exception for entity-related errors."""

    error_code = "ENTITY_ERROR"
    status_code = 400


class EntityNotFoundError(EntityError):
    """Raised when an entity cannot be found."""

    error_code = "ENTITY_NOT_FOUND"
    status_code = 404

    def __init__(self, entity_id: UUID | str) -> None:
        super().__init__(
            f"Entity not found: {entity_id}",
            context={"entity_id": str(entity_id)},
        )


class DuplicateEntityError(EntityError):
    """Raised when attempting to create a duplicate entity."""

    error_code = "DUPLICATE_ENTITY"
    status_code = 409

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Entity already exists: {name}",
            context={"entity_name": name},
        )


# =============================================================================
# Account Errors
# =============================================================================


class AccountError(FamilyOfficeLedgerError):
    """Base exception for account-related errors."""

    error_code = "ACCOUNT_ERROR"
    status_code = 400


class AccountNotFoundError(AccountError):
    """Raised when an account cannot be found."""

    error_code = "ACCOUNT_NOT_FOUND"
    status_code = 404

    def __init__(self, account_id: UUID | str) -> None:
        super().__init__(
            f"Account not found: {account_id}",
            context={"account_id": str(account_id)},
        )


class AccountBalanceError(AccountError):
    """Raised when an account balance operation fails."""

    error_code = "ACCOUNT_BALANCE_ERROR"

    def __init__(self, account_id: UUID | str, message: str) -> None:
        super().__init__(
            message, context={"account_id": str(account_id)}
        )


class InsufficientBalanceError(AccountBalanceError):
    """Raised when account has insufficient balance for an operation."""

    error_code = "INSUFFICIENT_BALANCE"

    def __init__(
        self, account_id: UUID | str, required: str, available: str
    ) -> None:
        super().__init__(
            account_id,
            f"Insufficient balance: required {required}, available {available}",
        )
        self.context.update({"required": required, "available": available})


# =============================================================================
# Transaction Errors
# =============================================================================


class TransactionError(FamilyOfficeLedgerError):
    """Base exception for transaction-related errors."""

    error_code = "TRANSACTION_ERROR"
    status_code = 400


class TransactionNotFoundError(TransactionError):
    """Raised when a transaction cannot be found."""

    error_code = "TRANSACTION_NOT_FOUND"
    status_code = 404

    def __init__(self, transaction_id: UUID | str) -> None:
        super().__init__(
            f"Transaction not found: {transaction_id}",
            context={"transaction_id": str(transaction_id)},
        )


class UnbalancedTransactionError(TransactionError):
    """Raised when a transaction's debits don't equal credits."""

    error_code = "UNBALANCED_TRANSACTION"

    def __init__(self, debit_total: str, credit_total: str) -> None:
        super().__init__(
            f"Transaction is unbalanced: debits={debit_total}, credits={credit_total}",
            context={"debit_total": debit_total, "credit_total": credit_total},
        )


class InvalidTransactionDateError(TransactionError):
    """Raised when a transaction date is invalid."""

    error_code = "INVALID_TRANSACTION_DATE"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TransactionLockedError(TransactionError):
    """Raised when attempting to modify a locked transaction."""

    error_code = "TRANSACTION_LOCKED"
    status_code = 403

    def __init__(self, transaction_id: UUID | str, reason: str) -> None:
        super().__init__(
            f"Transaction is locked: {reason}",
            context={"transaction_id": str(transaction_id), "reason": reason},
        )


# =============================================================================
# Tax Lot Errors
# =============================================================================


class TaxLotError(FamilyOfficeLedgerError):
    """Base exception for tax lot-related errors."""

    error_code = "TAX_LOT_ERROR"
    status_code = 400


class TaxLotNotFoundError(TaxLotError):
    """Raised when a tax lot cannot be found."""

    error_code = "TAX_LOT_NOT_FOUND"
    status_code = 404

    def __init__(self, lot_id: UUID | str) -> None:
        super().__init__(
            f"Tax lot not found: {lot_id}",
            context={"lot_id": str(lot_id)},
        )


class InsufficientSharesError(TaxLotError):
    """Raised when a tax lot has insufficient shares for a sale."""

    error_code = "INSUFFICIENT_SHARES"

    def __init__(
        self, lot_id: UUID | str, required: str, available: str
    ) -> None:
        super().__init__(
            f"Insufficient shares in lot: required {required}, available {available}",
            context={
                "lot_id": str(lot_id),
                "required": required,
                "available": available,
            },
        )


class WashSaleViolationError(TaxLotError):
    """Raised when a wash sale rule is violated."""

    error_code = "WASH_SALE_VIOLATION"

    def __init__(self, security_symbol: str, sale_date: str, buy_date: str) -> None:
        super().__init__(
            f"Wash sale detected for {security_symbol}: sale on {sale_date}, "
            f"repurchase on {buy_date} within 30-day window",
            context={
                "security": security_symbol,
                "sale_date": sale_date,
                "buy_date": buy_date,
            },
        )


# =============================================================================
# QSBS Errors
# =============================================================================


class QSBSError(FamilyOfficeLedgerError):
    """Base exception for QSBS-related errors."""

    error_code = "QSBS_ERROR"
    status_code = 400


class QSBSNotEligibleError(QSBSError):
    """Raised when a security is not eligible for QSBS treatment."""

    error_code = "QSBS_NOT_ELIGIBLE"

    def __init__(self, security_symbol: str, reason: str) -> None:
        super().__init__(
            f"{security_symbol} is not eligible for QSBS treatment: {reason}",
            context={"security": security_symbol, "reason": reason},
        )


class QSBSHoldingPeriodError(QSBSError):
    """Raised when QSBS 5-year holding period is not met."""

    error_code = "QSBS_HOLDING_PERIOD"

    def __init__(
        self, security_symbol: str, days_held: int, required_days: int = 1825
    ) -> None:
        super().__init__(
            f"{security_symbol} has not met the 5-year holding period: "
            f"{days_held} days held, {required_days} required",
            context={
                "security": security_symbol,
                "days_held": days_held,
                "required_days": required_days,
            },
        )


class QSBSExclusionCapError(QSBSError):
    """Raised when $10M per-issuer cap is exceeded."""

    error_code = "QSBS_EXCLUSION_CAP"

    def __init__(
        self, security_symbol: str, excluded_amount: str, cap_amount: str = "$10,000,000"
    ) -> None:
        super().__init__(
            f"QSBS exclusion cap exceeded for {security_symbol}: "
            f"{excluded_amount} already excluded (cap: {cap_amount})",
            context={
                "security": security_symbol,
                "excluded_amount": excluded_amount,
                "cap_amount": cap_amount,
            },
        )


class Section1045RolloverError(QSBSError):
    """Raised when a Section 1045 rollover fails."""

    error_code = "SECTION_1045_ERROR"

    def __init__(self, message: str, days_elapsed: int | None = None) -> None:
        context = {}
        if days_elapsed is not None:
            context["days_elapsed"] = days_elapsed
            context["max_days"] = 60
        super().__init__(message, context=context)


# =============================================================================
# Reconciliation Errors
# =============================================================================


class ReconciliationError(FamilyOfficeLedgerError):
    """Base exception for reconciliation-related errors."""

    error_code = "RECONCILIATION_ERROR"
    status_code = 400


class ReconciliationMismatchError(ReconciliationError):
    """Raised when reconciliation totals don't match."""

    error_code = "RECONCILIATION_MISMATCH"

    def __init__(
        self, account_name: str, ledger_balance: str, statement_balance: str
    ) -> None:
        difference = f"difference: {ledger_balance} vs {statement_balance}"
        super().__init__(
            f"Reconciliation failed for {account_name}: {difference}",
            context={
                "account": account_name,
                "ledger_balance": ledger_balance,
                "statement_balance": statement_balance,
            },
        )


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(FamilyOfficeLedgerError):
    """Base exception for database-related errors."""

    error_code = "DATABASE_ERROR"
    status_code = 500


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    error_code = "DATABASE_CONNECTION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(f"Database connection failed: {message}")


class IntegrityError(DatabaseError):
    """Raised when a database integrity constraint is violated."""

    error_code = "DATABASE_INTEGRITY_ERROR"
    status_code = 409


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(FamilyOfficeLedgerError):
    """Base exception for validation errors."""

    error_code = "VALIDATION_ERROR"
    status_code = 422


class InvalidCurrencyError(ValidationError):
    """Raised when an invalid currency code is provided."""

    error_code = "INVALID_CURRENCY"

    def __init__(self, currency_code: str) -> None:
        super().__init__(
            f"Invalid currency code: {currency_code}",
            context={"currency_code": currency_code},
        )


class InvalidAmountError(ValidationError):
    """Raised when an invalid monetary amount is provided."""

    error_code = "INVALID_AMOUNT"

    def __init__(self, amount: str, reason: str) -> None:
        super().__init__(
            f"Invalid amount '{amount}': {reason}",
            context={"amount": amount, "reason": reason},
        )


# =============================================================================
# Authorization Errors (Phase 3 prep)
# =============================================================================


class AuthorizationError(FamilyOfficeLedgerError):
    """Base exception for authorization errors."""

    error_code = "AUTHORIZATION_ERROR"
    status_code = 403


class PermissionDeniedError(AuthorizationError):
    """Raised when user lacks permission for an action."""

    error_code = "PERMISSION_DENIED"

    def __init__(self, action: str, resource: str) -> None:
        super().__init__(
            f"Permission denied: cannot {action} on {resource}",
            context={"action": action, "resource": resource},
        )


class AuthenticationError(FamilyOfficeLedgerError):
    """Raised when authentication fails."""

    error_code = "AUTHENTICATION_ERROR"
    status_code = 401

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)
