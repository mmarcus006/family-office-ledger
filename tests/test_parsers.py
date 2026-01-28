"""Tests for file parsers (CSV, OFX/QFX)."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from family_office_ledger.parsers.csv_parser import CSVParser
from family_office_ledger.parsers.ofx_parser import OFXParser


# ===== CSVParser Tests =====


class TestCSVParser:
    """Tests for CSV file parser."""

    def test_parse_standard_bank_csv(self, tmp_path: Path) -> None:
        """Parse standard bank CSV with Date, Description, Amount columns."""
        csv_content = """Date,Description,Amount,Balance
2024-01-15,DEPOSIT ATM,1000.00,5000.00
2024-01-16,GROCERY STORE,-45.67,4954.33
2024-01-17,TRANSFER OUT,-500.00,4454.33
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert len(result) == 3
        assert result[0]["date"] == date(2024, 1, 15)
        assert result[0]["description"] == "DEPOSIT ATM"
        assert result[0]["amount"] == Decimal("1000.00")
        assert result[0]["balance"] == Decimal("5000.00")

        assert result[1]["amount"] == Decimal("-45.67")
        assert result[2]["amount"] == Decimal("-500.00")

    def test_parse_csv_with_different_date_formats(self, tmp_path: Path) -> None:
        """Parse CSV with MM/DD/YYYY date format."""
        csv_content = """Date,Description,Amount
01/15/2024,DEPOSIT,100.00
12/31/2023,WITHDRAWAL,-50.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert result[0]["date"] == date(2024, 1, 15)
        assert result[1]["date"] == date(2023, 12, 31)

    def test_parse_csv_with_column_mapping(self, tmp_path: Path) -> None:
        """Parse CSV with custom column names using mapping."""
        csv_content = """Trans Date,Trans Description,Debit,Credit
2024-01-15,DEPOSIT,,500.00
2024-01-16,PURCHASE,100.00,
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        column_mapping = {
            "date": "Trans Date",
            "description": "Trans Description",
            "debit": "Debit",
            "credit": "Credit",
        }
        parser = CSVParser(column_mapping=column_mapping)
        result = parser.parse(str(csv_file))

        assert len(result) == 2
        # Credit is positive, debit is negative
        assert result[0]["amount"] == Decimal("500.00")
        assert result[1]["amount"] == Decimal("-100.00")

    def test_parse_csv_with_quoted_fields(self, tmp_path: Path) -> None:
        """Parse CSV with quoted fields containing commas."""
        csv_content = """Date,Description,Amount
2024-01-15,"PAYMENT TO JONES, LLC",-1500.00
2024-01-16,"DEPOSIT, WIRE TRANSFER",2500.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert result[0]["description"] == "PAYMENT TO JONES, LLC"
        assert result[1]["description"] == "DEPOSIT, WIRE TRANSFER"

    def test_parse_csv_generates_unique_ids(self, tmp_path: Path) -> None:
        """Each parsed transaction should have a unique import_id."""
        csv_content = """Date,Description,Amount
2024-01-15,DEPOSIT,100.00
2024-01-16,DEPOSIT,100.00
2024-01-17,DEPOSIT,100.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        ids = [r["import_id"] for r in result]
        assert len(ids) == len(set(ids)), "All import IDs should be unique"

    def test_parse_csv_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Empty CSV (header only) should return empty list."""
        csv_content = """Date,Description,Amount
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert result == []

    def test_parse_csv_handles_missing_optional_balance(self, tmp_path: Path) -> None:
        """Parse CSV without balance column."""
        csv_content = """Date,Description,Amount
2024-01-15,DEPOSIT,100.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert "balance" not in result[0] or result[0]["balance"] is None

    def test_parse_csv_file_not_found_raises(self) -> None:
        """Parsing non-existent file should raise FileNotFoundError."""
        parser = CSVParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/file.csv")

    def test_parse_csv_with_explicit_date_format(self, tmp_path: Path) -> None:
        """Parse CSV with explicit date format that would fail auto-detection."""
        csv_content = """Date,Description,Amount
