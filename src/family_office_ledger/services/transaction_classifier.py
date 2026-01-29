"""Transaction classifier using a rules-based engine.

Classifies ParsedTransaction objects into TransactionType categories
based on keyword matching, amount direction, and security lookups.
"""

from typing import Protocol

from family_office_ledger.domain.value_objects import TransactionType
from family_office_ledger.parsers.bank_parsers import ParsedTransaction


class SecurityLookup(Protocol):
    """Protocol for security QSBS eligibility lookup."""

    def is_qsbs_eligible(self, symbol: str | None, cusip: str | None) -> bool | None:
        """Check if security is QSBS eligible.

        Args:
            symbol: Security ticker symbol
            cusip: CUSIP identifier

        Returns:
            True if QSBS eligible, False if not eligible, None if security not found
        """
        ...


class TransactionClassifier:
    """Classifies transactions using ordered rules.

    Rules are evaluated in priority order. The first matching rule
    determines the transaction type. UNCLASSIFIED is the fallback.

    Attributes:
        security_lookup: Protocol for checking QSBS eligibility
    """

    # Keywords for each transaction type (case-insensitive matching)
    INTEREST_KEYWORDS = ["INTEREST", "MARGIN INT", "INT PAYMENT"]
    EXPENSE_KEYWORDS = ["LEGAL FEE", "PROFESSIONAL", "ACCOUNTING", "ADVISORY"]
    LOAN_KEYWORDS = ["LOAN TO", "NOTE RECEIVABLE", "ADVANCE TO"]
    LOAN_REPAYMENT_KEYWORDS = ["LOAN REPAYMENT", "NOTE REPAYMENT"]
    BROKER_FEE_KEYWORDS = ["BROKER FEE", "TRANSACTION FEE", "SECONDARY MARKET"]
    RETURN_KEYWORDS = ["REFUND", "RETURN OF FUNDS", "CANCELLED"]
    OZ_FUND_KEYWORDS = ["OZ FUND", "OPPORTUNITY ZONE"]
    FUND_INDICATORS = ["LP", "FUND", "CAPITAL", "PARTNERS"]
    CONTRIBUTION_KEYWORDS = ["CAPITAL CONTRIBUTION", "MEMBER CONTRIBUTION"]
    PUBLIC_MARKET_KEYWORDS = ["TREASURY", "T-BILL", "CRYPTO", "HYPERLIQUID", "BITCOIN"]
    LIQUIDATION_KEYWORDS = ["LIQUIDATION", "ESCROW RELEASE", "WIND DOWN"]
    SALE_ACTIVITY_TYPES = ["SOLD", "SALE", "REDEMPTION"]
    PURCHASE_ACTIVITY_TYPES = ["BOUGHT", "PURCHASE"]
    TRANSFER_KEYWORDS = ["WIRE TRANSFER", "ACH TRANSFER", "INTERNAL TRANSFER"]

    def __init__(self, security_lookup: SecurityLookup | None = None) -> None:
        """Initialize the classifier.

        Args:
            security_lookup: Optional lookup for QSBS eligibility checks.
                If None, all purchases/sales are classified as NON_QSBS.
        """
        self._security_lookup = security_lookup

    def classify(self, txn: ParsedTransaction) -> TransactionType:
        """Classify a transaction into a TransactionType.

        Rules are evaluated in priority order. The first matching rule wins.

        Args:
            txn: The parsed transaction to classify

        Returns:
            The determined TransactionType
        """
        # Build search text from description and other_party
        search_text = self._build_search_text(txn)

        # Rule 1: INTEREST
        if self._is_interest(txn, search_text):
            return TransactionType.INTEREST

        # Rule 2: EXPENSE
        if self._is_expense(txn, search_text):
            return TransactionType.EXPENSE

        # Rule 3: TRUST_TRANSFER
        if self._is_trust_transfer(txn):
            return TransactionType.TRUST_TRANSFER

        # Rule 4: LOAN
        if self._is_loan(txn, search_text):
            return TransactionType.LOAN

        # Rule 5: LOAN_REPAYMENT
        if self._is_loan_repayment(txn, search_text):
            return TransactionType.LOAN_REPAYMENT

        # Rule 6: BROKER_FEES
        if self._is_broker_fees(txn, search_text):
            return TransactionType.BROKER_FEES

        # Rule 7: RETURN_OF_FUNDS
        if self._is_return_of_funds(txn, search_text):
            return TransactionType.RETURN_OF_FUNDS

        # Rule 8: PURCHASE_OZ_FUND
        if self._is_oz_fund_purchase(txn, search_text):
            return TransactionType.PURCHASE_OZ_FUND

        # Rule 9: CONTRIBUTION_DISTRIBUTION
        if self._is_contribution_distribution(txn):
            return TransactionType.CONTRIBUTION_DISTRIBUTION

        # Rule 10: CONTRIBUTION_TO_ENTITY
        if self._is_contribution_to_entity(txn, search_text):
            return TransactionType.CONTRIBUTION_TO_ENTITY

        # Rule 11: PUBLIC_MARKET
        if self._is_public_market(search_text):
            return TransactionType.PUBLIC_MARKET

        # Rule 12: LIQUIDATION
        if self._is_liquidation(search_text):
            return TransactionType.LIQUIDATION

        # Rule 13: SALE (QSBS or NON_QSBS)
        sale_type = self._classify_sale(txn)
        if sale_type:
            return sale_type

        # Rule 14: PURCHASE (QSBS or NON_QSBS)
        purchase_type = self._classify_purchase(txn)
        if purchase_type:
            return purchase_type

        # Rule 15: TRANSFER
        if self._is_transfer(search_text):
            return TransactionType.TRANSFER

        # Rule 16: UNCLASSIFIED (default fallback)
        return TransactionType.UNCLASSIFIED

    def _build_search_text(self, txn: ParsedTransaction) -> str:
        """Build combined search text from description and other_party."""
        parts = [txn.description]
        if txn.other_party:
            parts.append(txn.other_party)
        return " ".join(parts).upper()

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        """Check if text contains any of the keywords (case-insensitive)."""
        text_upper = text.upper()
        return any(kw.upper() in text_upper for kw in keywords)

    def _has_security_identifier(self, txn: ParsedTransaction) -> bool:
        """Check if transaction has CUSIP or symbol."""
        return bool(txn.cusip or txn.symbol)

    def _is_interest(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is INTEREST."""
        return (
            self._contains_any(search_text, self.INTEREST_KEYWORDS)
            and txn.amount > 0
            and not self._has_security_identifier(txn)
        )

    def _is_expense(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is EXPENSE."""
        return self._contains_any(search_text, self.EXPENSE_KEYWORDS) and txn.amount < 0

    def _is_trust_transfer(self, txn: ParsedTransaction) -> bool:
        """Check if transaction is TRUST_TRANSFER."""
        if txn.other_party:
            return "TRUST" in txn.other_party.upper()
        return False

    def _is_loan(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is LOAN."""
        return self._contains_any(search_text, self.LOAN_KEYWORDS) and txn.amount < 0

    def _is_loan_repayment(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is LOAN_REPAYMENT."""
        return (
            self._contains_any(search_text, self.LOAN_REPAYMENT_KEYWORDS)
            and txn.amount > 0
        )

    def _is_broker_fees(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is BROKER_FEES."""
        return (
            self._contains_any(search_text, self.BROKER_FEE_KEYWORDS) and txn.amount < 0
        )

    def _is_return_of_funds(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is RETURN_OF_FUNDS."""
        return self._contains_any(search_text, self.RETURN_KEYWORDS) and txn.amount > 0

    def _is_oz_fund_purchase(self, txn: ParsedTransaction, search_text: str) -> bool:
        """Check if transaction is PURCHASE_OZ_FUND."""
        return self._contains_any(search_text, self.OZ_FUND_KEYWORDS) and txn.amount < 0

    def _is_contribution_distribution(self, txn: ParsedTransaction) -> bool:
        """Check if transaction is CONTRIBUTION_DISTRIBUTION."""
        if txn.other_party:
            return self._contains_any(txn.other_party, self.FUND_INDICATORS)
        return False

    def _is_contribution_to_entity(
        self, txn: ParsedTransaction, search_text: str
    ) -> bool:
        """Check if transaction is CONTRIBUTION_TO_ENTITY."""
        return (
            self._contains_any(search_text, self.CONTRIBUTION_KEYWORDS)
            and txn.amount > 0
        )

    def _is_public_market(self, search_text: str) -> bool:
        """Check if transaction is PUBLIC_MARKET."""
        return self._contains_any(search_text, self.PUBLIC_MARKET_KEYWORDS)

    def _is_liquidation(self, search_text: str) -> bool:
        """Check if transaction is LIQUIDATION."""
        return self._contains_any(search_text, self.LIQUIDATION_KEYWORDS)

    def _classify_sale(self, txn: ParsedTransaction) -> TransactionType | None:
        """Classify sale transactions (QSBS or NON_QSBS)."""
        is_sale_activity = txn.activity_type and txn.activity_type.upper() in [
            at.upper() for at in self.SALE_ACTIVITY_TYPES
        ]
        if is_sale_activity and self._has_security_identifier(txn):
            return self._determine_qsbs_sale(txn)
        return None

    def _classify_purchase(self, txn: ParsedTransaction) -> TransactionType | None:
        """Classify purchase transactions (QSBS or NON_QSBS)."""
        is_purchase_activity = txn.activity_type and txn.activity_type.upper() in [
            at.upper() for at in self.PURCHASE_ACTIVITY_TYPES
        ]
        if is_purchase_activity and self._has_security_identifier(txn):
            return self._determine_qsbs_purchase(txn)

        if txn.amount < 0 and self._has_security_identifier(txn):
            return self._determine_qsbs_purchase(txn)

        return None

    def _determine_qsbs_sale(self, txn: ParsedTransaction) -> TransactionType:
        """Determine if sale is QSBS or NON_QSBS."""
        if self._security_lookup:
            is_qsbs = self._security_lookup.is_qsbs_eligible(txn.symbol, txn.cusip)
            if is_qsbs is True:
                return TransactionType.SALE_QSBS
        return TransactionType.SALE_NON_QSBS

    def _determine_qsbs_purchase(self, txn: ParsedTransaction) -> TransactionType:
        """Determine if purchase is QSBS or NON_QSBS."""
        if self._security_lookup:
            is_qsbs = self._security_lookup.is_qsbs_eligible(txn.symbol, txn.cusip)
            if is_qsbs is True:
                return TransactionType.PURCHASE_QSBS
        return TransactionType.PURCHASE_NON_QSBS

    def _is_transfer(self, search_text: str) -> bool:
        """Check if transaction is TRANSFER."""
        return self._contains_any(search_text, self.TRANSFER_KEYWORDS)
