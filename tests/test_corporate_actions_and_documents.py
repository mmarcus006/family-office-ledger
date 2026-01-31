from datetime import date
from decimal import Decimal
from uuid import uuid4

from family_office_ledger.domain.corporate_actions import CorporateAction, Price
from family_office_ledger.domain.documents import Document, TaxDocLine
from family_office_ledger.domain.value_objects import (
    CorporateActionType,
    Money,
)


class TestPrice:
    def test_price_creation(self):
        security_id = uuid4()
        price = Price(
            security_id=security_id,
            price_date=date(2024, 6, 15),
            price=Decimal("150.25"),
            source="Bloomberg",
        )

        assert price.security_id == security_id
        assert price.price_date == date(2024, 6, 15)
        assert price.price == Decimal("150.25")
        assert price.source == "Bloomberg"

    def test_price_has_unique_id(self):
        price = Price(
            security_id=uuid4(),
            price_date=date(2024, 6, 15),
            price=Decimal("100.00"),
        )

        assert price.id is not None

    def test_price_default_source_is_manual(self):
        price = Price(
            security_id=uuid4(),
            price_date=date(2024, 6, 15),
            price=Decimal("100.00"),
        )

        assert price.source == "manual"


class TestCorporateAction:
    def test_corporate_action_stock_split(self):
        security_id = uuid4()
        action = CorporateAction(
            security_id=security_id,
            action_type=CorporateActionType.SPLIT,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
        )

        assert action.security_id == security_id
        assert action.action_type == CorporateActionType.SPLIT
        assert action.ratio_numerator == Decimal("2")
        assert action.ratio_denominator == Decimal("1")

    def test_corporate_action_reverse_split(self):
        action = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.REVERSE_SPLIT,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("4"),
        )

        assert action.action_type == CorporateActionType.REVERSE_SPLIT
        assert action.ratio == Decimal("0.25")

    def test_corporate_action_spinoff_has_resulting_security(self):
        parent_id = uuid4()
        child_id = uuid4()
        action = CorporateAction(
            security_id=parent_id,
            action_type=CorporateActionType.SPINOFF,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("10"),
            resulting_security_id=child_id,
        )

        assert action.resulting_security_id == child_id
        assert action.action_type == CorporateActionType.SPINOFF

    def test_corporate_action_merger(self):
        old_security_id = uuid4()
        new_security_id = uuid4()
        action = CorporateAction(
            security_id=old_security_id,
            action_type=CorporateActionType.MERGER,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("3"),
            ratio_denominator=Decimal("2"),
            resulting_security_id=new_security_id,
        )

        assert action.action_type == CorporateActionType.MERGER
        assert action.ratio == Decimal("1.5")

    def test_corporate_action_ratio_property(self):
        action = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.SPLIT,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("3"),
            ratio_denominator=Decimal("1"),
        )

        assert action.ratio == Decimal("3")

    def test_corporate_action_with_metadata(self):
        action = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.DIVIDEND,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("1"),
            metadata={"dividend_per_share": "0.50", "ex_date": "2024-06-10"},
        )

        assert action.metadata["dividend_per_share"] == "0.50"

    def test_corporate_action_is_split(self):
        split = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.SPLIT,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
        )
        merger = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.MERGER,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("1"),
        )

        assert split.is_split is True
        assert merger.is_split is False

    def test_corporate_action_requires_resulting_security(self):
        spinoff = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.SPINOFF,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("1"),
            ratio_denominator=Decimal("10"),
        )

        assert spinoff.requires_resulting_security is True

        split = CorporateAction(
            security_id=uuid4(),
            action_type=CorporateActionType.SPLIT,
            effective_date=date(2024, 6, 15),
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
        )

        assert split.requires_resulting_security is False


class TestDocument:
    def test_document_creation_k1(self):
        entity_id = uuid4()
        doc = Document(
            entity_id=entity_id,
            doc_type="K1",
            tax_year=2024,
            issuer="ABC Partnership",
        )

        assert doc.entity_id == entity_id
        assert doc.doc_type == "K1"
        assert doc.tax_year == 2024
        assert doc.issuer == "ABC Partnership"

    def test_document_creation_1099div(self):
        doc = Document(
            entity_id=uuid4(),
            doc_type="1099DIV",
            tax_year=2024,
            issuer="Fidelity",
            received_date=date(2025, 1, 31),
        )

        assert doc.doc_type == "1099DIV"
        assert doc.received_date == date(2025, 1, 31)

    def test_document_with_file_path(self):
        doc = Document(
            entity_id=uuid4(),
            doc_type="1099B",
            tax_year=2024,
            issuer="Schwab",
            file_path="/documents/2024/schwab_1099b.pdf",
        )

        assert doc.file_path == "/documents/2024/schwab_1099b.pdf"

    def test_document_types(self):
        valid_types = ["K1", "1099DIV", "1099INT", "1099B", "BrokerStatement"]
        for doc_type in valid_types:
            doc = Document(
                entity_id=uuid4(),
                doc_type=doc_type,
                tax_year=2024,
                issuer="Test Issuer",
            )
            assert doc.doc_type == doc_type


class TestTaxDocLine:
    def test_tax_doc_line_creation(self):
        doc_id = uuid4()
        line = TaxDocLine(
            document_id=doc_id,
            line_item="Ordinary Dividends",
            amount=Money(Decimal("1500.00")),
        )

        assert line.document_id == doc_id
        assert line.line_item == "Ordinary Dividends"
        assert line.amount == Money(Decimal("1500.00"))

    def test_tax_doc_line_with_mapped_account(self):
        account_id = uuid4()
        line = TaxDocLine(
            document_id=uuid4(),
            line_item="Interest Income",
            amount=Money(Decimal("250.00")),
            mapped_account_id=account_id,
        )

        assert line.mapped_account_id == account_id
        assert line.is_mapped is True

    def test_tax_doc_line_unmapped(self):
        line = TaxDocLine(
            document_id=uuid4(),
            line_item="Capital Gains",
            amount=Money(Decimal("5000.00")),
        )

        assert line.mapped_account_id is None
        assert line.is_mapped is False

    def test_tax_doc_line_reconciliation_status(self):
        line = TaxDocLine(
            document_id=uuid4(),
            line_item="Qualified Dividends",
            amount=Money(Decimal("800.00")),
            is_reconciled=False,
        )

        assert line.is_reconciled is False

        line.mark_reconciled()

        assert line.is_reconciled is True

    def test_tax_doc_line_k1_items(self):
        k1_items = [
            ("Box 1 - Ordinary Income", Decimal("10000.00")),
            ("Box 2 - Net Rental Income", Decimal("5000.00")),
            ("Box 5 - Interest Income", Decimal("1200.00")),
            ("Box 6a - Ordinary Dividends", Decimal("800.00")),
            ("Box 9a - Net Long-Term Capital Gain", Decimal("15000.00")),
        ]

        doc_id = uuid4()
        lines = [
            TaxDocLine(
                document_id=doc_id,
                line_item=item,
                amount=Money(amount),
            )
            for item, amount in k1_items
        ]

        assert len(lines) == 5
        assert lines[0].line_item == "Box 1 - Ordinary Income"
        assert lines[4].amount == Money(Decimal("15000.00"))
