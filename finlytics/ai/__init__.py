"""AI / quantitative layer: forecasting and natural-language insights."""

from __future__ import annotations

from finlytics.ai.forecast import ForecastResult, Forecaster, monte_carlo
from finlytics.ai.insights import generate_insight

__all__ = [
    "Forecaster",
    "ForecastResult",
    "monte_carlo",
    "generate_insight",
]
