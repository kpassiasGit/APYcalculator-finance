"""Central configuration and tunable defaults for Finlytics.

Values can be overridden at runtime via environment variables so the toolkit
can be reconfigured without code changes (handy for CI or containers).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Number of trading days used to annualise daily statistics.
TRADING_DAYS: int = 252

# Risk-free rate (annual, decimal) used for Sharpe/Sortino ratios.
RISK_FREE_RATE: float = float(os.getenv("FINLYTICS_RISK_FREE", "0.03"))

# Default market benchmark used for beta/relative-strength calculations.
DEFAULT_BENCHMARK: str = os.getenv("FINLYTICS_BENCHMARK", "^GSPC")  # S&P 500

# Indicative annual percentage yields per currency (decimal-friendly, in %).
# These are *defaults only*; override on the CLI with ``--apy``.
DEFAULT_APY: dict[str, float] = {
    "GBP": float(os.getenv("FINLYTICS_APY_GBP", "5.12")),
    "USD": float(os.getenv("FINLYTICS_APY_USD", "5.05")),
    "EUR": float(os.getenv("FINLYTICS_APY_EUR", "3.85")),
}

SUPPORTED_CURRENCIES: tuple[str, ...] = ("EUR", "USD", "GBP")


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for the optional LLM ('AI analyst') narrative layer."""

    api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    model: str = os.getenv("FINLYTICS_LLM_MODEL", "claude-opus-4-8")
    max_tokens: int = int(os.getenv("FINLYTICS_LLM_MAX_TOKENS", "900"))

    @property
    def enabled(self) -> bool:
        """True when an API key is present and the SDK can be imported."""
        if not self.api_key:
            return False
        try:  # pragma: no cover - depends on optional dependency
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True


# How long (seconds) downloaded price frames stay in the in-process cache.
CACHE_TTL: int = int(os.getenv("FINLYTICS_CACHE_TTL", "900"))
