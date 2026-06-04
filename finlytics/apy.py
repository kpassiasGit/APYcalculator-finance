"""APY / compound-growth projections.

This is the modernised, testable core of the original calculator. It supports
arbitrary compounding frequencies, recurring contributions and a multi-currency
comparison that mirrors (and fixes) the behaviour of the legacy script.
"""

from __future__ import annotations

from dataclasses import dataclass

from finlytics.config import DEFAULT_APY
from finlytics.data import get_fx_rate

__all__ = ["APYResult", "project_apy", "compare_currencies"]


@dataclass(frozen=True)
class APYResult:
    """Outcome of a single compound-growth projection."""

    principal: float
    apy_percent: float
    years: float
    final_value: float
    contributions: float

    @property
    def profit(self) -> float:
        """Total gain over principal *and* contributions."""
        return self.final_value - self.principal - self.contributions

    @property
    def total_invested(self) -> float:
        return self.principal + self.contributions


def project_apy(
    principal: float,
    apy_percent: float,
    years: float = 1.0,
    *,
    compounding_per_year: int = 365,
    monthly_contribution: float = 0.0,
) -> APYResult:
    """Project the future value of ``principal`` under a fixed APY.

    Parameters
    ----------
    principal:
        Starting capital.
    apy_percent:
        Annual percentage yield, expressed in percent (e.g. ``5.05``).
    years:
        Investment horizon in years (fractional allowed).
    compounding_per_year:
        Number of compounding periods per year (365 = daily, 12 = monthly).
    monthly_contribution:
        Optional recurring deposit added at the start of each month.

    Notes
    -----
    Uses the standard compound-interest formula applied per period, with
    contributions injected on month boundaries.
    """
    if principal < 0 or apy_percent < -100 or years < 0:
        raise ValueError("Invalid projection inputs.")

    rate = apy_percent / 100.0
    periodic_rate = rate / compounding_per_year
    total_periods = int(round(compounding_per_year * years))
    periods_per_month = max(1, compounding_per_year // 12)

    balance = float(principal)
    contributed = 0.0
    for period in range(total_periods):
        if monthly_contribution and period > 0 and period % periods_per_month == 0:
            balance += monthly_contribution
            contributed += monthly_contribution
        balance += balance * periodic_rate

    return APYResult(
        principal=float(principal),
        apy_percent=apy_percent,
        years=years,
        final_value=balance,
        contributions=contributed,
    )


def compare_currencies(
    principal: float,
    base_currency: str,
    *,
    years: float = 1.0,
    apy_table: dict[str, float] | None = None,
    monthly_contribution: float = 0.0,
) -> dict[str, APYResult]:
    """Compare keeping the capital in each supported currency for ``years``.

    For every target currency the capital is converted at the live spot rate,
    grown at that currency's APY, then converted back to ``base_currency`` so
    the results are directly comparable.
    """
    apy_table = apy_table or DEFAULT_APY
    base_currency = base_currency.upper()
    results: dict[str, APYResult] = {}

    for currency, apy in apy_table.items():
        currency = currency.upper()
        if currency == base_currency:
            grown = project_apy(
                principal,
                apy,
                years,
                monthly_contribution=monthly_contribution,
            )
            results[currency] = grown
            continue

        to_rate = get_fx_rate(base_currency, currency)
        back_rate = get_fx_rate(currency, base_currency)
        local_principal = principal * to_rate
        grown = project_apy(
            local_principal,
            apy,
            years,
            monthly_contribution=monthly_contribution * to_rate,
        )
        final_in_base = grown.final_value * back_rate
        results[currency] = APYResult(
            principal=float(principal),
            apy_percent=apy,
            years=years,
            final_value=final_in_base,
            contributions=grown.contributions * back_rate,
        )

    return results
