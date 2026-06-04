"""Currency conversion helpers built on the data layer."""

from __future__ import annotations

from dataclasses import dataclass

from finlytics.config import SUPPORTED_CURRENCIES
from finlytics.data import get_fx_rate

__all__ = ["Conversion", "convert", "cross_rates"]


@dataclass(frozen=True)
class Conversion:
    """Result of converting an amount between two currencies."""

    amount: float
    from_currency: str
    to_currency: str
    rate: float

    @property
    def converted(self) -> float:
        return self.amount * self.rate

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"{self.amount:,.2f} {self.from_currency} = "
            f"{self.converted:,.2f} {self.to_currency} "
            f"(rate {self.rate:.4f})"
        )


def convert(amount: float, from_currency: str, to_currency: str) -> Conversion:
    """Convert ``amount`` from one currency to another at the latest spot rate."""
    rate = get_fx_rate(from_currency, to_currency)
    return Conversion(amount, from_currency.upper(), to_currency.upper(), rate)


def cross_rates(
    base: str, currencies: tuple[str, ...] = SUPPORTED_CURRENCIES
) -> dict[str, float]:
    """Return spot rates from ``base`` to each currency in ``currencies``."""
    base = base.upper()
    return {c.upper(): get_fx_rate(base, c) for c in currencies if c.upper() != base}
