"""Anomaly detection service for identifying unusual transactions.

Detects:
- Transactions > N standard deviations from mean
- New payees with large amounts
- Unusual timing patterns
- Duplicate transactions
- Negative cash balances
- Round number transactions (potential fraud indicator)
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money
from family_office_ledger.logging_config import get_logger

logger = get_logger(__name__)


class AnomalyType(str, Enum):
    """Types of detected anomalies."""

    LARGE_TRANSACTION = "large_transaction"
    UNUSUAL_AMOUNT = "unusual_amount"  # Statistical outlier
    NEW_PAYEE_LARGE = "new_payee_large"
    DUPLICATE_SUSPECTED = "duplicate_suspected"
    NEGATIVE_BALANCE = "negative_balance"
    UNUSUAL_TIMING = "unusual_timing"
    ROUND_NUMBER = "round_number"
    RAPID_SUCCESSION = "rapid_succession"
    UNUSUAL_CATEGORY = "unusual_category"
    STRUCTURING_SUSPECTED = "structuring_suspected"  # Multiple txns just under threshold
    WEEKEND_TRANSACTION = "weekend_transaction"
    AFTER_HOURS = "after_hours"
    VELOCITY_SPIKE = "velocity_spike"  # Unusual number of transactions


class AnomalySeverity(str, Enum):
    """Severity level of anomaly."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyStatus(str, Enum):
    """Status of anomaly review."""

    OPEN = "open"
    REVIEWING = "reviewing"
    CONFIRMED = "confirmed"  # Confirmed as anomaly
    DISMISSED = "dismissed"  # False positive
    RESOLVED = "resolved"


@dataclass
class Anomaly:
    """A detected anomaly."""

    anomaly_type: AnomalyType
    severity: AnomalySeverity
    description: str
    id: UUID = field(default_factory=uuid4)

    # Related data
    transaction_id: UUID | None = None
    account_id: UUID | None = None
    entity_id: UUID | None = None

    # Detection details
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    detection_score: Decimal | None = None  # Confidence/severity score
    threshold_value: Decimal | None = None
    actual_value: Decimal | None = None

    # Context
    context: dict[str, Any] = field(default_factory=dict)
    related_transaction_ids: list[UUID] = field(default_factory=list)

    # Review
    status: AnomalyStatus = AnomalyStatus.OPEN
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None

    def mark_reviewed(
        self,
        reviewer_id: UUID,
        status: AnomalyStatus,
        notes: str | None = None,
    ) -> None:
        """Mark the anomaly as reviewed."""
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.now(UTC)
        self.status = status
        self.review_notes = notes


@dataclass
class TransactionStats:
    """Statistical summary of transactions for anomaly detection."""

    account_id: UUID | None = None
    entity_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None

    # Amount statistics
    count: int = 0
    total_amount: Decimal = Decimal("0")
    mean_amount: Decimal = Decimal("0")
    std_dev: Decimal = Decimal("0")
    min_amount: Decimal = Decimal("0")
    max_amount: Decimal = Decimal("0")
    median_amount: Decimal = Decimal("0")

    # Timing statistics
    avg_transactions_per_day: Decimal = Decimal("0")
    avg_transactions_per_week: Decimal = Decimal("0")

    # Payee statistics
    unique_payees: int = 0
    top_payees: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class AnomalyDetectionConfig:
    """Configuration for anomaly detection thresholds."""

    # Statistical thresholds
    std_dev_threshold: Decimal = Decimal("3.0")  # Flag > 3 std devs
    large_transaction_threshold: Money = field(
        default_factory=lambda: Money(Decimal("50000"))
    )

    # New payee thresholds
    new_payee_large_threshold: Money = field(
        default_factory=lambda: Money(Decimal("10000"))
    )
    new_payee_lookback_days: int = 365

    # Duplicate detection
    duplicate_time_window_hours: int = 24
    duplicate_amount_tolerance: Decimal = Decimal("0.01")  # 1%

    # Velocity thresholds
    max_transactions_per_day: int = 20
    velocity_spike_multiplier: Decimal = Decimal("3.0")

    # Structuring detection (just under reporting thresholds)
    structuring_threshold: Money = field(
        default_factory=lambda: Money(Decimal("10000"))  # CTR threshold
    )
    structuring_tolerance: Decimal = Decimal("0.15")  # 15% below threshold
    structuring_time_window_days: int = 3

    # Round number detection
    round_number_threshold: Money = field(
        default_factory=lambda: Money(Decimal("5000"))
    )

    # Timing
    flag_weekend_transactions: bool = False
    flag_after_hours: bool = False
    business_hours_start: int = 8
    business_hours_end: int = 18


