"""OFX/QFX file parser for bank/brokerage statements."""

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class OFXParser:
    """Parser for OFX/QFX bank and brokerage statement files.

    Handles the OFX SGML format (not strict XML) by converting to valid XML
    before parsing. Extracts STMTTRN records from bank, credit card, and
    investment statements.
    """

    def __init__(self) -> None:
        """Initialize OFX parser."""
        pass

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        """Parse an OFX/QFX file and return standardized transactions.

        Args:
            file_path: Path to the OFX/QFX file.

        Returns:
            List of transaction dictionaries with standardized fields:
            - import_id: FITID from the OFX file (unique transaction ID)
            - fitid: Same as import_id (OFX Financial Institution Transaction ID)
            - date: Transaction date
            - amount: Transaction amount
            - memo: Transaction memo/description
            - transaction_type: OFX transaction type (CREDIT, DEBIT, CHECK, etc.)
            - check_number: Check number if applicable

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"OFX file not found: {file_path}")

        content = path.read_text(encoding="utf-8", errors="replace")

        # Convert OFX SGML to valid XML
        xml_content = self._convert_to_xml(content)

        # Parse the XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            # Try wrapping in root element if parsing fails
            try:
                root = ET.fromstring(f"<ROOT>{xml_content}</ROOT>")
            except ET.ParseError:
                return []

        transactions: list[dict[str, Any]] = []

        # Find all STMTTRN elements (bank transactions)
        for stmttrn in root.iter("STMTTRN"):
            txn = self._parse_stmttrn(stmttrn)
            if txn is not None:
                transactions.append(txn)

        return transactions

    def _convert_to_xml(self, content: str) -> str:
        """Convert OFX SGML content to valid XML.

        OFX files are not valid XML because:
        1. Tags may not have closing tags
        2. Header section uses a different format

        Args:
            content: Raw OFX file content.

        Returns:
            Content converted to valid XML format.
        """
        # Remove OFX header (everything before <OFX>)
        ofx_start = content.find("<OFX>")
        if ofx_start == -1:
            ofx_start = content.find("<ofx>")
        if ofx_start == -1:
            # Try to find any XML-like content
            ofx_start = content.find("<")

        if ofx_start > 0:
            content = content[ofx_start:]

        # Remove newlines from within tag content for easier processing
        # This preserves newlines but helps with tag parsing
        lines = content.split("\n")
        result_lines = []

        for line in lines:
            line = line.strip()
            if line:
                result_lines.append(line)

        content = "\n".join(result_lines)

        # Close unclosed tags
        # OFX uses tags like <TAG>value without closing </TAG>
        # We need to add closing tags for leaf elements

        # Pattern: <TAG>value (where value doesn't start with <)
        # Should become: <TAG>value</TAG>
        pattern = r"<([A-Z0-9_]+)>([^<\n]+)"

        def add_closing_tag(match: re.Match[str]) -> str:
            tag = match.group(1)
            value = match.group(2).strip()
            if value:
                return f"<{tag}>{value}</{tag}>"
            return match.group(0)

        content = re.sub(pattern, add_closing_tag, content, flags=re.IGNORECASE)

        return content

    def _parse_stmttrn(self, element: ET.Element) -> dict[str, Any] | None:
        """Parse a STMTTRN element into a transaction dictionary.

        Args:
            element: STMTTRN XML element.

        Returns:
            Transaction dictionary or None if required fields are missing.
        """
        # Required fields
        fitid = self._get_element_text(element, "FITID")
        dtposted = self._get_element_text(element, "DTPOSTED")
        trnamt = self._get_element_text(element, "TRNAMT")

        if fitid is None or dtposted is None or trnamt is None:
            return None

        # Parse date
        txn_date = self._parse_ofx_date(dtposted)
        if txn_date is None:
            return None

        # Parse amount
        try:
            amount = Decimal(trnamt)
        except (InvalidOperation, ValueError):
            return None

        # Optional fields
        trntype = self._get_element_text(element, "TRNTYPE") or ""
        memo = self._get_element_text(element, "MEMO")
        name = self._get_element_text(element, "NAME")
        checknum = self._get_element_text(element, "CHECKNUM")

        # Use NAME as memo if MEMO is not present
        if not memo and name:
            memo = name
        elif not memo:
            memo = ""

        result: dict[str, Any] = {
            "import_id": fitid,
            "fitid": fitid,
            "date": txn_date,
            "amount": amount,
            "memo": memo,
            "transaction_type": trntype,
        }

        if checknum:
            result["check_number"] = checknum

        return result

    def _get_element_text(self, parent: ET.Element, tag: str) -> str | None:
        """Get text content of a child element.

        Args:
            parent: Parent XML element.
            tag: Tag name to find.

        Returns:
            Text content or None if not found.
        """
        # Try exact match
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()

        # Try case-insensitive search
        for child in parent:
            if child.tag.upper() == tag.upper() and child.text:
                return child.text.strip()

        return None

    def _parse_ofx_date(self, date_str: str | None) -> date | None:
        """Parse an OFX date string.

        OFX dates are in format: YYYYMMDDHHMMSS[.XXX][gmt offset:tz name]
        or shorter versions like YYYYMMDD.

        Args:
            date_str: OFX date string.

        Returns:
            Parsed date or None if invalid.
        """
        if not date_str:
            return None

        # Take only the first 8 characters for the date portion
        date_part = date_str[:8]

        try:
            return datetime.strptime(date_part, "%Y%m%d").date()
        except ValueError:
            return None
