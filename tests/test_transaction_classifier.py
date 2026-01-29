"""Tests for TransactionClassifier.

Tests each of the 18 transaction types in priority order.
"""

from datetime import date
from decimal import Decimal

import pytest

from family_office_ledger.domain.value_objects import ExpenseCategory, TransactionType
from family_office_ledger.parsers.bank_parsers import ParsedTransaction
from family_office_ledger.services.transaction_classifier import (
    SecurityLookup,
    TransactionClassifier,
)


class MockSecurityLookup:
    """Mock security lookup for testing."""

    def __init__(self, qsbs_symbols: set[str] | None = None) -> None:
        """Initialize with optional set of QSBS-eligible symbols."""
        self._qsbs_symbols = qsbs_symbols or set()

    def is_qsbs_eligible(self, symbol: str | None, cusip: str | None) -> bool | None:
        """Return True for symbols in QSBS set, False otherwise, None if not found."""
        if symbol and symbol in self._qsbs_symbols:
            return True
        if cusip and cusip in self._qsbs_symbols:
            return True
        # Return None if security not found (not in any list)
        if symbol or cusip:
            return False
        return None


def make_txn(
    description: str = "TEST",
    amount: Decimal | str = "0.00",
    other_party: str | None = None,
    symbol: str | None = None,
    cusip: str | None = None,
    activity_type: str | None = None,
) -> ParsedTransaction:
    """Create a ParsedTransaction for testing."""
    return ParsedTransaction(
        import_id="test123",
        date=date(2026, 1, 15),
        description=description,
        amount=Decimal(amount) if isinstance(amount, str) else amount,
        account_number="1234",
        account_name="Test Account",
        other_party=other_party,
        symbol=symbol,
        cusip=cusip,
        activity_type=activity_type,
    )


class TestTransactionClassifier:
    """Test suite for TransactionClassifier."""

    @pytest.fixture
    def classifier(self) -> TransactionClassifier:
        """Create classifier without security lookup."""
        return TransactionClassifier()

    @pytest.fixture
    def classifier_with_qsbs(self) -> TransactionClassifier:
        """Create classifier with QSBS-eligible symbols."""
        lookup = MockSecurityLookup(qsbs_symbols={"STARTUP", "QSBS123", "12345Q123"})
        return TransactionClassifier(security_lookup=lookup)


class TestInterestClassification(TestTransactionClassifier):
    """Tests for INTEREST classification (Rule 1)."""

    def test_classify_interest_keyword(self, classifier: TransactionClassifier) -> None:
        """INTEREST keyword with positive amount, no security."""
        txn = make_txn(description="INTEREST PAYMENT", amount="50.00")
        assert classifier.classify(txn) == TransactionType.INTEREST

    def test_classify_margin_int(self, classifier: TransactionClassifier) -> None:
        """MARGIN INT keyword variant."""
        txn = make_txn(description="MARGIN INT CREDIT", amount="25.00")
        assert classifier.classify(txn) == TransactionType.INTEREST

    def test_classify_int_payment(self, classifier: TransactionClassifier) -> None:
        """INT PAYMENT keyword variant."""
        txn = make_txn(description="INT PAYMENT Q4", amount="100.00")
        assert classifier.classify(txn) == TransactionType.INTEREST

    def test_interest_negative_not_interest(
        self, classifier: TransactionClassifier
    ) -> None:
        """Negative interest is not classified as INTEREST."""
        txn = make_txn(description="INTEREST CHARGE", amount="-50.00")
        assert classifier.classify(txn) != TransactionType.INTEREST

    def test_interest_with_security_not_interest(
        self, classifier: TransactionClassifier
    ) -> None:
        """Interest with security identifier is not classified as INTEREST."""
        txn = make_txn(description="INTEREST PAYMENT", amount="50.00", symbol="BOND")
        assert classifier.classify(txn) != TransactionType.INTEREST

    def test_interest_case_insensitive(self, classifier: TransactionClassifier) -> None:
        """Keywords match case-insensitively."""
        txn = make_txn(description="interest payment", amount="50.00")
        assert classifier.classify(txn) == TransactionType.INTEREST