class AnomalyDetectionService:
    """Service for detecting anomalous transactions and patterns."""

    def __init__(
        self,
        config: AnomalyDetectionConfig | None = None,
        repository: Any = None,
    ) -> None:
        self.config = config or AnomalyDetectionConfig()
        self.repository = repository

    def analyze_transaction(
        self,
        transaction: Any,  # Would be Transaction type
        historical_stats: TransactionStats | None = None,
    ) -> list[Anomaly]:
        """Analyze a single transaction for anomalies.

        Args:
            transaction: Transaction to analyze
            historical_stats: Pre-computed statistics for comparison

        Returns:
            List of detected anomalies
        """
        anomalies: list[Anomaly] = []

        amount = abs(Decimal(str(transaction.amount)))
        transaction_id = transaction.id
        account_id = getattr(transaction, "account_id", None)
        entity_id = getattr(transaction, "entity_id", None)

        # Check for large transaction
        if amount >= self.config.large_transaction_threshold.amount:
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.LARGE_TRANSACTION,
                    severity=self._calculate_severity_by_amount(amount),
                    description=f"Large transaction: ${amount:,.2f}",
                    transaction_id=transaction_id,
                    account_id=account_id,
                    entity_id=entity_id,
                    threshold_value=self.config.large_transaction_threshold.amount,
                    actual_value=amount,
                )
            )

        # Check statistical outlier
        if historical_stats and historical_stats.std_dev > 0:
            z_score = (amount - historical_stats.mean_amount) / historical_stats.std_dev
            if abs(z_score) > self.config.std_dev_threshold:
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.UNUSUAL_AMOUNT,
                        severity=self._calculate_severity_by_zscore(z_score),
                        description=f"Statistical outlier: {z_score:.2f} std devs from mean",
                        transaction_id=transaction_id,
                        account_id=account_id,
                        entity_id=entity_id,
                        detection_score=abs(z_score),
                        threshold_value=self.config.std_dev_threshold,
                        actual_value=z_score,
                        context={
                            "mean": str(historical_stats.mean_amount),
                            "std_dev": str(historical_stats.std_dev),
                            "z_score": str(z_score),
                        },
                    )
                )

        # Check for round number (potential fraud indicator)
        if self._is_suspicious_round_number(amount):
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.ROUND_NUMBER,
                    severity=AnomalySeverity.LOW,
                    description=f"Suspicious round number: ${amount:,.2f}",
                    transaction_id=transaction_id,
                    account_id=account_id,
                    entity_id=entity_id,
                    actual_value=amount,
                )
            )

        # Check for structuring (just under reporting threshold)
        if self._check_structuring(amount):
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.STRUCTURING_SUSPECTED,
                    severity=AnomalySeverity.HIGH,
                    description=f"Possible structuring: ${amount:,.2f} just under $10,000",
                    transaction_id=transaction_id,
                    account_id=account_id,
                    entity_id=entity_id,
                    threshold_value=self.config.structuring_threshold.amount,
                    actual_value=amount,
                )
            )

        # Check timing anomalies
        if hasattr(transaction, "date"):
            timing_anomalies = self._check_timing_anomalies(
                transaction.date, transaction_id, account_id, entity_id
            )
            anomalies.extend(timing_anomalies)

        logger.debug(
            "transaction_analyzed",
            transaction_id=str(transaction_id),
            anomalies_found=len(anomalies),
        )

        return anomalies

    def detect_duplicates(
        self,
        transactions: list[Any],
    ) -> list[Anomaly]:
        """Detect potential duplicate transactions.

        Args:
            transactions: List of transactions to check

        Returns:
            List of duplicate anomalies
        """
        anomalies: list[Anomaly] = []
        seen: dict[str, list[Any]] = {}  # Key -> list of matching transactions

        for txn in transactions:
            # Create a key based on amount, payee, and approximate time
            amount = abs(Decimal(str(txn.amount)))
            payee = getattr(txn, "payee", "") or getattr(txn, "description", "")
            txn_date = getattr(txn, "date", date.today())

            # Round amount for fuzzy matching
            rounded_amount = round(amount, 2)
            key = f"{payee}|{rounded_amount}"

            if key in seen:
                for prev_txn in seen[key]:
                    prev_date = getattr(prev_txn, "date", date.today())
                    days_apart = abs((txn_date - prev_date).days)

                    if days_apart * 24 <= self.config.duplicate_time_window_hours:
                        anomalies.append(
                            Anomaly(
                                anomaly_type=AnomalyType.DUPLICATE_SUSPECTED,
                                severity=AnomalySeverity.MEDIUM,
                                description=f"Potential duplicate: ${amount:,.2f} to {payee}",
                                transaction_id=txn.id,
                                related_transaction_ids=[prev_txn.id],
                                context={
                                    "original_date": str(prev_date),
                                    "duplicate_date": str(txn_date),
                                    "days_apart": days_apart,
                                },
                            )
                        )

            if key not in seen:
                seen[key] = []
            seen[key].append(txn)

        logger.info(
            "duplicate_detection_complete",
            transactions_checked=len(transactions),
            duplicates_found=len(anomalies),
        )

        return anomalies

    def detect_new_payee_anomalies(
        self,
        transaction: Any,
        known_payees: set[str],
    ) -> Anomaly | None:
        """Detect large transactions to new payees.

        Args:
            transaction: Transaction to check
            known_payees: Set of previously seen payee names

        Returns:
            Anomaly if detected, None otherwise
        """
        payee = getattr(transaction, "payee", "") or getattr(transaction, "description", "")
        if not payee:
            return None

        payee_normalized = payee.lower().strip()
        amount = abs(Decimal(str(transaction.amount)))

        if payee_normalized not in known_payees:
            if amount >= self.config.new_payee_large_threshold.amount:
                return Anomaly(
                    anomaly_type=AnomalyType.NEW_PAYEE_LARGE,
                    severity=self._calculate_severity_by_amount(amount),
                    description=f"Large transaction to new payee: ${amount:,.2f} to {payee}",
                    transaction_id=transaction.id,
                    actual_value=amount,
                    threshold_value=self.config.new_payee_large_threshold.amount,
                    context={"payee": payee},
                )

        return None

    def detect_velocity_anomalies(
        self,
        account_id: UUID,
        transactions: list[Any],
        lookback_days: int = 30,
    ) -> list[Anomaly]:
        """Detect unusual transaction velocity.

        Args:
            account_id: Account to analyze
            transactions: Recent transactions
            lookback_days: Days to analyze

        Returns:
            List of velocity anomalies
        """
        anomalies: list[Anomaly] = []

        # Group by date
        by_date: dict[date, list[Any]] = {}
        for txn in transactions:
            txn_date = getattr(txn, "date", date.today())
            if txn_date not in by_date:
                by_date[txn_date] = []
            by_date[txn_date].append(txn)

        if not by_date:
            return anomalies

        # Calculate average transactions per day
        counts = [len(txns) for txns in by_date.values()]
        avg_count = sum(counts) / len(counts) if counts else 0

        # Check each day for spikes
        for txn_date, txns in by_date.items():
            count = len(txns)
            if count > self.config.max_transactions_per_day:
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.VELOCITY_SPIKE,
                        severity=AnomalySeverity.MEDIUM,
                        description=f"High transaction volume: {count} transactions on {txn_date}",
                        account_id=account_id,
                        actual_value=Decimal(count),
                        threshold_value=Decimal(self.config.max_transactions_per_day),
                        context={
                            "date": str(txn_date),
                            "count": count,
                            "average": avg_count,
                        },
                    )
                )

            # Check for spike vs average
            if avg_count > 0:
                multiplier = count / avg_count
                if multiplier >= float(self.config.velocity_spike_multiplier):
                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.VELOCITY_SPIKE,
                            severity=AnomalySeverity.MEDIUM,
                            description=f"Velocity spike: {multiplier:.1f}x normal on {txn_date}",
                            account_id=account_id,
                            detection_score=Decimal(str(multiplier)),
                            context={
                                "date": str(txn_date),
                                "count": count,
                                "average": avg_count,
                                "multiplier": multiplier,
                            },
                        )
                    )

        return anomalies

    def check_negative_balance(
        self,
        account_id: UUID,
        balance: Decimal,
        account_name: str | None = None,
    ) -> Anomaly | None:
        """Check for negative balance in non-liability accounts.

        Args:
            account_id: Account ID
            balance: Current balance
            account_name: Account name for description

        Returns:
            Anomaly if negative balance detected
        """
        if balance < 0:
            name = account_name or str(account_id)
            return Anomaly(
                anomaly_type=AnomalyType.NEGATIVE_BALANCE,
                severity=AnomalySeverity.HIGH,
                description=f"Negative balance in {name}: ${balance:,.2f}",
                account_id=account_id,
                actual_value=balance,
                threshold_value=Decimal("0"),
            )
        return None

    def calculate_transaction_stats(
        self,
        transactions: list[Any],
        account_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> TransactionStats:
        """Calculate statistical summary of transactions.

        Args:
            transactions: Transactions to analyze
            account_id: Optional account filter
            entity_id: Optional entity filter

        Returns:
            TransactionStats summary
        """
        stats = TransactionStats(account_id=account_id, entity_id=entity_id)

        if not transactions:
            return stats

        amounts = [abs(Decimal(str(t.amount))) for t in transactions]
        stats.count = len(amounts)
        stats.total_amount = sum(amounts)
        stats.mean_amount = stats.total_amount / stats.count
        stats.min_amount = min(amounts)
        stats.max_amount = max(amounts)

        # Calculate standard deviation
        if stats.count > 1:
            variance = sum((a - stats.mean_amount) ** 2 for a in amounts) / stats.count
            stats.std_dev = variance ** Decimal("0.5")

        # Calculate median
        sorted_amounts = sorted(amounts)
        mid = len(sorted_amounts) // 2
        if len(sorted_amounts) % 2 == 0:
            stats.median_amount = (sorted_amounts[mid - 1] + sorted_amounts[mid]) / 2
        else:
            stats.median_amount = sorted_amounts[mid]

        # Date range
        dates = [getattr(t, "date", date.today()) for t in transactions]
        if dates:
            stats.period_start = min(dates)
            stats.period_end = max(dates)
            days = (stats.period_end - stats.period_start).days + 1
            if days > 0:
                stats.avg_transactions_per_day = Decimal(stats.count) / Decimal(days)
                stats.avg_transactions_per_week = stats.avg_transactions_per_day * 7

        return stats

    def _calculate_severity_by_amount(self, amount: Decimal) -> AnomalySeverity:
        """Calculate severity based on transaction amount."""
        if amount >= Decimal("100000"):
            return AnomalySeverity.CRITICAL
        elif amount >= Decimal("50000"):
            return AnomalySeverity.HIGH
        elif amount >= Decimal("25000"):
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    def _calculate_severity_by_zscore(self, z_score: Decimal) -> AnomalySeverity:
        """Calculate severity based on z-score."""
        abs_z = abs(z_score)
        if abs_z >= Decimal("5"):
            return AnomalySeverity.CRITICAL
        elif abs_z >= Decimal("4"):
            return AnomalySeverity.HIGH
        elif abs_z >= Decimal("3.5"):
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    def _is_suspicious_round_number(self, amount: Decimal) -> bool:
        """Check if amount is a suspicious round number."""
        if amount < self.config.round_number_threshold.amount:
            return False

        # Check if it's a round thousand
        remainder = amount % 1000
        return remainder == 0

    def _check_structuring(self, amount: Decimal) -> bool:
        """Check if transaction might be structuring."""
        threshold = self.config.structuring_threshold.amount
        tolerance = self.config.structuring_tolerance
        lower_bound = threshold * (1 - tolerance)

        return lower_bound <= amount < threshold

    def _check_timing_anomalies(
        self,
        txn_date: date,
        transaction_id: UUID | None,
        account_id: UUID | None,
        entity_id: UUID | None,
    ) -> list[Anomaly]:
        """Check for timing-based anomalies."""
        anomalies: list[Anomaly] = []

        # Weekend check
        if self.config.flag_weekend_transactions and txn_date.weekday() >= 5:
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.WEEKEND_TRANSACTION,
                    severity=AnomalySeverity.LOW,
                    description=f"Transaction on weekend: {txn_date}",
                    transaction_id=transaction_id,
                    account_id=account_id,
                    entity_id=entity_id,
                    context={"day_of_week": txn_date.strftime("%A")},
                )
            )

        return anomalies
