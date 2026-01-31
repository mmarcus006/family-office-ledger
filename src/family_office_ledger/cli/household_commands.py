"""Household management CLI commands for Family Office Ledger."""

import argparse
from datetime import datetime as dt
from pathlib import Path
from uuid import UUID

from family_office_ledger.cli._main import get_default_db_path
from family_office_ledger.domain.households import Household, HouseholdMember
from family_office_ledger.repositories.sqlite import (
    SQLiteAccountRepository,
    SQLiteDatabase,
    SQLiteEntityOwnershipRepository,
    SQLiteEntityRepository,
    SQLiteHouseholdRepository,
    SQLiteTransactionRepository,
)
from family_office_ledger.services.ownership_graph import OwnershipGraphService


def cmd_household_list(args: argparse.Namespace) -> int:
    """List all households."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        household_repo = SQLiteHouseholdRepository(db)

        households = list(household_repo.list_all())
        if not households:
            print("No households found.")
            return 0

        print("Households:")
        print("=" * 70)
        for h in households:
            status = "Active" if h.is_active else "Inactive"
            print(f"  {h.id}")
            print(f"    Name: {h.name}")
            print(f"    Status: {status}")
            if h.primary_contact_entity_id:
                print(f"    Primary Contact: {h.primary_contact_entity_id}")
            print()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_household_create(args: argparse.Namespace) -> int:
    """Create a new household."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        household_repo = SQLiteHouseholdRepository(db)

        primary_contact = UUID(args.primary_contact) if args.primary_contact else None
        household = Household(name=args.name, primary_contact_entity_id=primary_contact)
        household_repo.add(household)

        print(f"Created household: {household.id}")
        print(f"  Name: {household.name}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_household_add_member(args: argparse.Namespace) -> int:
    """Add a member to a household."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        household_repo = SQLiteHouseholdRepository(db)
        entity_repo = SQLiteEntityRepository(db)

        household = household_repo.get(UUID(args.household_id))
        if household is None:
            print(f"Error: Household {args.household_id} not found")
            return 1

        entity = entity_repo.get(UUID(args.entity_id))
        if entity is None:
            print(f"Error: Entity {args.entity_id} not found")
            return 1

        start_date = (
            dt.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None
        )

        member = HouseholdMember(
            household_id=UUID(args.household_id),
            entity_id=UUID(args.entity_id),
            role=args.role,
            display_name=args.display_name,
            effective_start_date=start_date,
        )
        household_repo.add_member(member)

        print(f"Added member {entity.name} to household {household.name}")
        print(f"  Member ID: {member.id}")
        print(f"  Role: {args.role or 'not set'}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_household_members(args: argparse.Namespace) -> int:
    """List members of a household."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        household_repo = SQLiteHouseholdRepository(db)
        entity_repo = SQLiteEntityRepository(db)

        household = household_repo.get(UUID(args.household_id))
        if household is None:
            print(f"Error: Household {args.household_id} not found")
            return 1

        as_of = dt.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else None
        members = list(household_repo.list_members(UUID(args.household_id), as_of))

        if not members:
            print(f"No members in household {household.name}")
            return 0

        print(f"Members of {household.name}:")
        print("=" * 70)
        for m in members:
            entity = entity_repo.get(m.entity_id)
            entity_name = entity.name if entity else "Unknown"
            print(f"  {m.id}")
            print(f"    Entity: {entity_name} ({m.entity_id})")
            print(f"    Role: {m.role or 'not set'}")
            if m.display_name:
                print(f"    Display Name: {m.display_name}")
            if m.effective_start_date:
                print(
                    f"    Effective: {m.effective_start_date} - {m.effective_end_date or 'present'}"
                )
            print()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_household_net_worth(args: argparse.Namespace) -> int:
    """Show look-through net worth for a household."""
    db_path = Path(args.database) if args.database else get_default_db_path()
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    try:
        db = SQLiteDatabase(str(db_path))
        household_repo = SQLiteHouseholdRepository(db)
        ownership_repo = SQLiteEntityOwnershipRepository(db)
        entity_repo = SQLiteEntityRepository(db)
        account_repo = SQLiteAccountRepository(db)
        transaction_repo = SQLiteTransactionRepository(db)

        household = household_repo.get(UUID(args.household_id))
        if household is None:
            print(f"Error: Household {args.household_id} not found")
            return 1

        as_of = (
            dt.strptime(args.as_of, "%Y-%m-%d").date()
            if args.as_of
            else dt.now().date()
        )

        service = OwnershipGraphService(
            ownership_repo, household_repo, entity_repo, account_repo, transaction_repo
        )
        result = service.household_look_through_net_worth(
            UUID(args.household_id), as_of
        )

        print(f"Look-Through Net Worth: {household.name}")
        print(f"As of: {as_of}")
        print("=" * 70)
        print(f"  Total Assets:      ${result['total_assets']:,.2f}")
        print(f"  Total Liabilities: ${result['total_liabilities']:,.2f}")
        print(f"  Net Worth:         ${result['net_worth']:,.2f}")

        if args.detail and result["detail"]:
            print()
            print("Detail:")
            print("-" * 70)
            for d in result["detail"]:
                print(f"  {d['entity_name']} / {d['account_name']}")
                print(
                    f"    Direct: ${d['direct_balance']:,.2f} x {float(d['effective_fraction']):.1%} = ${d['weighted_balance']:,.2f}"
                )

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


__all__ = [
    "cmd_household_list",
    "cmd_household_create",
    "cmd_household_add_member",
    "cmd_household_members",
    "cmd_household_net_worth",
]