class TestExpenseClassification(TestTransactionClassifier):
    """Tests for EXPENSE classification (Rule 2)."""

    def test_classify_legal_fee(self, classifier: TransactionClassifier) -> None:
        """LEGAL FEE keyword with negative amount."""
        txn = make_txn(description="LEGAL FEE - GCA LAW", amount="-5000.00")
        assert classifier.classify(txn) == TransactionType.EXPENSE

    def test_classify_professional(self, classifier: TransactionClassifier) -> None:
        """PROFESSIONAL keyword."""
        txn = make_txn(description="PROFESSIONAL SERVICES", amount="-2500.00")
        assert classifier.classify(txn) == TransactionType.EXPENSE

    def test_classify_accounting(self, classifier: TransactionClassifier) -> None:
        """ACCOUNTING keyword."""
        txn = make_txn(description="ACCOUNTING FEE", amount="-1500.00")
        assert classifier.classify(txn) == TransactionType.EXPENSE

    def test_classify_advisory(self, classifier: TransactionClassifier) -> None:
        """ADVISORY keyword."""
        txn = make_txn(description="ADVISORY FEE", amount="-3000.00")
        assert classifier.classify(txn) == TransactionType.EXPENSE

    def test_expense_positive_not_expense(
        self, classifier: TransactionClassifier
    ) -> None:
        """Positive amount with expense keyword is not classified as EXPENSE."""
        txn = make_txn(description="LEGAL FEE REFUND", amount="5000.00")
        assert classifier.classify(txn) != TransactionType.EXPENSE


class TestTrustTransferClassification(TestTransactionClassifier):
    """Tests for TRUST_TRANSFER classification (Rule 3)."""

    def test_classify_trust_transfer_in_other_party(
        self, classifier: TransactionClassifier
    ) -> None:
        """Other party contains TRUST."""
        txn = make_txn(
            description="WIRE TRANSFER",
            amount="10000.00",
            other_party="THE KANEDA TRUST",
        )
        assert classifier.classify(txn) == TransactionType.TRUST_TRANSFER

    def test_classify_trust_transfer_negative(
        self, classifier: TransactionClassifier
    ) -> None:
        """Negative trust transfer."""
        txn = make_txn(
            description="WIRE TO TRUST",
            amount="-10000.00",
            other_party="THE IKIGAI TRUST",
        )
        assert classifier.classify(txn) == TransactionType.TRUST_TRANSFER

    def test_trust_in_description_not_sufficient(
        self, classifier: TransactionClassifier
    ) -> None:
        """TRUST in description alone doesn't trigger without other_party."""
        txn = make_txn(description="WIRE TO TRUST", amount="10000.00")
        # Should not be TRUST_TRANSFER without other_party containing TRUST
        assert classifier.classify(txn) != TransactionType.TRUST_TRANSFER


class TestLoanClassification(TestTransactionClassifier):
    """Tests for LOAN classification (Rule 4)."""

    def test_classify_loan_to(self, classifier: TransactionClassifier) -> None:
        """LOAN TO keyword with negative amount."""
        txn = make_txn(description="LOAN TO PARTNER", amount="-50000.00")
        assert classifier.classify(txn) == TransactionType.LOAN

    def test_classify_note_receivable(self, classifier: TransactionClassifier) -> None:
        """NOTE RECEIVABLE keyword."""
        txn = make_txn(description="NOTE RECEIVABLE - ABC LLC", amount="-25000.00")
        assert classifier.classify(txn) == TransactionType.LOAN

    def test_classify_advance_to(self, classifier: TransactionClassifier) -> None:
        """ADVANCE TO keyword."""
        txn = make_txn(description="ADVANCE TO SUBSIDIARY", amount="-10000.00")
        assert classifier.classify(txn) == TransactionType.LOAN

    def test_loan_positive_not_loan(self, classifier: TransactionClassifier) -> None:
        """Positive amount with loan keyword is not LOAN."""
        txn = make_txn(description="LOAN TO PARTNER", amount="50000.00")
        assert classifier.classify(txn) != TransactionType.LOAN


class TestLoanRepaymentClassification(TestTransactionClassifier):
    """Tests for LOAN_REPAYMENT classification (Rule 5)."""

    def test_classify_loan_repayment(self, classifier: TransactionClassifier) -> None:
        """LOAN REPAYMENT keyword with positive amount."""
        txn = make_txn(description="LOAN REPAYMENT FROM ABC", amount="10000.00")
        assert classifier.classify(txn) == TransactionType.LOAN_REPAYMENT

    def test_classify_note_repayment(self, classifier: TransactionClassifier) -> None:
        """NOTE REPAYMENT keyword."""
        txn = make_txn(description="NOTE REPAYMENT", amount="5000.00")
        assert classifier.classify(txn) == TransactionType.LOAN_REPAYMENT

    def test_loan_repayment_negative_not_repayment(
        self, classifier: TransactionClassifier
    ) -> None:
        """Negative amount with repayment keyword is not LOAN_REPAYMENT."""
        txn = make_txn(description="LOAN REPAYMENT", amount="-10000.00")
        assert classifier.classify(txn) != TransactionType.LOAN_REPAYMENT


