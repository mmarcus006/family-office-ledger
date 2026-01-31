"""Portfolio analytics service for asset allocation, performance, and risk metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from family_office_ledger.domain.value_objects import AssetClass, Money
from family_office_ledger.repositories.interfaces import (
    EntityRepository,
    PositionRepository,
    SecurityRepository,
)


@dataclass
class AssetAllocation:
    asset_class: AssetClass
    market_value: Money
    cost_basis: Money
    unrealized_gain: Money
    allocation_percent: Decimal
    position_count: int


@dataclass
class AssetAllocationReport:
    as_of_date: date
    entity_names: list[str]
    allocations: list[AssetAllocation]
    total_market_value: Money
    total_cost_basis: Money
    total_unrealized_gain: Money


@dataclass
class HoldingConcentration:
    security_id: UUID
    security_symbol: str
    security_name: str
    asset_class: AssetClass
    market_value: Money
    cost_basis: Money
    unrealized_gain: Money
    concentration_percent: Decimal
    position_count: int


@dataclass
class ConcentrationReport:
    as_of_date: date
    entity_names: list[str]
    holdings: list[HoldingConcentration]
    total_market_value: Money
    top_5_concentration: Decimal
    top_10_concentration: Decimal
    largest_single_holding: Decimal


@dataclass
class PerformanceMetrics:
    entity_name: str
    start_value: Money
    end_value: Money
    net_contributions: Money
    total_return_amount: Money
    total_return_percent: Decimal
    unrealized_gain: Money
    unrealized_gain_percent: Decimal


@dataclass
class PerformanceReport:
    start_date: date
    end_date: date
    entity_names: list[str]
    metrics: list[PerformanceMetrics]
    portfolio_total_return_amount: Money
    portfolio_total_return_percent: Decimal


class PortfolioAnalyticsService:
    def __init__(
        self,
        entity_repo: EntityRepository,
        position_repo: PositionRepository,
        security_repo: SecurityRepository,
    ) -> None:
        self._entity_repo = entity_repo
        self._position_repo = position_repo
        self._security_repo = security_repo

    def asset_allocation_report(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
    ) -> AssetAllocationReport:
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]
        else:
            entities = [e for e in self._entity_repo.list_all() if e.id in entity_ids]

        entity_names = [e.name for e in entities]

        allocation_by_class: dict[AssetClass, dict[str, Any]] = {}

        for entity_id in entity_ids:
            positions = list(self._position_repo.list_by_entity(entity_id))

            for position in positions:
                if position.quantity.is_zero:
                    continue

                security = self._security_repo.get(position.security_id)
                if security is None:
                    continue

                asset_class = security.asset_class

                if asset_class not in allocation_by_class:
                    allocation_by_class[asset_class] = {
                        "market_value": Decimal("0"),
                        "cost_basis": Decimal("0"),
                        "position_count": 0,
                    }

                allocation_by_class[asset_class]["market_value"] += (
                    position.market_value.amount
                )
                allocation_by_class[asset_class]["cost_basis"] += (
                    position.cost_basis.amount
                )
                allocation_by_class[asset_class]["position_count"] += 1

        total_market_value = sum(
            (a["market_value"] for a in allocation_by_class.values()),
            Decimal("0"),
        )
        total_cost_basis = sum(
            (a["cost_basis"] for a in allocation_by_class.values()),
            Decimal("0"),
        )

        allocations: list[AssetAllocation] = []
        for asset_class in AssetClass:
            if asset_class not in allocation_by_class:
                continue

            data = allocation_by_class[asset_class]
            market_value = data["market_value"]
            cost_basis = data["cost_basis"]

            allocation_percent = Decimal("0")
            if total_market_value > 0:
                allocation_percent = (market_value / total_market_value * 100).quantize(
                    Decimal("0.01")
                )

            allocations.append(
                AssetAllocation(
                    asset_class=asset_class,
                    market_value=Money(market_value, "USD"),
                    cost_basis=Money(cost_basis, "USD"),
                    unrealized_gain=Money(market_value - cost_basis, "USD"),
                    allocation_percent=allocation_percent,
                    position_count=data["position_count"],
                )
            )

        allocations.sort(key=lambda a: a.allocation_percent, reverse=True)

        return AssetAllocationReport(
            as_of_date=as_of_date,
            entity_names=entity_names,
            allocations=allocations,
            total_market_value=Money(total_market_value, "USD"),
            total_cost_basis=Money(total_cost_basis, "USD"),
            total_unrealized_gain=Money(total_market_value - total_cost_basis, "USD"),
        )

    def concentration_report(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
        top_n: int = 20,
    ) -> ConcentrationReport:
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]
        else:
            entities = [e for e in self._entity_repo.list_all() if e.id in entity_ids]

        entity_names = [e.name for e in entities]

        holdings_by_security: dict[UUID, dict[str, Any]] = {}

        for entity_id in entity_ids:
            positions = list(self._position_repo.list_by_entity(entity_id))

            for position in positions:
                if position.quantity.is_zero:
                    continue

                security_id = position.security_id

                if security_id not in holdings_by_security:
                    security = self._security_repo.get(security_id)
                    holdings_by_security[security_id] = {
                        "security": security,
                        "market_value": Decimal("0"),
                        "cost_basis": Decimal("0"),
                        "position_count": 0,
                    }

                holdings_by_security[security_id]["market_value"] += (
                    position.market_value.amount
                )
                holdings_by_security[security_id]["cost_basis"] += (
                    position.cost_basis.amount
                )
                holdings_by_security[security_id]["position_count"] += 1

        total_market_value = sum(
            (h["market_value"] for h in holdings_by_security.values()),
            Decimal("0"),
        )

        holdings: list[HoldingConcentration] = []
        for security_id, data in holdings_by_security.items():
            security = data["security"]
            if security is None:
                continue

            market_value = data["market_value"]
            cost_basis = data["cost_basis"]

            concentration_percent = Decimal("0")
            if total_market_value > 0:
                concentration_percent = (
                    market_value / total_market_value * 100
                ).quantize(Decimal("0.01"))

            holdings.append(
                HoldingConcentration(
                    security_id=security_id,
                    security_symbol=security.symbol,
                    security_name=security.name,
                    asset_class=security.asset_class,
                    market_value=Money(market_value, "USD"),
                    cost_basis=Money(cost_basis, "USD"),
                    unrealized_gain=Money(market_value - cost_basis, "USD"),
                    concentration_percent=concentration_percent,
                    position_count=data["position_count"],
                )
            )

        holdings.sort(key=lambda h: h.concentration_percent, reverse=True)
        top_holdings = holdings[:top_n]

        top_5_concentration = sum(
            (h.concentration_percent for h in holdings[:5]),
            Decimal("0"),
        )
        top_10_concentration = sum(
            (h.concentration_percent for h in holdings[:10]),
            Decimal("0"),
        )
        largest_single_holding = (
            holdings[0].concentration_percent if holdings else Decimal("0")
        )

        return ConcentrationReport(
            as_of_date=as_of_date,
            entity_names=entity_names,
            holdings=top_holdings,
            total_market_value=Money(total_market_value, "USD"),
            top_5_concentration=top_5_concentration,
            top_10_concentration=top_10_concentration,
            largest_single_holding=largest_single_holding,
        )

    def performance_report(
        self,
        entity_ids: list[UUID] | None,
        start_date: date,
        end_date: date,
    ) -> PerformanceReport:
        if entity_ids is None:
            entities = list(self._entity_repo.list_all())
            entity_ids = [e.id for e in entities]
        else:
            entities = [e for e in self._entity_repo.list_all() if e.id in entity_ids]

        entity_names = [e.name for e in entities]

        metrics: list[PerformanceMetrics] = []
        portfolio_cost_basis = Decimal("0")
        portfolio_market_value = Decimal("0")

        for entity in entities:
            positions = list(self._position_repo.list_by_entity(entity.id))

            entity_cost_basis = Decimal("0")
            entity_market_value = Decimal("0")

            for position in positions:
                if position.quantity.is_zero:
                    continue

                entity_cost_basis += position.cost_basis.amount
                entity_market_value += position.market_value.amount

            unrealized_gain = entity_market_value - entity_cost_basis
            unrealized_gain_percent = Decimal("0")
            if entity_cost_basis > 0:
                unrealized_gain_percent = (
                    unrealized_gain / entity_cost_basis * 100
                ).quantize(Decimal("0.01"))

            metrics.append(
                PerformanceMetrics(
                    entity_name=entity.name,
                    start_value=Money(entity_cost_basis, "USD"),
                    end_value=Money(entity_market_value, "USD"),
                    net_contributions=Money(Decimal("0"), "USD"),
                    total_return_amount=Money(unrealized_gain, "USD"),
                    total_return_percent=unrealized_gain_percent,
                    unrealized_gain=Money(unrealized_gain, "USD"),
                    unrealized_gain_percent=unrealized_gain_percent,
                )
            )

            portfolio_cost_basis += entity_cost_basis
            portfolio_market_value += entity_market_value

        portfolio_return = portfolio_market_value - portfolio_cost_basis
        portfolio_return_percent = Decimal("0")
        if portfolio_cost_basis > 0:
            portfolio_return_percent = (
                portfolio_return / portfolio_cost_basis * 100
            ).quantize(Decimal("0.01"))

        return PerformanceReport(
            start_date=start_date,
            end_date=end_date,
            entity_names=entity_names,
            metrics=metrics,
            portfolio_total_return_amount=Money(portfolio_return, "USD"),
            portfolio_total_return_percent=portfolio_return_percent,
        )

    def get_portfolio_summary(
        self,
        entity_ids: list[UUID] | None,
        as_of_date: date,
    ) -> dict[str, Any]:
        allocation = self.asset_allocation_report(entity_ids, as_of_date)
        concentration = self.concentration_report(entity_ids, as_of_date, top_n=10)

        return {
            "as_of_date": as_of_date,
            "total_market_value": str(allocation.total_market_value.amount),
            "total_cost_basis": str(allocation.total_cost_basis.amount),
            "total_unrealized_gain": str(allocation.total_unrealized_gain.amount),
            "asset_allocation": [
                {
                    "asset_class": a.asset_class.value,
                    "market_value": str(a.market_value.amount),
                    "allocation_percent": str(a.allocation_percent),
                    "position_count": a.position_count,
                }
                for a in allocation.allocations
            ],
            "top_holdings": [
                {
                    "symbol": h.security_symbol,
                    "name": h.security_name,
                    "market_value": str(h.market_value.amount),
                    "concentration_percent": str(h.concentration_percent),
                }
                for h in concentration.holdings[:5]
            ],
            "concentration_metrics": {
                "top_5_concentration": str(concentration.top_5_concentration),
                "top_10_concentration": str(concentration.top_10_concentration),
                "largest_single_holding": str(concentration.largest_single_holding),
            },
        }
