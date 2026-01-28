"""Tax document and line item domain models."""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from family_office_ledger.domain.value_objects import Money


@dataclass
class Document:
    """Tax document (K1, 1099, broker statement, etc.)."""

    entity_id: UUID
    doc_type: str
    tax_year: int
    issuer: str
    received_date: date | None = None
    file_path: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class TaxDocLine:
    """Individual line item from a tax document."""

    document_id: UUID
    line_item: str
    amount: Money
    mapped_account_id: UUID | None = None
    is_reconciled: bool = False
    id: UUID = field(default_factory=uuid4)

    @property
    def is_mapped(self) -> bool:
        """Return True if this line is mapped to an account."""
        return self.mapped_account_id is not None

    def mark_reconciled(self) -> None:
        """Mark this line item as reconciled."""
        self.is_reconciled = True
