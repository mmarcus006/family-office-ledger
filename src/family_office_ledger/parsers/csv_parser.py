"""CSV file parser for bank/brokerage statements."""

import csv
import hashlib
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class CSVParser:
    """Parser for CSV bank/brokerage statement exports.

    Handles various CSV formats with configurable column mapping.
    Returns standardized transaction dictionaries.
    """

    # Default column names to look for (case-insensitive)
    DEFAULT_DATE_COLUMNS = ["date", "trans date", "transaction date", "posted date"]
    DEFAULT_DESC_COLUMNS = ["description", "trans description", "memo", "payee", "name"]
    DEFAULT_AMOUNT_COLUMNS = ["amount", "transaction amount"]
    DEFAULT_BALANCE_COLUMNS = ["balance", "running balance", "ending balance"]
    DEFAULT_DEBIT_COLUMNS = ["debit", "withdrawal", "amount debit"]
    DEFAULT_CREDIT_COLUMNS = ["credit", "deposit", "amount credit"]

    # Date formats to try
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ]

    def __init__(
        self,
        column_mapping: dict[str, str] | None = None,
        date_format: str | None = None,
    ) -> None:
        """Initialize CSV parser.

        Args:
            column_mapping: Optional mapping from standard names to actual column names.
                           Keys: 'date', 'description', 'amount', 'balance', 'debit', 'credit'
            date_format: Optional specific date format string.
        """
        self._column_mapping = column_mapping or {}
        self._date_format = date_format

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        """Parse a CSV file and return standardized transactions.

        Args:
            file_path: Path to the CSV file.

        Returns:
            List of transaction dictionaries with standardized fields:
            - import_id: Unique identifier for this import record
            - date: Transaction date
            - description: Transaction description
            - amount: Transaction amount (positive for credit, negative for debit)
            - balance: Optional running balance

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        transactions: list[dict[str, Any]] = []

        with open(path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            if reader.fieldnames is None:
                return []

            # Build column index based on mapping or auto-detection
            columns = self._detect_columns(reader.fieldnames)

            for row_num, row in enumerate(reader, start=1):
                txn = self._parse_row(row, columns, file_path, row_num)
                if txn is not None:
                    transactions.append(txn)

        return transactions

    def _detect_columns(self, fieldnames: Sequence[str]) -> dict[str, str | None]:
        """Detect which columns correspond to which fields.

        Args:
            fieldnames: List of column names from the CSV header.

        Returns:
            Mapping from standard field names to actual column names.
        """
        columns: dict[str, str | None] = {
            "date": None,
            "description": None,
            "amount": None,
            "balance": None,
            "debit": None,
            "credit": None,
        }

        # Normalize fieldnames for matching
        fieldname_lower = {name.lower().strip(): name for name in fieldnames}

        # Use explicit mapping if provided
        if self._column_mapping:
            for field, col_name in self._column_mapping.items():
                if col_name in fieldnames:
                    columns[field] = col_name
                elif col_name.lower().strip() in fieldname_lower:
                    columns[field] = fieldname_lower[col_name.lower().strip()]
            return columns

        # Auto-detect columns
        for field_lower, field_name in fieldname_lower.items():
            if field_lower in [c.lower() for c in self.DEFAULT_DATE_COLUMNS]:
                columns["date"] = field_name
            elif field_lower in [c.lower() for c in self.DEFAULT_DESC_COLUMNS]:
                columns["description"] = field_name
            elif field_lower in [c.lower() for c in self.DEFAULT_AMOUNT_COLUMNS]:
                columns["amount"] = field_name
            elif field_lower in [c.lower() for c in self.DEFAULT_BALANCE_COLUMNS]:
                columns["balance"] = field_name
            elif field_lower in [c.lower() for c in self.DEFAULT_DEBIT_COLUMNS]:
                columns["debit"] = field_name
            elif field_lower in [c.lower() for c in self.DEFAULT_CREDIT_COLUMNS]:
                columns["credit"] = field_name

        return columns

    def _parse_row(
        self,
        row: dict[str, str],
        columns: dict[str, str | None],
        file_path: str,
        row_num: int,
    ) -> dict[str, Any] | None:
        """Parse a single CSV row into a transaction dict.

        Args:
            row: CSV row as dictionary.
            columns: Column mapping.
            file_path: Source file path (for ID generation).
            row_num: Row number (for ID generation).

        Returns:
            Transaction dictionary or None if row is invalid/empty.
        """
        # Parse date
        date_col = columns.get("date")
        if not date_col or not row.get(date_col, "").strip():
            return None

        txn_date = self._parse_date(row[date_col].strip())
        if txn_date is None:
            return None

        # Parse description
        desc_col = columns.get("description")
        description = row.get(desc_col, "").strip() if desc_col else ""

        # Parse amount
        amount = self._parse_amount(row, columns)
        if amount is None:
            return None

        # Parse balance (optional)
        balance: Decimal | None = None
        balance_col = columns.get("balance")
        if balance_col and row.get(balance_col, "").strip():
            balance = self._parse_decimal(row[balance_col])

        # Generate unique import ID
        import_id = self._generate_import_id(file_path, row_num, txn_date, amount)

        result: dict[str, Any] = {
            "import_id": import_id,
            "date": txn_date,
            "description": description,
            "amount": amount,
        }

        if balance is not None:
            result["balance"] = balance

        return result

    def _parse_date(self, date_str: str) -> date | None:
        """Parse a date string using various formats.

        Args:
            date_str: Date string to parse.

        Returns:
            Parsed date or None if parsing fails.
        """
        if self._date_format:
            try:
                return datetime.strptime(date_str, self._date_format).date()
            except ValueError:
                return None

        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _parse_amount(
        self, row: dict[str, str], columns: dict[str, str | None]
    ) -> Decimal | None:
        """Parse the transaction amount from a row.

        Handles both single amount column and separate debit/credit columns.

        Args:
            row: CSV row.
            columns: Column mapping.

        Returns:
            Amount as Decimal (negative for debits) or None if invalid.
        """
        # Try single amount column first
        amount_col = columns.get("amount")
        if amount_col and row.get(amount_col, "").strip():
            return self._parse_decimal(row[amount_col])

        # Try debit/credit columns
        debit_col = columns.get("debit")
        credit_col = columns.get("credit")

        debit_val = Decimal("0")
        credit_val = Decimal("0")

        if debit_col and row.get(debit_col, "").strip():
            parsed = self._parse_decimal(row[debit_col])
            if parsed is not None:
                debit_val = abs(parsed)

        if credit_col and row.get(credit_col, "").strip():
            parsed = self._parse_decimal(row[credit_col])
            if parsed is not None:
                credit_val = abs(parsed)

        if debit_val or credit_val:
            return credit_val - debit_val

        return None

    def _parse_decimal(self, value: str) -> Decimal | None:
        """Parse a string to Decimal, handling currency symbols and formatting.

        Args:
            value: String value to parse.

        Returns:
            Decimal or None if parsing fails.
        """
        # Clean the value
        cleaned = value.strip()
        # Remove currency symbols and thousands separators
        cleaned = cleaned.replace("$", "").replace(",", "").replace(" ", "")
        # Handle parentheses for negative numbers
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]

        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _generate_import_id(
        self, file_path: str, row_num: int, txn_date: date, amount: Decimal
    ) -> str:
        """Generate a unique import ID for a transaction.

        Args:
            file_path: Source file path.
            row_num: Row number in the file.
            txn_date: Transaction date.
            amount: Transaction amount.

        Returns:
            Unique import ID string.
        """
        # Create deterministic but unique ID based on file, row, and transaction data
        hash_input = f"{file_path}:{row_num}:{txn_date.isoformat()}:{amount}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
