"""QSBS (Qualified Small Business Stock) CLI commands for Family Office Ledger."""

import argparse
from datetime import date as dt_date
from pathlib import Path
from uuid import UUID

from family_office_ledger.cli._main import get_default_db_path
from family_office_ledger.repositories.sqlite import (
    SQLiteDatabase,
    SQLitePositionRepository,
    SQLiteSecurityRepository,
    SQLiteTaxLotRepository,
)
from family_office_ledger.services.qsbs import QSBSService, SecurityNotFoundError


def cmd_qsbs_list(args: argparse.Namespace) -> int:
    """List QSBS-eligible securities."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        securities = service.list_qsbs_eligible_securities()

        if not securities:
            print("No QSBS-eligible securities found")
            return 0

        print(f"{'Symbol':<12} {'Name':<30} {'Qualification Date':<20} {'Issuer'}")
        print("-" * 85)
        for sec in securities:
            qual_date = (
                sec.qsbs_qualification_date.isoformat()
                if sec.qsbs_qualification_date
                else "N/A"
            )
            issuer = sec.issuer or "N/A"
            print(f"{sec.symbol:<12} {sec.name[:28]:<30} {qual_date:<20} {issuer}")

        print(f"\nTotal: {len(securities)} QSBS-eligible securities")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_mark(args: argparse.Namespace) -> int:
    """Mark a security as QSBS-eligible."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        security_id = UUID(args.security_id)
    except ValueError:
        print(f"Error: Invalid security ID: {args.security_id}")
        return 1

    try:
        qual_date = dt_date.fromisoformat(args.qualification_date)
    except ValueError:
        print(f"Error: Invalid date format: {args.qualification_date}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        security = service.mark_security_qsbs_eligible(security_id, qual_date)
        print(f"Marked {security.symbol} ({security.name}) as QSBS-eligible")
        print(f"  Qualification date: {qual_date}")
        return 0

    except SecurityNotFoundError:
        print("Error: Security not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_remove(args: argparse.Namespace) -> int:
    """Remove QSBS eligibility from a security."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        security_id = UUID(args.security_id)
    except ValueError:
        print(f"Error: Invalid security ID: {args.security_id}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        security = service.remove_qsbs_eligibility(security_id)
        print(f"Removed QSBS eligibility from {security.symbol} ({security.name})")
        return 0

    except SecurityNotFoundError:
        print("Error: Security not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_qsbs_summary(args: argparse.Namespace) -> int:
    """Show QSBS holdings summary."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        as_of_date = None
        if args.as_of:
            as_of_date = dt_date.fromisoformat(args.as_of)

        db = SQLiteDatabase(str(db_path))
        security_repo = SQLiteSecurityRepository(db)
        position_repo = SQLitePositionRepository(db)
        tax_lot_repo = SQLiteTaxLotRepository(db)
        service = QSBSService(security_repo, position_repo, tax_lot_repo)

        summary = service.get_qsbs_summary(as_of_date=as_of_date)

        print("QSBS Holdings Summary")
        print(f"  Total Holdings: {summary.total_qsbs_holdings}")
        print(f"  Qualified (5+ years): {summary.qualified_holdings}")
        print(f"  Pending: {summary.pending_holdings}")
        print(f"  Total Cost Basis: ${summary.total_cost_basis:,.2f}")
        print(f"  Potential Exclusion: ${summary.total_potential_exclusion:,.2f}")

        if summary.holdings:
            print(
                f"\n{'Symbol':<12} {'Held (days)':<12} {'Qualified':<10} {'Days Left':<12} {'Potential Exclusion'}"
            )
            print("-" * 70)
            for h in summary.holdings:
                status = "YES" if h.is_qualified else "NO"
                days_left = "-" if h.is_qualified else str(h.days_until_qualified)
                print(
                    f"{h.security_symbol:<12} {h.holding_period_days:<12} {status:<10} "
                    f"{days_left:<12} ${h.potential_exclusion:,.2f}"
                )

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


__all__ = [
    "cmd_qsbs_list",
    "cmd_qsbs_mark",
    "cmd_qsbs_remove",
    "cmd_qsbs_summary",
]
