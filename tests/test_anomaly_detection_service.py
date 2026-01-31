"""Tests for AnomalyDetectionService.

Tests anomaly detection for:
- Large transactions
- Statistical outliers (z-score)
- Suspicious round numbers
- Structuring detection (just under $10k)
- Duplicate transactions
- New payee anomalies
- Velocity spikes
- Negative balance detection
- Transaction statistics calculation
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from family_office_ledger.domain.value_objects import Money
from family_office_ledger.services.anomaly_detection import (
    Anomaly,
    AnomalyDetectionConfig,
    AnomalyDetectionService,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    TransactionStats,
)


@dataclass
class MockTransaction:
    """Simple transaction mock with required fields for anomaly detection."""

    id: UUID = field(default_factory=uuid4)
    amount: Decimal = Decimal("100.00")
    date: date = field(default_factory=date.today)
    payee: str = "Test Payee"
    account_id: UUID | None = None
    entity_id: UUID | None = None
    description: str = ""


@pytest.fixture
def service() -> AnomalyDetectionService:
    """Default anomaly detection service with standard config."""
    return AnomalyDetectionService()


@pytest.fixture
def custom_config() -> AnomalyDetectionConfig:
    """Custom config for testing specific thresholds."""
    return AnomalyDetectionConfig(
        large_transaction_threshold=Money(Decimal("10000")),
        new_payee_large_threshold=Money(Decimal("5000")),
        max_transactions_per_day=5,
        structuring_threshold=Money(Decimal("10000")),
        structuring_tolerance=Decimal("0.15"),
        round_number_threshold=Money(Decimal("1000")),
    )


@pytest.fixture
def service_with_custom_config(
    custom_config: AnomalyDetectionConfig,
) -> AnomalyDetectionService:
    """Service with custom thresholds for testing."""
    return AnomalyDetectionService(config=custom_config)


# =============================================================================
# TestAnalyzeTransactionLargeAmount
# =============================================================================


class TestAnalyzeTransactionLargeAmount:
    """Tests for large transaction detection."""

    def test_detects_large_transaction_above_threshold(
        self, service: AnomalyDetectionService
    ):
        """Transaction above $50,000 threshold should be flagged."""
        txn = MockTransaction(amount=Decimal("75000.00"))

        anomalies = service.analyze_transaction(txn)

        assert len(anomalies) >= 1
        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is not None
        assert large_txn_anomaly.actual_value == Decimal("75000.00")
        assert large_txn_anomaly.threshold_value == Decimal("50000")

    def test_does_not_flag_transaction_below_threshold(
        self, service: AnomalyDetectionService
    ):
        """Transaction below threshold should not be flagged as large."""
        txn = MockTransaction(amount=Decimal("25000.00"))

        anomalies = service.analyze_transaction(txn)

        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is None

    def test_transaction_exactly_at_threshold_is_flagged(
        self, service: AnomalyDetectionService
    ):
        """Transaction exactly at threshold should be flagged."""
        txn = MockTransaction(amount=Decimal("50000.00"))

        anomalies = service.analyze_transaction(txn)

        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is not None

    def test_negative_amount_uses_absolute_value(
        self, service: AnomalyDetectionService
    ):
        """Negative amounts should use absolute value for comparison."""
        txn = MockTransaction(amount=Decimal("-75000.00"))

        anomalies = service.analyze_transaction(txn)

        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is not None
        assert large_txn_anomaly.actual_value == Decimal("75000.00")

    def test_severity_critical_for_very_large_amount(
        self, service: AnomalyDetectionService
    ):
        """Very large transactions (>=100k) should have CRITICAL severity."""
        txn = MockTransaction(amount=Decimal("150000.00"))

        anomalies = service.analyze_transaction(txn)

        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is not None
        assert large_txn_anomaly.severity == AnomalySeverity.CRITICAL

    def test_severity_high_for_large_amount(self, service: AnomalyDetectionService):
        """Large transactions (>=50k, <100k) should have HIGH severity."""
        txn = MockTransaction(amount=Decimal("75000.00"))

        anomalies = service.analyze_transaction(txn)

        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is not None
        assert large_txn_anomaly.severity == AnomalySeverity.HIGH

    def test_custom_threshold(
        self, service_with_custom_config: AnomalyDetectionService
    ):
        """Custom threshold of $10,000 should be respected."""
        txn = MockTransaction(amount=Decimal("15000.00"))

        anomalies = service_with_custom_config.analyze_transaction(txn)

        large_txn_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.LARGE_TRANSACTION),
            None,
        )
        assert large_txn_anomaly is not None
        assert large_txn_anomaly.threshold_value == Decimal("10000")


# =============================================================================
# TestAnalyzeTransactionStatisticalOutlier
# =============================================================================


class TestAnalyzeTransactionStatisticalOutlier:
    """Tests for z-score based statistical outlier detection."""

    @pytest.fixture
    def historical_stats(self) -> TransactionStats:
        """Historical stats with mean=1000, std_dev=200."""
        return TransactionStats(
            count=100,
            mean_amount=Decimal("1000"),
            std_dev=Decimal("200"),
        )

    def test_detects_statistical_outlier_above_threshold(
        self, service: AnomalyDetectionService, historical_stats: TransactionStats
    ):
        """Transaction > 3 std devs from mean should be flagged."""
        # 1000 + (3.5 * 200) = 1700
        txn = MockTransaction(amount=Decimal("1800.00"))

        anomalies = service.analyze_transaction(txn, historical_stats)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is not None
        assert "Statistical outlier" in outlier_anomaly.description

    def test_does_not_flag_normal_transaction(
        self, service: AnomalyDetectionService, historical_stats: TransactionStats
    ):
        """Transaction within 3 std devs should not be flagged."""
        # 1000 + (2 * 200) = 1400
        txn = MockTransaction(amount=Decimal("1200.00"))

        anomalies = service.analyze_transaction(txn, historical_stats)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is None

    def test_z_score_in_context(
        self, service: AnomalyDetectionService, historical_stats: TransactionStats
    ):
        """Z-score should be recorded in anomaly context."""
        txn = MockTransaction(amount=Decimal("1800.00"))

        anomalies = service.analyze_transaction(txn, historical_stats)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is not None
        assert "z_score" in outlier_anomaly.context
        z_score = Decimal(outlier_anomaly.context["z_score"])
        assert z_score == Decimal("4")  # (1800 - 1000) / 200 = 4

    def test_no_detection_without_historical_stats(
        self, service: AnomalyDetectionService
    ):
        """Without historical stats, no statistical outlier detection occurs."""
        txn = MockTransaction(amount=Decimal("1000000.00"))

        anomalies = service.analyze_transaction(txn, historical_stats=None)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is None

    def test_no_detection_with_zero_std_dev(self, service: AnomalyDetectionService):
        """With zero std dev, no statistical outlier detection occurs."""
        stats = TransactionStats(
            count=10,
            mean_amount=Decimal("1000"),
            std_dev=Decimal("0"),
        )
        txn = MockTransaction(amount=Decimal("5000.00"))

        anomalies = service.analyze_transaction(txn, stats)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is None

    def test_severity_critical_for_extreme_outlier(
        self, service: AnomalyDetectionService
    ):
        """Z-score >= 5 should have CRITICAL severity."""
        stats = TransactionStats(
            count=100,
            mean_amount=Decimal("1000"),
            std_dev=Decimal("100"),
        )
        # z-score = (1600 - 1000) / 100 = 6
        txn = MockTransaction(amount=Decimal("1600.00"))

        anomalies = service.analyze_transaction(txn, stats)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is not None
        assert outlier_anomaly.severity == AnomalySeverity.CRITICAL

    def test_detects_negative_outlier(
        self, service: AnomalyDetectionService, historical_stats: TransactionStats
    ):
        """Transaction far below mean should also be flagged."""
        # 1000 - (4 * 200) = 200
        txn = MockTransaction(amount=Decimal("150.00"))

        anomalies = service.analyze_transaction(txn, historical_stats)

        outlier_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_AMOUNT),
            None,
        )
        assert outlier_anomaly is not None


# =============================================================================
# TestAnalyzeTransactionRoundNumber
# =============================================================================


class TestAnalyzeTransactionRoundNumber:
    """Tests for suspicious round number detection."""

    def test_detects_round_thousand_above_threshold(
        self, service: AnomalyDetectionService
    ):
        """Round thousands above $5,000 threshold should be flagged."""
        txn = MockTransaction(amount=Decimal("10000.00"))

        anomalies = service.analyze_transaction(txn)

        round_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.ROUND_NUMBER),
            None,
        )
        assert round_anomaly is not None
        assert "Suspicious round number" in round_anomaly.description

    def test_does_not_flag_round_number_below_threshold(
        self, service: AnomalyDetectionService
    ):
        """Round numbers below $5,000 threshold should not be flagged."""
        txn = MockTransaction(amount=Decimal("3000.00"))

        anomalies = service.analyze_transaction(txn)

        round_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.ROUND_NUMBER),
            None,
        )
        assert round_anomaly is None

    def test_does_not_flag_non_round_number(self, service: AnomalyDetectionService):
        """Non-round numbers should not be flagged."""
        txn = MockTransaction(amount=Decimal("10543.27"))

        anomalies = service.analyze_transaction(txn)

        round_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.ROUND_NUMBER),
            None,
        )
        assert round_anomaly is None

    def test_round_number_has_low_severity(self, service: AnomalyDetectionService):
        """Round number anomalies should have LOW severity."""
        txn = MockTransaction(amount=Decimal("25000.00"))

        anomalies = service.analyze_transaction(txn)

        round_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.ROUND_NUMBER),
            None,
        )
        assert round_anomaly is not None
        assert round_anomaly.severity == AnomalySeverity.LOW

    def test_custom_round_number_threshold(
        self, service_with_custom_config: AnomalyDetectionService
    ):
        """Custom threshold of $1,000 should be respected."""
        txn = MockTransaction(amount=Decimal("2000.00"))

        anomalies = service_with_custom_config.analyze_transaction(txn)

        round_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.ROUND_NUMBER),
            None,
        )
        assert round_anomaly is not None


# =============================================================================
# TestAnalyzeTransactionStructuring
# =============================================================================


class TestAnalyzeTransactionStructuring:
    """Tests for structuring detection (amounts just under $10k threshold)."""

    def test_detects_structuring_just_under_threshold(
        self, service: AnomalyDetectionService
    ):
        """Amount like $9,500 (just under $10k) should trigger structuring alert."""
        txn = MockTransaction(amount=Decimal("9500.00"))

        anomalies = service.analyze_transaction(txn)

        structuring_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.STRUCTURING_SUSPECTED
            ),
            None,
        )
        assert structuring_anomaly is not None
        assert "structuring" in structuring_anomaly.description.lower()

    def test_structuring_tolerance_window(self, service: AnomalyDetectionService):
        """Amounts within 15% below $10k threshold should be flagged."""
        # 10000 * 0.85 = 8500 (lower bound)
        txn = MockTransaction(amount=Decimal("8600.00"))

        anomalies = service.analyze_transaction(txn)

        structuring_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.STRUCTURING_SUSPECTED
            ),
            None,
        )
        assert structuring_anomaly is not None

    def test_does_not_flag_amount_below_tolerance(
        self, service: AnomalyDetectionService
    ):
        """Amounts below the tolerance window should not be flagged."""
        # 10000 * 0.85 = 8500 (lower bound)
        txn = MockTransaction(amount=Decimal("8000.00"))

        anomalies = service.analyze_transaction(txn)

        structuring_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.STRUCTURING_SUSPECTED
            ),
            None,
        )
        assert structuring_anomaly is None

    def test_does_not_flag_amount_at_or_above_threshold(
        self, service: AnomalyDetectionService
    ):
        """Amounts at or above $10k should not be flagged as structuring."""
        txn = MockTransaction(amount=Decimal("10000.00"))

        anomalies = service.analyze_transaction(txn)

        structuring_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.STRUCTURING_SUSPECTED
            ),
            None,
        )
        assert structuring_anomaly is None

    def test_structuring_has_high_severity(self, service: AnomalyDetectionService):
        """Structuring anomalies should have HIGH severity."""
        txn = MockTransaction(amount=Decimal("9500.00"))

        anomalies = service.analyze_transaction(txn)

        structuring_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.STRUCTURING_SUSPECTED
            ),
            None,
        )
        assert structuring_anomaly is not None
        assert structuring_anomaly.severity == AnomalySeverity.HIGH


# =============================================================================
# TestDetectDuplicates
# =============================================================================


class TestDetectDuplicates:
    """Tests for duplicate transaction detection."""

    def test_detects_duplicate_same_day(self, service: AnomalyDetectionService):
        """Two identical transactions on same day should be flagged."""
        today = date.today()
        txn1 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )
        txn2 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )

        anomalies = service.detect_duplicates([txn1, txn2])

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.DUPLICATE_SUSPECTED
        assert anomalies[0].transaction_id == txn2.id
        assert txn1.id in anomalies[0].related_transaction_ids

    def test_detects_duplicate_within_time_window(
        self, service: AnomalyDetectionService
    ):
        """Duplicates within 24-hour window should be flagged."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        txn1 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=yesterday,
        )
        txn2 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )

        anomalies = service.detect_duplicates([txn1, txn2])

        assert len(anomalies) == 1

    def test_does_not_flag_duplicates_outside_time_window(
        self, service: AnomalyDetectionService
    ):
        """Transactions more than 24 hours apart should not be flagged."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        txn1 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=week_ago,
        )
        txn2 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )

        anomalies = service.detect_duplicates([txn1, txn2])

        assert len(anomalies) == 0

    def test_does_not_flag_different_amounts(self, service: AnomalyDetectionService):
        """Different amounts should not be flagged as duplicates."""
        today = date.today()
        txn1 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )
        txn2 = MockTransaction(
            amount=Decimal("600.00"),
            payee="Vendor ABC",
            date=today,
        )

        anomalies = service.detect_duplicates([txn1, txn2])

        assert len(anomalies) == 0

    def test_does_not_flag_different_payees(self, service: AnomalyDetectionService):
        """Different payees should not be flagged as duplicates."""
        today = date.today()
        txn1 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )
        txn2 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor XYZ",
            date=today,
        )

        anomalies = service.detect_duplicates([txn1, txn2])

        assert len(anomalies) == 0

    def test_detects_multiple_duplicates(self, service: AnomalyDetectionService):
        """Multiple duplicates should all be flagged."""
        today = date.today()
        txns = [
            MockTransaction(amount=Decimal("500.00"), payee="Vendor ABC", date=today)
            for _ in range(3)
        ]

        anomalies = service.detect_duplicates(txns)

        # txn2 is flagged as dup of txn1
        # txn3 is flagged as dup of txn1 AND txn2 (compared against all previous)
        assert len(anomalies) == 3
        assert all(a.anomaly_type == AnomalyType.DUPLICATE_SUSPECTED for a in anomalies)

    def test_duplicate_has_medium_severity(self, service: AnomalyDetectionService):
        """Duplicate anomalies should have MEDIUM severity."""
        today = date.today()
        txn1 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )
        txn2 = MockTransaction(
            amount=Decimal("500.00"),
            payee="Vendor ABC",
            date=today,
        )

        anomalies = service.detect_duplicates([txn1, txn2])

        assert anomalies[0].severity == AnomalySeverity.MEDIUM

    def test_empty_transaction_list(self, service: AnomalyDetectionService):
        """Empty transaction list should return empty anomalies."""
        anomalies = service.detect_duplicates([])

        assert len(anomalies) == 0

    def test_single_transaction(self, service: AnomalyDetectionService):
        """Single transaction cannot have duplicates."""
        txn = MockTransaction(amount=Decimal("500.00"), payee="Vendor ABC")

        anomalies = service.detect_duplicates([txn])

        assert len(anomalies) == 0


# =============================================================================
# TestDetectNewPayeeAnomalies
# =============================================================================


class TestDetectNewPayeeAnomalies:
    """Tests for detecting large transactions to new payees."""

    def test_detects_large_transaction_to_new_payee(
        self, service: AnomalyDetectionService
    ):
        """Large transaction to unknown payee should be flagged."""
        txn = MockTransaction(
            amount=Decimal("15000.00"),
            payee="Unknown Vendor",
        )
        known_payees = {"vendor a", "vendor b", "vendor c"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.NEW_PAYEE_LARGE
        assert anomaly.actual_value == Decimal("15000.00")

    def test_does_not_flag_known_payee(self, service: AnomalyDetectionService):
        """Large transaction to known payee should not be flagged."""
        txn = MockTransaction(
            amount=Decimal("50000.00"),
            payee="Vendor A",
        )
        known_payees = {"vendor a", "vendor b", "vendor c"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        assert anomaly is None

    def test_does_not_flag_small_transaction_to_new_payee(
        self, service: AnomalyDetectionService
    ):
        """Small transaction to new payee should not be flagged."""
        txn = MockTransaction(
            amount=Decimal("500.00"),
            payee="Unknown Vendor",
        )
        known_payees = {"vendor a", "vendor b", "vendor c"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        assert anomaly is None

    def test_payee_matching_is_case_insensitive(self, service: AnomalyDetectionService):
        """Payee matching should be case insensitive."""
        txn = MockTransaction(
            amount=Decimal("50000.00"),
            payee="VENDOR A",
        )
        known_payees = {"vendor a", "vendor b"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        assert anomaly is None

    def test_payee_matching_strips_whitespace(self, service: AnomalyDetectionService):
        """Payee matching should strip whitespace."""
        txn = MockTransaction(
            amount=Decimal("50000.00"),
            payee="  Vendor A  ",
        )
        known_payees = {"vendor a", "vendor b"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        assert anomaly is None

    def test_empty_payee_returns_none(self, service: AnomalyDetectionService):
        """Empty payee should return None."""
        txn = MockTransaction(
            amount=Decimal("50000.00"),
            payee="",
        )
        known_payees = {"vendor a", "vendor b"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        assert anomaly is None

    def test_uses_description_as_fallback(self, service: AnomalyDetectionService):
        """Should use description if payee is empty."""
        txn = MockTransaction(
            amount=Decimal("15000.00"),
            payee="",
            description="Wire Transfer",
        )
        known_payees = {"vendor a", "vendor b"}

        anomaly = service.detect_new_payee_anomalies(txn, known_payees)

        # wire transfer is not in known_payees, so should be flagged
        assert anomaly is not None

    def test_custom_threshold(
        self, service_with_custom_config: AnomalyDetectionService
    ):
        """Custom threshold of $5,000 should be respected."""
        txn = MockTransaction(
            amount=Decimal("7000.00"),
            payee="Unknown Vendor",
        )
        known_payees = set()

        anomaly = service_with_custom_config.detect_new_payee_anomalies(
            txn, known_payees
        )

        assert anomaly is not None
        assert anomaly.threshold_value == Decimal("5000")

    def test_includes_payee_in_context(self, service: AnomalyDetectionService):
        """Payee should be included in anomaly context."""
        txn = MockTransaction(
            amount=Decimal("15000.00"),
            payee="Suspicious Corp",
        )

        anomaly = service.detect_new_payee_anomalies(txn, set())

        assert anomaly is not None
        assert anomaly.context["payee"] == "Suspicious Corp"


# =============================================================================
# TestDetectVelocityAnomalies
# =============================================================================


class TestDetectVelocityAnomalies:
    """Tests for transaction velocity spike detection."""

    def test_detects_high_daily_volume(self, service: AnomalyDetectionService):
        """Days with > 20 transactions should be flagged."""
        account_id = uuid4()
        today = date.today()
        transactions = [
            MockTransaction(date=today, account_id=account_id) for _ in range(25)
        ]

        anomalies = service.detect_velocity_anomalies(
            account_id, transactions, lookback_days=30
        )

        velocity_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.VELOCITY_SPIKE),
            None,
        )
        assert velocity_anomaly is not None
        assert velocity_anomaly.actual_value == Decimal("25")

    def test_does_not_flag_normal_volume(self, service: AnomalyDetectionService):
        """Normal transaction volume should not be flagged."""
        account_id = uuid4()
        today = date.today()
        transactions = [
            MockTransaction(date=today, account_id=account_id) for _ in range(5)
        ]

        anomalies = service.detect_velocity_anomalies(
            account_id, transactions, lookback_days=30
        )

        # Check for anomalies that are only due to exceeding max_transactions_per_day
        max_daily_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.VELOCITY_SPIKE
                and a.threshold_value == Decimal("20")
            ),
            None,
        )
        assert max_daily_anomaly is None

    def test_detects_velocity_spike_vs_average(self, service: AnomalyDetectionService):
        """Spike of 3x normal volume should be flagged."""
        account_id = uuid4()
        base_date = date.today() - timedelta(days=10)

        # Create normal days with 2 transactions each
        transactions = []
        for day_offset in range(10):
            day = base_date + timedelta(days=day_offset)
            transactions.extend(
                [MockTransaction(date=day, account_id=account_id) for _ in range(2)]
            )

        # Add spike day with 10 transactions (5x average)
        spike_day = date.today()
        transactions.extend(
            [MockTransaction(date=spike_day, account_id=account_id) for _ in range(10)]
        )

        anomalies = service.detect_velocity_anomalies(
            account_id, transactions, lookback_days=30
        )

        # Should detect velocity spike
        spike_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.VELOCITY_SPIKE
                and "multiplier" in a.context
            ),
            None,
        )
        assert spike_anomaly is not None

    def test_empty_transaction_list(self, service: AnomalyDetectionService):
        """Empty transaction list should return empty anomalies."""
        account_id = uuid4()

        anomalies = service.detect_velocity_anomalies(account_id, [], lookback_days=30)

        assert len(anomalies) == 0

    def test_custom_max_transactions_per_day(
        self, service_with_custom_config: AnomalyDetectionService
    ):
        """Custom threshold of 5 transactions per day should be respected."""
        account_id = uuid4()
        today = date.today()
        transactions = [
            MockTransaction(date=today, account_id=account_id) for _ in range(8)
        ]

        anomalies = service_with_custom_config.detect_velocity_anomalies(
            account_id, transactions, lookback_days=30
        )

        velocity_anomaly = next(
            (
                a
                for a in anomalies
                if a.anomaly_type == AnomalyType.VELOCITY_SPIKE
                and a.threshold_value == Decimal("5")
            ),
            None,
        )
        assert velocity_anomaly is not None

    def test_includes_context_details(self, service: AnomalyDetectionService):
        """Anomaly should include detailed context."""
        account_id = uuid4()
        today = date.today()
        transactions = [
            MockTransaction(date=today, account_id=account_id) for _ in range(25)
        ]

        anomalies = service.detect_velocity_anomalies(
            account_id, transactions, lookback_days=30
        )

        velocity_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.VELOCITY_SPIKE),
            None,
        )
        assert velocity_anomaly is not None
        assert "date" in velocity_anomaly.context
        assert "count" in velocity_anomaly.context


# =============================================================================
# TestCheckNegativeBalance
# =============================================================================


class TestCheckNegativeBalance:
    """Tests for negative balance detection."""

    def test_detects_negative_balance(self, service: AnomalyDetectionService):
        """Negative balance should be flagged."""
        account_id = uuid4()

        anomaly = service.check_negative_balance(
            account_id, Decimal("-500.00"), "Checking Account"
        )

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.NEGATIVE_BALANCE
        assert anomaly.actual_value == Decimal("-500.00")
        assert anomaly.account_id == account_id

    def test_does_not_flag_positive_balance(self, service: AnomalyDetectionService):
        """Positive balance should not be flagged."""
        account_id = uuid4()

        anomaly = service.check_negative_balance(
            account_id, Decimal("1000.00"), "Checking Account"
        )

        assert anomaly is None

    def test_does_not_flag_zero_balance(self, service: AnomalyDetectionService):
        """Zero balance should not be flagged."""
        account_id = uuid4()

        anomaly = service.check_negative_balance(
            account_id, Decimal("0.00"), "Checking Account"
        )

        assert anomaly is None

    def test_negative_balance_has_high_severity(self, service: AnomalyDetectionService):
        """Negative balance anomaly should have HIGH severity."""
        account_id = uuid4()

        anomaly = service.check_negative_balance(
            account_id, Decimal("-100.00"), "Checking Account"
        )

        assert anomaly is not None
        assert anomaly.severity == AnomalySeverity.HIGH

    def test_includes_account_name_in_description(
        self, service: AnomalyDetectionService
    ):
        """Account name should be in description."""
        account_id = uuid4()

        anomaly = service.check_negative_balance(
            account_id, Decimal("-500.00"), "Main Checking"
        )

        assert anomaly is not None
        assert "Main Checking" in anomaly.description

    def test_uses_account_id_when_no_name_provided(
        self, service: AnomalyDetectionService
    ):
        """Should use account ID in description when name is None."""
        account_id = uuid4()

        anomaly = service.check_negative_balance(account_id, Decimal("-500.00"))

        assert anomaly is not None
        assert str(account_id) in anomaly.description


# =============================================================================
# TestCalculateTransactionStats
# =============================================================================


class TestCalculateTransactionStats:
    """Tests for transaction statistics calculation."""

    def test_calculates_basic_stats(self, service: AnomalyDetectionService):
        """Should calculate count, total, mean, min, max."""
        transactions = [
            MockTransaction(amount=Decimal("100.00")),
            MockTransaction(amount=Decimal("200.00")),
            MockTransaction(amount=Decimal("300.00")),
        ]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.count == 3
        assert stats.total_amount == Decimal("600.00")
        assert stats.mean_amount == Decimal("200.00")
        assert stats.min_amount == Decimal("100.00")
        assert stats.max_amount == Decimal("300.00")

    def test_calculates_median_odd_count(self, service: AnomalyDetectionService):
        """Median for odd count should be middle value."""
        transactions = [
            MockTransaction(amount=Decimal("100.00")),
            MockTransaction(amount=Decimal("200.00")),
            MockTransaction(amount=Decimal("300.00")),
        ]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.median_amount == Decimal("200.00")

    def test_calculates_median_even_count(self, service: AnomalyDetectionService):
        """Median for even count should be average of middle two values."""
        transactions = [
            MockTransaction(amount=Decimal("100.00")),
            MockTransaction(amount=Decimal("200.00")),
            MockTransaction(amount=Decimal("300.00")),
            MockTransaction(amount=Decimal("400.00")),
        ]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.median_amount == Decimal("250.00")

    def test_calculates_standard_deviation(self, service: AnomalyDetectionService):
        """Standard deviation should be calculated correctly."""
        # Using values where std dev is easy to verify
        transactions = [
            MockTransaction(amount=Decimal("10.00")),
            MockTransaction(amount=Decimal("20.00")),
            MockTransaction(amount=Decimal("30.00")),
        ]

        stats = service.calculate_transaction_stats(transactions)

        # Mean = 20, variance = ((10-20)^2 + (20-20)^2 + (30-20)^2) / 3 = 200/3
        # std_dev = sqrt(200/3) ~ 8.165
        assert stats.std_dev > Decimal("8.0")
        assert stats.std_dev < Decimal("8.5")

    def test_empty_transaction_list(self, service: AnomalyDetectionService):
        """Empty list should return zero stats."""
        stats = service.calculate_transaction_stats([])

        assert stats.count == 0
        assert stats.total_amount == Decimal("0")
        assert stats.mean_amount == Decimal("0")
        assert stats.std_dev == Decimal("0")

    def test_single_transaction(self, service: AnomalyDetectionService):
        """Single transaction should have zero std dev."""
        transactions = [MockTransaction(amount=Decimal("100.00"))]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.count == 1
        assert stats.mean_amount == Decimal("100.00")
        assert stats.median_amount == Decimal("100.00")
        assert stats.std_dev == Decimal("0")

    def test_uses_absolute_values(self, service: AnomalyDetectionService):
        """Should use absolute values for amounts."""
        transactions = [
            MockTransaction(amount=Decimal("-100.00")),
            MockTransaction(amount=Decimal("200.00")),
        ]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.min_amount == Decimal("100.00")
        assert stats.max_amount == Decimal("200.00")
        assert stats.total_amount == Decimal("300.00")

    def test_calculates_date_range(self, service: AnomalyDetectionService):
        """Should calculate period start and end."""
        base_date = date(2024, 1, 1)
        transactions = [
            MockTransaction(date=base_date),
            MockTransaction(date=base_date + timedelta(days=10)),
            MockTransaction(date=base_date + timedelta(days=20)),
        ]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.period_start == date(2024, 1, 1)
        assert stats.period_end == date(2024, 1, 21)

    def test_calculates_transactions_per_day(self, service: AnomalyDetectionService):
        """Should calculate average transactions per day."""
        base_date = date(2024, 1, 1)
        # 10 transactions over 10 days (day 0 to day 9 = 10 days)
        transactions = [
            MockTransaction(date=base_date + timedelta(days=i)) for i in range(10)
        ]

        stats = service.calculate_transaction_stats(transactions)

        assert stats.avg_transactions_per_day == Decimal("1")
        assert stats.avg_transactions_per_week == Decimal("7")

    def test_includes_account_and_entity_ids(self, service: AnomalyDetectionService):
        """Should include provided account and entity IDs."""
        account_id = uuid4()
        entity_id = uuid4()
        transactions = [MockTransaction(amount=Decimal("100.00"))]

        stats = service.calculate_transaction_stats(
            transactions, account_id=account_id, entity_id=entity_id
        )

        assert stats.account_id == account_id
        assert stats.entity_id == entity_id


# =============================================================================
# TestAnomalyDataclass
# =============================================================================


class TestAnomalyDataclass:
    """Tests for Anomaly dataclass functionality."""

    def test_anomaly_creation_with_defaults(self):
        """Anomaly should be created with sensible defaults."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.LARGE_TRANSACTION,
            severity=AnomalySeverity.HIGH,
            description="Test anomaly",
        )

        assert anomaly.id is not None
        assert anomaly.status == AnomalyStatus.OPEN
        assert anomaly.detected_at is not None
        assert anomaly.context == {}
        assert anomaly.related_transaction_ids == []

    def test_mark_reviewed(self):
        """Anomaly can be marked as reviewed."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.LARGE_TRANSACTION,
            severity=AnomalySeverity.HIGH,
            description="Test anomaly",
        )
        reviewer_id = uuid4()

        anomaly.mark_reviewed(
            reviewer_id, AnomalyStatus.DISMISSED, notes="False positive"
        )

        assert anomaly.status == AnomalyStatus.DISMISSED
        assert anomaly.reviewed_by == reviewer_id
        assert anomaly.reviewed_at is not None
        assert anomaly.review_notes == "False positive"


# =============================================================================
# TestTransactionStatsDataclass
# =============================================================================


class TestTransactionStatsDataclass:
    """Tests for TransactionStats dataclass functionality."""

    def test_transaction_stats_defaults(self):
        """TransactionStats should have sensible defaults."""
        stats = TransactionStats()

        assert stats.count == 0
        assert stats.total_amount == Decimal("0")
        assert stats.mean_amount == Decimal("0")
        assert stats.std_dev == Decimal("0")
        assert stats.top_payees == []


# =============================================================================
# TestAnomalyDetectionConfig
# =============================================================================


class TestAnomalyDetectionConfig:
    """Tests for AnomalyDetectionConfig."""

    def test_default_config_values(self):
        """Default config should have reasonable thresholds."""
        config = AnomalyDetectionConfig()

        assert config.std_dev_threshold == Decimal("3.0")
        assert config.large_transaction_threshold.amount == Decimal("50000")
        assert config.new_payee_large_threshold.amount == Decimal("10000")
        assert config.structuring_threshold.amount == Decimal("10000")
        assert config.duplicate_time_window_hours == 24
        assert config.max_transactions_per_day == 20

    def test_custom_config_values(self):
        """Config should accept custom values."""
        config = AnomalyDetectionConfig(
            std_dev_threshold=Decimal("2.5"),
            large_transaction_threshold=Money(Decimal("25000")),
            max_transactions_per_day=10,
        )

        assert config.std_dev_threshold == Decimal("2.5")
        assert config.large_transaction_threshold.amount == Decimal("25000")
        assert config.max_transactions_per_day == 10


# =============================================================================
# TestTimingAnomalies
# =============================================================================


class TestTimingAnomalies:
    """Tests for timing-based anomaly detection."""

    def test_weekend_transaction_flagged_when_enabled(self):
        """Weekend transactions should be flagged when config enabled."""
        config = AnomalyDetectionConfig(flag_weekend_transactions=True)
        service = AnomalyDetectionService(config=config)

        # Find a Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0 and today.weekday() != 5:
            days_until_saturday = 7
        saturday = today + timedelta(days=days_until_saturday)

        txn = MockTransaction(amount=Decimal("100.00"), date=saturday)

        anomalies = service.analyze_transaction(txn)

        weekend_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.WEEKEND_TRANSACTION),
            None,
        )
        assert weekend_anomaly is not None

    def test_weekend_transaction_not_flagged_by_default(
        self, service: AnomalyDetectionService
    ):
        """Weekend transactions should not be flagged by default."""
        # Find a Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0 and today.weekday() != 5:
            days_until_saturday = 7
        saturday = today + timedelta(days=days_until_saturday)

        txn = MockTransaction(amount=Decimal("100.00"), date=saturday)

        anomalies = service.analyze_transaction(txn)

        weekend_anomaly = next(
            (a for a in anomalies if a.anomaly_type == AnomalyType.WEEKEND_TRANSACTION),
            None,
        )
        assert weekend_anomaly is None