15-Jan-24,DEPOSIT,100.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        # This format isn't in default list, so explicit format needed
        parser = CSVParser(date_format="%d-%b-%y")
        result = parser.parse(str(csv_file))

        assert len(result) == 1
        assert result[0]["date"] == date(2024, 1, 15)

    def test_parse_csv_invalid_date_format_returns_none(self, tmp_path: Path) -> None:
        """Rows with invalid dates are skipped."""
        csv_content = """Date,Description,Amount
not-a-date,DEPOSIT,100.00
2024-01-15,WITHDRAWAL,-50.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        # First row skipped due to invalid date
        assert len(result) == 1
        assert result[0]["description"] == "WITHDRAWAL"

    def test_parse_csv_with_negative_parentheses(self, tmp_path: Path) -> None:
        """Parse amounts in parentheses as negative."""
        csv_content = """Date,Description,Amount
2024-01-15,WITHDRAWAL,(500.00)
2024-01-16,DEPOSIT,250.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert result[0]["amount"] == Decimal("-500.00")
        assert result[1]["amount"] == Decimal("250.00")

    def test_parse_csv_with_currency_symbols(self, tmp_path: Path) -> None:
        """Parse amounts with currency symbols and commas."""
        csv_content = """Date,Description,Amount
2024-01-15,BIG DEPOSIT,"$1,500.00"
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert result[0]["amount"] == Decimal("1500.00")

    def test_parse_csv_empty_amount_skips_row(self, tmp_path: Path) -> None:
        """Rows with empty amount are skipped."""
        csv_content = """Date,Description,Amount
2024-01-15,NO AMOUNT,
2024-01-16,HAS AMOUNT,50.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert len(result) == 1
        assert result[0]["description"] == "HAS AMOUNT"

    def test_parse_csv_invalid_amount_skips_row(self, tmp_path: Path) -> None:
        """Rows with invalid amount format are skipped."""
        csv_content = """Date,Description,Amount
2024-01-15,BAD AMOUNT,abc
2024-01-16,GOOD AMOUNT,50.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert len(result) == 1
        assert result[0]["description"] == "GOOD AMOUNT"

    def test_parse_csv_empty_date_skips_row(self, tmp_path: Path) -> None:
        """Rows with empty date are skipped."""
        csv_content = """Date,Description,Amount
,NO DATE,100.00
2024-01-16,HAS DATE,50.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        parser = CSVParser()
        result = parser.parse(str(csv_file))

        assert len(result) == 1
        assert result[0]["description"] == "HAS DATE"

    def test_parse_csv_case_insensitive_mapping(self, tmp_path: Path) -> None:
        """Column mapping works case-insensitively."""
        csv_content = """TRANS DATE,DESCRIPTION,AMOUNT
2024-01-15,DEPOSIT,100.00
"""
        csv_file = tmp_path / "bank.csv"
        csv_file.write_text(csv_content)

        column_mapping = {
            "date": "trans date",  # lowercase
            "description": "Description",
            "amount": "amount",
        }
        parser = CSVParser(column_mapping=column_mapping)
        result = parser.parse(str(csv_file))

        assert len(result) == 1
        assert result[0]["date"] == date(2024, 1, 15)


# ===== OFXParser Tests =====