class TestBrokerFeesClassification(TestTransactionClassifier):
    """Tests for BROKER_FEES classification (Rule 6)."""

    def test_classify_broker_fee(self, classifier: TransactionClassifier) -> None:
        """BROKER FEE keyword with negative amount."""
        txn = make_txn(description="BROKER FEE - BGC PARTNERS", amount="-500.00")
        assert classifier.classify(txn) == TransactionType.BROKER_FEES

    def test_classify_transaction_fee(self, classifier: TransactionClassifier) -> None:
        """TRANSACTION FEE keyword."""
        txn = make_txn(description="TRANSACTION FEE", amount="-250.00")
        assert classifier.classify(txn) == TransactionType.BROKER_FEES

    def test_classify_secondary_market(self, classifier: TransactionClassifier) -> None:
        """SECONDARY MARKET keyword."""
        txn = make_txn(description="SECONDARY MARKET FEE", amount="-1000.00")
        assert classifier.classify(txn) == TransactionType.BROKER_FEES

    def test_broker_fee_positive_not_fee(
        self, classifier: TransactionClassifier
    ) -> None:
        """Positive amount with fee keyword is not BROKER_FEES."""
        txn = make_txn(description="BROKER FEE REFUND", amount="500.00")
        assert classifier.classify(txn) != TransactionType.BROKER_FEES


class TestReturnOfFundsClassification(TestTransactionClassifier):
    """Tests for RETURN_OF_FUNDS classification (Rule 7)."""

    def test_classify_refund(self, classifier: TransactionClassifier) -> None:
        """REFUND keyword with positive amount."""
        txn = make_txn(description="REFUND OF CAPITAL", amount="2500.00")
        assert classifier.classify(txn) == TransactionType.RETURN_OF_FUNDS

    def test_classify_return_of_funds(self, classifier: TransactionClassifier) -> None:
        """RETURN OF FUNDS keyword."""
        txn = make_txn(description="RETURN OF FUNDS - CANCELLED", amount="5000.00")
        assert classifier.classify(txn) == TransactionType.RETURN_OF_FUNDS

    def test_classify_cancelled(self, classifier: TransactionClassifier) -> None:
        """CANCELLED keyword."""
        txn = make_txn(description="CANCELLED INVESTMENT", amount="10000.00")
        assert classifier.classify(txn) == TransactionType.RETURN_OF_FUNDS

    def test_return_negative_not_return(
        self, classifier: TransactionClassifier
    ) -> None:
        """Negative amount with return keyword is not RETURN_OF_FUNDS."""
        txn = make_txn(description="REFUND PAYMENT", amount="-2500.00")
        assert classifier.classify(txn) != TransactionType.RETURN_OF_FUNDS


class TestOzFundPurchaseClassification(TestTransactionClassifier):
    """Tests for PURCHASE_OZ_FUND classification (Rule 8)."""

    def test_classify_oz_fund(self, classifier: TransactionClassifier) -> None:
        """OZ FUND keyword with negative amount."""
        txn = make_txn(description="BV SOUTH SLC OZ FUND", amount="-100000.00")
        assert classifier.classify(txn) == TransactionType.PURCHASE_OZ_FUND

    def test_classify_opportunity_zone(self, classifier: TransactionClassifier) -> None:
        """OPPORTUNITY ZONE keyword."""
        txn = make_txn(description="OPPORTUNITY ZONE INVESTMENT", amount="-50000.00")
        assert classifier.classify(txn) == TransactionType.PURCHASE_OZ_FUND

    def test_oz_fund_positive_not_purchase(
        self, classifier: TransactionClassifier
    ) -> None:
        """Positive OZ fund transaction is not PURCHASE_OZ_FUND."""
        txn = make_txn(description="OZ FUND DISTRIBUTION", amount="5000.00")
        assert classifier.classify(txn) != TransactionType.PURCHASE_OZ_FUND


