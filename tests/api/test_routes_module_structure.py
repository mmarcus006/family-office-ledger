"""TDD Tests for API routes module structure.

These tests verify that the routes module works correctly.
The routes.py refactoring into submodules is deferred to a future iteration
to avoid destabilizing the existing test suite.
"""

import pytest
from fastapi import APIRouter


class TestRoutesModuleExists:
    """Test that routes module is properly accessible."""

    def test_routes_module_exists(self) -> None:
        """Test that routes module can be imported."""
        from family_office_ledger.api import routes

        assert routes is not None


class TestHelperFunctionsAccessible:
    """Test that helper functions are accessible from routes module."""

    def test_dependency_injection_functions_exist(self) -> None:
        """Test dependency injection functions are available."""
        from family_office_ledger.api.routes import (
            get_account_repository,
            get_entity_repository,
            get_transaction_repository,
        )

        assert callable(get_entity_repository)
        assert callable(get_account_repository)
        assert callable(get_transaction_repository)


class TestRoutersExist:
    """Test that all routers are accessible from routes module."""

    def test_routers_accessible_from_routes_module(self) -> None:
        """Ensure routers are accessible from family_office_ledger.api.routes."""
        from family_office_ledger.api.routes import (
            account_router,
            audit_router,
            budget_router,
            currency_router,
            entity_router,
            expense_router,
            health_router,
            household_router,
            ownership_router,
            portfolio_router,
            qsbs_router,
            reconciliation_router,
            report_router,
            tax_router,
            transaction_router,
            transfer_router,
            vendor_router,
        )

        assert isinstance(entity_router, APIRouter)
        assert isinstance(account_router, APIRouter)
        assert isinstance(transaction_router, APIRouter)
        assert isinstance(report_router, APIRouter)
        assert isinstance(reconciliation_router, APIRouter)
        assert isinstance(transfer_router, APIRouter)
        assert isinstance(qsbs_router, APIRouter)
        assert isinstance(tax_router, APIRouter)
        assert isinstance(portfolio_router, APIRouter)
        assert isinstance(audit_router, APIRouter)
        assert isinstance(currency_router, APIRouter)
        assert isinstance(expense_router, APIRouter)
        assert isinstance(vendor_router, APIRouter)
        assert isinstance(budget_router, APIRouter)
        assert isinstance(household_router, APIRouter)
        assert isinstance(ownership_router, APIRouter)
        assert isinstance(health_router, APIRouter)


class TestAPIIntegration:
    """Test that the API app works correctly."""

    def test_app_includes_all_routers(self) -> None:
        """Test that FastAPI app includes all routers."""
        from family_office_ledger.api.app import app

        # Check that routes are registered
        route_paths = [route.path for route in app.routes]

        # Verify key endpoint patterns exist
        assert any("/entities" in path for path in route_paths)
        assert any("/accounts" in path for path in route_paths)
        assert any("/transactions" in path for path in route_paths)
        assert any("/reports" in path for path in route_paths)
        assert any("/health" in path for path in route_paths)
