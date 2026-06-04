"""Multi-asset portfolio analytics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from finlytics import metrics
from finlytics.data import get_history

__all__ = ["PortfolioResult", "analyze_portfolio"]


@dataclass
class PortfolioResult:
    """Aggregate risk/return profile of a weighted basket of assets."""

    weights: dict[str, float]
    annual_return: float
    annual_volatility: float
    sharpe: float
    max_drawdown: float
    correlation: pd.DataFrame
    contributions: dict[str, float]

    def summary(self) -> dict[str, object]:
        return {
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "annual_return": round(self.annual_return, 4),
            "annual_volatility": round(self.annual_volatility, 4),
            "sharpe": round(self.sharpe, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "risk_contributions": {
                k: round(v, 4) for k, v in self.contributions.items()
            },
        }


def _normalise_weights(
    symbols: list[str], weights: list[float] | None
) -> dict[str, float]:
    if weights is None:
        weights = [1.0 / len(symbols)] * len(symbols)
    if len(weights) != len(symbols):
        raise ValueError("Number of weights must match number of symbols.")
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("Weights must sum to a positive number.")
    return {s.upper(): w / total for s, w in zip(symbols, weights)}


def analyze_portfolio(
    symbols: list[str],
    weights: list[float] | None = None,
    period: str = "1y",
) -> PortfolioResult:
    """Compute return, risk, correlation and risk contributions for a basket."""
    if not symbols:
        raise ValueError("Provide at least one symbol.")

    weight_map = _normalise_weights(symbols, weights)

    closes = {}
    for symbol in weight_map:
        closes[symbol] = get_history(symbol, period=period)["Close"].dropna()

    prices = pd.DataFrame(closes).dropna()
    if prices.empty:
        raise ValueError("Assets have no overlapping trading history.")

    returns = prices.pct_change().dropna()
    w = np.array([weight_map[s] for s in prices.columns])

    portfolio_returns = returns.to_numpy() @ w
    portfolio_returns = pd.Series(portfolio_returns, index=returns.index)
    portfolio_prices = (1 + portfolio_returns).cumprod()

    cov = returns.cov().to_numpy() * 252
    portfolio_var = float(w @ cov @ w)
    # Marginal risk contribution of each asset (sums to total variance).
    marginal = cov @ w
    contributions = {
        sym: float(w[i] * marginal[i] / portfolio_var) if portfolio_var else 0.0
        for i, sym in enumerate(prices.columns)
    }

    return PortfolioResult(
        weights=weight_map,
        annual_return=metrics.annualised_return(portfolio_returns),
        annual_volatility=float(np.sqrt(portfolio_var)),
        sharpe=metrics.sharpe_ratio(portfolio_returns),
        max_drawdown=metrics.max_drawdown(portfolio_prices),
        correlation=returns.corr(),
        contributions=contributions,
    )