class TestContributionDistributionClassification(TestTransactionClassifier):
    """Tests for CONTRIBUTION_DISTRIBUTION classification (Rule 9)."""

    def test_classify_lp_fund(self, classifier: TransactionClassifier) -> None:
        """Other party contains LP."""
        txn = make_txn(
            description="CAPITAL CALL",
            amount="-50000.00",
            other_party="ZIGG CAPITAL I LP",
        )
        assert classifier.classify(txn) == TransactionType.CONTRIBUTION_DISTRIBUTION

    def test_classify_fund_distribution(
        self, classifier: TransactionClassifier
    ) -> None:
        """Other party contains FUND."""
        txn = make_txn(
            description="DISTRIBUTION",
            amount="25000.00",
            other_party="ABC GROWTH FUND II",
        )
        assert classifier.classify(txn) == TransactionType.CONTRIBUTION_DISTRIBUTION

    def test_classify_capital_partners(self, classifier: TransactionClassifier) -> None:
        """Other party contains CAPITAL."""
        txn = make_txn(
            description="INVESTMENT",
            amount="-100000.00",
            other_party="ACME CAPITAL",
        )
        assert classifier.classify(txn) == TransactionType.CONTRIBUTION_DISTRIBUTION

    def test_classify_partners_fund(self, classifier: TransactionClassifier) -> None:
        """Other party contains PARTNERS."""
        txn = make_txn(
            description="CONTRIBUTION",
            amount="-75000.00",
            other_party="XYZ VENTURE PARTNERS",
        )
        assert classifier.classify(txn) == TransactionType.CONTRIBUTION_DISTRIBUTION


class TestContributionToEntityClassification(TestTransactionClassifier):
    """Tests for CONTRIBUTION_TO_ENTITY classification (Rule 10)."""

    def test_classify_capital_contribution(
        self, classifier: TransactionClassifier
    ) -> None:
        """CAPITAL CONTRIBUTION keyword with positive amount."""
        txn = make_txn(
            description="CAPITAL CONTRIBUTION FROM MEMBER", amount="100000.00"
        )
        assert classifier.classify(txn) == TransactionType.CONTRIBUTION_TO_ENTITY

    def test_classify_member_contribution(
        self, classifier: TransactionClassifier
    ) -> None:
        """MEMBER CONTRIBUTION keyword."""
        txn = make_txn(description="MEMBER CONTRIBUTION", amount="50000.00")
        assert classifier.classify(txn) == TransactionType.CONTRIBUTION_TO_ENTITY

    def test_contribution_negative_not_contribution(
        self, classifier: TransactionClassifier
    ) -> None:
        """Negative amount is not CONTRIBUTION_TO_ENTITY."""
        txn = make_txn(description="CAPITAL CONTRIBUTION", amount="-100000.00")
        assert classifier.classify(txn) != TransactionType.CONTRIBUTION_TO_ENTITY


class TestPublicMarketClassification(TestTransactionClassifier):
    """Tests for PUBLIC_MARKET classification (Rule 11)."""

    def test_classify_treasury(self, classifier: TransactionClassifier) -> None:
        """TREASURY keyword."""
        txn = make_txn(description="US TREASURY PURCHASE", amount="-100000.00")
        assert classifier.classify(txn) == TransactionType.PUBLIC_MARKET

    def test_classify_tbill(self, classifier: TransactionClassifier) -> None:
        """T-BILL keyword."""
        txn = make_txn(description="T-BILL MATURITY", amount="100500.00")
        assert classifier.classify(txn) == TransactionType.PUBLIC_MARKET

    def test_classify_crypto(self, classifier: TransactionClassifier) -> None:
        """CRYPTO keyword."""
        txn = make_txn(description="CRYPTO SALE", amount="50000.00")
        assert classifier.classify(txn) == TransactionType.PUBLIC_MARKET

    def test_classify_hyperliquid(self, classifier: TransactionClassifier) -> None:
        """HYPERLIQUID keyword."""
        txn = make_txn(description="HYPERLIQUID TOKEN SALE", amount="25000.00")
        assert classifier.classify(txn) == TransactionType.PUBLIC_MARKET

    def test_classify_bitcoin(self, classifier: TransactionClassifier) -> None:
        """BITCOIN keyword."""
        txn = make_txn(description="BITCOIN PURCHASE", amount="-10000.00")
        assert classifier.classify(txn) == TransactionType.PUBLIC_MARKET


class TestLiquidationClassification(TestTransactionClassifier):
    """Tests for LIQUIDATION classification (Rule 12)."""

    def test_classify_liquidation(self, classifier: TransactionClassifier) -> None:
        """LIQUIDATION keyword."""
        txn = make_txn(description="LIQUIDATION PROCEEDS", amount="500000.00")
        assert classifier.classify(txn) == TransactionType.LIQUIDATION

    def test_classify_escrow_release(self, classifier: TransactionClassifier) -> None:
        """ESCROW RELEASE keyword."""
        txn = make_txn(description="ESCROW RELEASE - ACQUIOM", amount="75000.00")
        assert classifier.classify(txn) == TransactionType.LIQUIDATION

    def test_classify_wind_down(self, classifier: TransactionClassifier) -> None:
        """WIND DOWN keyword."""
        txn = make_txn(description="WIND DOWN DISTRIBUTION", amount="25000.00")
        assert classifier.classify(txn) == TransactionType.LIQUIDATION