class TestOFXParser:
    """Tests for OFX/QFX file parser."""

    def test_parse_ofx_basic_statement(self, tmp_path: Path) -> None:
        """Parse basic OFX statement with STMTTRN records."""
        ofx_content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20240120120000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1001
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>USD
<BANKACCTFROM>
<BANKID>123456789
<ACCTID>987654321
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20240101120000
<DTEND>20240131120000
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240115120000
<TRNAMT>1000.00
<FITID>20240115001
<MEMO>DIRECT DEPOSIT PAYROLL
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240116120000
<TRNAMT>-45.67
<FITID>20240116001
<MEMO>GROCERY STORE
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>5000.00
<DTASOF>20240131120000
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "statement.ofx"
        ofx_file.write_text(ofx_content)

        parser = OFXParser()
        result = parser.parse(str(ofx_file))

        assert len(result) == 2

        assert result[0]["date"] == date(2024, 1, 15)
        assert result[0]["amount"] == Decimal("1000.00")
        assert result[0]["memo"] == "DIRECT DEPOSIT PAYROLL"
        assert result[0]["fitid"] == "20240115001"
        assert result[0]["import_id"] == "20240115001"

        assert result[1]["date"] == date(2024, 1, 16)
        assert result[1]["amount"] == Decimal("-45.67")
        assert result[1]["memo"] == "GROCERY STORE"

    def test_parse_qfx_file(self, tmp_path: Path) -> None:
        """Parse QFX file (Quicken format, same as OFX)."""
        qfx_content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>USD
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CHECK
<DTPOSTED>20240120
<TRNAMT>-250.00
<FITID>CHK1234
<CHECKNUM>1234
<MEMO>CHECK 1234
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        qfx_file = tmp_path / "statement.qfx"
        qfx_file.write_text(qfx_content)

        parser = OFXParser()
        result = parser.parse(str(qfx_file))

        assert len(result) == 1
        assert result[0]["date"] == date(2024, 1, 20)
        assert result[0]["amount"] == Decimal("-250.00")
        assert result[0]["check_number"] == "1234"

    def test_parse_ofx_with_name_field(self, tmp_path: Path) -> None:
        """Parse OFX where NAME field is used instead of MEMO."""
        ofx_content = """<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240115
<TRNAMT>-100.00
<FITID>TX001
<NAME>AMAZON PURCHASE
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "statement.ofx"
        ofx_file.write_text(ofx_content)

        parser = OFXParser()
        result = parser.parse(str(ofx_file))

        # Should use NAME as description when MEMO is absent
        assert result[0]["memo"] == "AMAZON PURCHASE"

    def test_parse_ofx_credit_card_statement(self, tmp_path: Path) -> None:
        """Parse credit card OFX statement (CCSTMTRS)."""
        ofx_content = """<OFX>
<CREDITCARDMSGSRSV1>
<CCSTMTTRNRS>
<CCSTMTRS>
<CURDEF>USD
<CCACCTFROM>
<ACCTID>1234567890123456
</CCACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240110
<TRNAMT>-75.50
<FITID>CC20240110001
<MEMO>RESTAURANT
</STMTTRN>
</BANKTRANLIST>
</CCSTMTRS>
</CCSTMTTRNRS>
</CREDITCARDMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "cc_statement.ofx"
        ofx_file.write_text(ofx_content)

        parser = OFXParser()
        result = parser.parse(str(ofx_file))

        assert len(result) == 1
        assert result[0]["amount"] == Decimal("-75.50")

    def test_parse_ofx_empty_transaction_list(self, tmp_path: Path) -> None:
        """Parse OFX with no transactions."""
        ofx_content = """<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "empty.ofx"
        ofx_file.write_text(ofx_content)

        parser = OFXParser()
        result = parser.parse(str(ofx_file))

        assert result == []

    def test_parse_ofx_file_not_found_raises(self) -> None:
        """Parsing non-existent OFX file should raise FileNotFoundError."""
        parser = OFXParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path/file.ofx")

    def test_parse_ofx_investment_statement(self, tmp_path: Path) -> None:
        """Parse investment OFX statement (INVSTMTRS)."""
        ofx_content = """<OFX>
<INVSTMTMSGSRSV1>
<INVSTMTTRNRS>
<INVSTMTRS>
<INVTRANLIST>
<DTSTART>20240101
<DTEND>20240131
<INVBANKTRANS>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240115
<TRNAMT>5000.00
<FITID>INV20240115001
<MEMO>WIRE TRANSFER IN
</STMTTRN>
</INVBANKTRANS>
</INVTRANLIST>
</INVSTMTRS>
</INVSTMTTRNRS>
</INVSTMTMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "investment.ofx"
        ofx_file.write_text(ofx_content)

        parser = OFXParser()
        result = parser.parse(str(ofx_file))

        assert len(result) == 1
        assert result[0]["amount"] == Decimal("5000.00")
        assert result[0]["memo"] == "WIRE TRANSFER IN"

    def test_parse_ofx_returns_transaction_type(self, tmp_path: Path) -> None:
        """Parsed transactions should include transaction type."""
        ofx_content = """<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CHECK
<DTPOSTED>20240115
<TRNAMT>-100.00
<FITID>TX001
<MEMO>Test
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        ofx_file = tmp_path / "statement.ofx"
        ofx_file.write_text(ofx_content)

        parser = OFXParser()
        result = parser.parse(str(ofx_file))

        assert result[0]["transaction_type"] == "CHECK"