class TestSaleClassification(TestTransactionClassifier):
    """Tests for SALE_QSBS and SALE_NON_QSBS classification (Rule 13)."""

    def test_classify_sale_qsbs(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Sale of QSBS-eligible security."""
        txn = make_txn(
            description="STOCK SALE",
            amount="100000.00",
            symbol="STARTUP",
            activity_type="SOLD",
        )
        assert classifier_with_qsbs.classify(txn) == TransactionType.SALE_QSBS

    def test_classify_sale_non_qsbs(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Sale of non-QSBS security."""
        txn = make_txn(
            description="STOCK SALE",
            amount="50000.00",
            symbol="NONQSBS",
            activity_type="SOLD",
        )
        assert classifier_with_qsbs.classify(txn) == TransactionType.SALE_NON_QSBS

    def test_classify_sale_via_cusip(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Sale identified by CUSIP."""
        txn = make_txn(
            description="REDEMPTION",
            amount="75000.00",
            cusip="12345Q123",
            activity_type="REDEMPTION",
        )
        assert classifier_with_qsbs.classify(txn) == TransactionType.SALE_QSBS

    def test_classify_sale_without_lookup(
        self, classifier: TransactionClassifier
    ) -> None:
        """Sale without security lookup defaults to NON_QSBS."""
        txn = make_txn(
            description="STOCK SALE",
            amount="100000.00",
            symbol="ANY",
            activity_type="SOLD",
        )
        assert classifier.classify(txn) == TransactionType.SALE_NON_QSBS

    def test_sale_requires_activity_type(
        self, classifier: TransactionClassifier
    ) -> None:
        """Sale requires activity_type to match."""
        txn = make_txn(
            description="SOLD SHARES",
            amount="100000.00",
            symbol="ANY",
        )
        # Without activity_type, won't be classified as sale
        assert classifier.classify(txn) not in (
            TransactionType.SALE_QSBS,
            TransactionType.SALE_NON_QSBS,
        )


class TestPurchaseClassification(TestTransactionClassifier):
    """Tests for PURCHASE_QSBS and PURCHASE_NON_QSBS classification (Rule 14)."""

    def test_classify_purchase_qsbs(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Purchase of QSBS-eligible security."""
        txn = make_txn(
            description="STOCK PURCHASE",
            amount="-100000.00",
            symbol="STARTUP",
            activity_type="BOUGHT",
        )
        assert classifier_with_qsbs.classify(txn) == TransactionType.PURCHASE_QSBS

    def test_classify_purchase_non_qsbs(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Purchase of non-QSBS security."""
        txn = make_txn(
            description="STOCK PURCHASE",
            amount="-50000.00",
            symbol="BIGCO",
            activity_type="BOUGHT",
        )
        assert classifier_with_qsbs.classify(txn) == TransactionType.PURCHASE_NON_QSBS

    def test_classify_purchase_via_cusip(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Purchase identified by CUSIP."""
        txn = make_txn(
            description="INVESTMENT",
            amount="-75000.00",
            cusip="12345Q123",
            activity_type="PURCHASE",
        )
        assert classifier_with_qsbs.classify(txn) == TransactionType.PURCHASE_QSBS

    def test_classify_purchase_negative_amount_with_security(
        self, classifier: TransactionClassifier
    ) -> None:
        """Negative amount with security identifier is purchase."""
        txn = make_txn(
            description="INVESTMENT IN XYZ",
            amount="-25000.00",
            symbol="XYZ",
        )
        assert classifier.classify(txn) == TransactionType.PURCHASE_NON_QSBS

    def test_classify_purchase_without_lookup(
        self, classifier: TransactionClassifier
    ) -> None:
        """Purchase without security lookup defaults to NON_QSBS."""
        txn = make_txn(
            description="STOCK PURCHASE",
            amount="-100000.00",
            symbol="ANY",
            activity_type="BOUGHT",
        )
        assert classifier.classify(txn) == TransactionType.PURCHASE_NON_QSBS


class TestTransferClassification(TestTransactionClassifier):
    """Tests for TRANSFER classification (Rule 15)."""

    def test_classify_wire_transfer(self, classifier: TransactionClassifier) -> None:
        """WIRE TRANSFER keyword."""
        txn = make_txn(description="WIRE TRANSFER TO ABC ACCOUNT", amount="-50000.00")
        assert classifier.classify(txn) == TransactionType.TRANSFER

    def test_classify_ach_transfer(self, classifier: TransactionClassifier) -> None:
        """ACH TRANSFER keyword."""
        txn = make_txn(description="ACH TRANSFER FROM XYZ", amount="10000.00")
        assert classifier.classify(txn) == TransactionType.TRANSFER

    def test_classify_internal_transfer(
        self, classifier: TransactionClassifier
    ) -> None:
        """INTERNAL TRANSFER keyword."""
        txn = make_txn(description="INTERNAL TRANSFER", amount="25000.00")
        assert classifier.classify(txn) == TransactionType.TRANSFER


class TestUnclassifiedClassification(TestTransactionClassifier):
    """Tests for UNCLASSIFIED classification (Rule 16 - fallback)."""

    def test_classify_unclassified_unknown(
        self, classifier: TransactionClassifier
    ) -> None:
        """Unknown transaction type defaults to UNCLASSIFIED."""
        txn = make_txn(description="RANDOM PAYMENT", amount="1000.00")
        assert classifier.classify(txn) == TransactionType.UNCLASSIFIED

    def test_classify_unclassified_no_keywords(
        self, classifier: TransactionClassifier
    ) -> None:
        """Transaction with no matching keywords."""
        txn = make_txn(description="XYZ123", amount="-500.00")
        assert classifier.classify(txn) == TransactionType.UNCLASSIFIED

    def test_classify_unclassified_empty_description(
        self, classifier: TransactionClassifier
    ) -> None:
        """Transaction with empty description."""
        txn = make_txn(description="", amount="100.00")
        assert classifier.classify(txn) == TransactionType.UNCLASSIFIED


class TestPriorityOrder(TestTransactionClassifier):
    """Tests to verify rules are evaluated in correct priority order."""

    def test_interest_before_expense(self, classifier: TransactionClassifier) -> None:
        """INTEREST (Rule 1) takes priority even if EXPENSE keywords present."""
        # This shouldn't happen in real data, but verify priority
        txn = make_txn(description="INTEREST LEGAL FEE", amount="50.00")
        # Should be INTEREST (Rule 1) not EXPENSE (Rule 2)
        assert classifier.classify(txn) == TransactionType.INTEREST

    def test_trust_transfer_before_transfer(
        self, classifier: TransactionClassifier
    ) -> None:
        """TRUST_TRANSFER (Rule 3) before TRANSFER (Rule 15)."""
        txn = make_txn(
            description="WIRE TRANSFER",
            amount="10000.00",
            other_party="KANEDA TRUST",
        )
        assert classifier.classify(txn) == TransactionType.TRUST_TRANSFER

    def test_loan_before_purchase(self, classifier: TransactionClassifier) -> None:
        """LOAN (Rule 4) before PURCHASE (Rule 14)."""
        txn = make_txn(
            description="LOAN TO STARTUP",
            amount="-50000.00",
            symbol="START",
        )
        assert classifier.classify(txn) == TransactionType.LOAN

    def test_oz_fund_before_contribution_distribution(
        self, classifier: TransactionClassifier
    ) -> None:
        """PURCHASE_OZ_FUND (Rule 8) before CONTRIBUTION_DISTRIBUTION (Rule 9)."""
        txn = make_txn(
            description="OZ FUND INVESTMENT",
            amount="-100000.00",
            other_party="ABC OZ FUND LP",
        )
        # Should be OZ_FUND (Rule 8) not CONTRIBUTION_DISTRIBUTION (Rule 9)
        assert classifier.classify(txn) == TransactionType.PURCHASE_OZ_FUND

    def test_public_market_before_liquidation(
        self, classifier: TransactionClassifier
    ) -> None:
        """PUBLIC_MARKET (Rule 11) before LIQUIDATION (Rule 12)."""
        txn = make_txn(
            description="TREASURY LIQUIDATION",
            amount="50000.00",
        )
        # Should be PUBLIC_MARKET (Rule 11) not LIQUIDATION (Rule 12)
        assert classifier.classify(txn) == TransactionType.PUBLIC_MARKET

    def test_liquidation_before_sale(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """LIQUIDATION (Rule 12) before SALE (Rule 13)."""
        txn = make_txn(
            description="LIQUIDATION PROCEEDS",
            amount="100000.00",
            symbol="STARTUP",
            activity_type="SOLD",
        )
        # Should be LIQUIDATION (Rule 12) not SALE (Rule 13)
        assert classifier_with_qsbs.classify(txn) == TransactionType.LIQUIDATION


class TestCaseInsensitivity(TestTransactionClassifier):
    """Tests for case-insensitive keyword matching."""

    def test_lowercase_keywords(self, classifier: TransactionClassifier) -> None:
        """Lowercase keywords are matched."""
        txn = make_txn(description="interest payment", amount="50.00")
        assert classifier.classify(txn) == TransactionType.INTEREST

    def test_mixed_case_keywords(self, classifier: TransactionClassifier) -> None:
        """Mixed case keywords are matched."""
        txn = make_txn(description="Legal Fee Payment", amount="-5000.00")
        assert classifier.classify(txn) == TransactionType.EXPENSE

    def test_uppercase_other_party(self, classifier: TransactionClassifier) -> None:
        """Other party matching is case-insensitive."""
        txn = make_txn(
            description="WIRE",
            amount="10000.00",
            other_party="the kaneda trust",
        )
        assert classifier.classify(txn) == TransactionType.TRUST_TRANSFER


class TestEdgeCases(TestTransactionClassifier):
    """Tests for edge cases."""

    def test_zero_amount(self, classifier: TransactionClassifier) -> None:
        """Zero amount transaction."""
        txn = make_txn(description="INTEREST", amount="0.00")
        # Zero is not positive, so won't match INTEREST
        assert classifier.classify(txn) != TransactionType.INTEREST

    def test_very_large_amount(self, classifier: TransactionClassifier) -> None:
        """Very large amounts work correctly."""
        txn = make_txn(description="INTEREST PAYMENT", amount="999999999.99")
        assert classifier.classify(txn) == TransactionType.INTEREST

    def test_empty_other_party(self, classifier: TransactionClassifier) -> None:
        """None other_party is handled."""
        txn = make_txn(description="WIRE TRANSFER", amount="10000.00", other_party=None)
        assert classifier.classify(txn) == TransactionType.TRANSFER

    def test_description_and_other_party_combined(
        self, classifier: TransactionClassifier
    ) -> None:
        """Keywords in other_party are also matched."""
        txn = make_txn(
            description="PAYMENT",
            amount="-5000.00",
            other_party="LEGAL FEE SERVICES INC",
        )
        assert classifier.classify(txn) == TransactionType.EXPENSE

    def test_security_lookup_returns_none(
        self, classifier_with_qsbs: TransactionClassifier
    ) -> None:
        """Security not found in lookup returns NON_QSBS."""
        txn = make_txn(
            description="PURCHASE",
            amount="-10000.00",
            symbol="UNKNOWN",
            activity_type="BOUGHT",
        )
        # UNKNOWN not in QSBS list, lookup returns False → NON_QSBS
        assert classifier_with_qsbs.classify(txn) == TransactionType.PURCHASE_NON_QSBS


class TestExpenseCategoryInference(TestTransactionClassifier):
    """Tests for expense category inference."""

    def test_infer_legal_category(self, classifier: TransactionClassifier) -> None:
        """Infer LEGAL category from attorney keyword."""
        txn = make_txn(description="PAYMENT TO ATTORNEY SMITH", amount="-5000.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.LEGAL

    def test_infer_accounting_category(self, classifier: TransactionClassifier) -> None:
        """Infer ACCOUNTING category from CPA keyword."""
        txn = make_txn(description="CPA SERVICES - TAX PREP", amount="-2500.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.ACCOUNTING

    def test_infer_rent_category(self, classifier: TransactionClassifier) -> None:
        """Infer RENT category from rent keyword."""
        txn = make_txn(description="MONTHLY RENT PAYMENT", amount="-3000.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.RENT

    def test_infer_utilities_category(self, classifier: TransactionClassifier) -> None:
        """Infer UTILITIES category from electric keyword."""
        txn = make_txn(description="PG&E ELECTRIC BILL", amount="-150.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.UTILITIES

    def test_infer_software_category(self, classifier: TransactionClassifier) -> None:
        """Infer SOFTWARE category from SaaS keyword."""
        txn = make_txn(description="SLACK SUBSCRIPTION", amount="-99.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.SOFTWARE

    def test_infer_payroll_category(self, classifier: TransactionClassifier) -> None:
        """Infer PAYROLL category from payroll keyword."""
        txn = make_txn(description="GUSTO PAYROLL PROCESSING", amount="-500.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.PAYROLL

    def test_infer_travel_category(self, classifier: TransactionClassifier) -> None:
        """Infer TRAVEL category from airline keyword."""
        txn = make_txn(description="DELTA AIRLINES TICKET", amount="-450.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.TRAVEL

    def test_infer_meals_category(self, classifier: TransactionClassifier) -> None:
        """Infer MEALS category from restaurant keyword."""
        txn = make_txn(description="DOORDASH RESTAURANT ORDER", amount="-35.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.MEALS

    def test_infer_insurance_category(self, classifier: TransactionClassifier) -> None:
        """Infer INSURANCE category from insurance keyword."""
        txn = make_txn(description="GEICO INSURANCE PREMIUM", amount="-120.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.INSURANCE

    def test_infer_hosting_category(self, classifier: TransactionClassifier) -> None:
        """Infer HOSTING category from AWS keyword."""
        txn = make_txn(description="AWS CLOUD HOSTING", amount="-250.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.HOSTING

    def test_infer_marketing_category(self, classifier: TransactionClassifier) -> None:
        """Infer MARKETING category from advertising keyword."""
        txn = make_txn(description="GOOGLE ADS CAMPAIGN", amount="-1000.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.MARKETING

    def test_infer_consulting_category(self, classifier: TransactionClassifier) -> None:
        """Infer CONSULTING category from consultant keyword."""
        txn = make_txn(description="MANAGEMENT CONSULTANT FEES", amount="-5000.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.CONSULTING

    def test_infer_bank_fees_category(self, classifier: TransactionClassifier) -> None:
        """Infer BANK_FEES category from wire fee keyword."""
        txn = make_txn(description="WIRE FEE CHARGE", amount="-25.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.BANK_FEES

    def test_infer_office_supplies_category(
        self, classifier: TransactionClassifier
    ) -> None:
        """Infer OFFICE_SUPPLIES category from supplies keyword."""
        txn = make_txn(description="STAPLES OFFICE SUPPLIES", amount="-75.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.OFFICE_SUPPLIES

    def test_infer_hardware_category(self, classifier: TransactionClassifier) -> None:
        """Infer HARDWARE category from laptop keyword."""
        txn = make_txn(description="APPLE LAPTOP PURCHASE", amount="-1500.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.HARDWARE

    def test_infer_charitable_category(self, classifier: TransactionClassifier) -> None:
        """Infer CHARITABLE category from donation keyword."""
        txn = make_txn(description="DONATION TO CHARITY", amount="-500.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.CHARITABLE

    def test_infer_entertainment_category(
        self, classifier: TransactionClassifier
    ) -> None:
        """Infer ENTERTAINMENT category from movie keyword."""
        txn = make_txn(description="MOVIE THEATER TICKETS", amount="-30.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.ENTERTAINMENT

    def test_infer_interest_expense_category(
        self, classifier: TransactionClassifier
    ) -> None:
        """Infer INTEREST_EXPENSE category from interest expense keyword."""
        txn = make_txn(description="LOAN INTEREST EXPENSE", amount="-200.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.INTEREST_EXPENSE

    def test_no_category_match_returns_none(
        self, classifier: TransactionClassifier
    ) -> None:
        """No matching keywords returns None."""
        txn = make_txn(description="RANDOM PAYMENT XYZ123", amount="-100.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category is None

    def test_category_inference_case_insensitive(
        self, classifier: TransactionClassifier
    ) -> None:
        """Category inference is case-insensitive."""
        txn = make_txn(description="attorney smith legal services", amount="-5000.00")
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.LEGAL

    def test_category_inference_from_other_party(
        self, classifier: TransactionClassifier
    ) -> None:
        """Category can be inferred from other_party field."""
        txn = make_txn(
            description="PAYMENT",
            amount="-3000.00",
            other_party="DELTA AIRLINES INC",
        )
        _, category = classifier.classify_with_expense_category(txn)
        assert category == ExpenseCategory.TRAVEL

    def test_classify_with_expense_category_returns_tuple(
        self, classifier: TransactionClassifier
    ) -> None:
        """classify_with_expense_category returns (TransactionType, ExpenseCategory|None)."""
        txn = make_txn(description="LEGAL FEE", amount="-5000.00")
        result = classifier.classify_with_expense_category(txn)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], TransactionType)
        assert result[1] is None or isinstance(result[1], ExpenseCategory)

    def test_classify_with_expense_category_matches_classify(
        self, classifier: TransactionClassifier
    ) -> None:
        """TransactionType from classify_with_expense_category matches classify()."""
        txn = make_txn(description="LEGAL FEE", amount="-5000.00")
        txn_type_only = classifier.classify(txn)
        txn_type_with_cat, _ = classifier.classify_with_expense_category(txn)
        assert txn_type_only == txn_type_with_cat

    def test_multiple_keywords_first_match_wins(
        self, classifier: TransactionClassifier
    ) -> None:
        """When multiple keywords match, first category in dict wins."""
        txn = make_txn(description="LEGAL CONSULTING SERVICES", amount="-5000.00")
        _, category = classifier.classify_with_expense_category(txn)
        # Should match LEGAL first (appears first in EXPENSE_CATEGORY_KEYWORDS)
        assert category == ExpenseCategory.LEGAL
