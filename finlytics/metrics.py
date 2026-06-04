"""Risk and performance metrics derived from a return series."""

from __future__ import annotations

import numpy as np
import pandas as pd

from finlytics.config import RISK_FREE_RATE, TRADING_DAYS

__all__ = [
    "annualised_return",
    "annualised_volatility",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "beta",
]


def annualised_return(returns: pd.Series) -> float:
    """Geometric annualised return from a series of periodic returns."""
    returns = returns.dropna()
    if returns.empty:
        return float("nan")
    growth = float((1 + returns).prod())
    years = len(returns) / TRADING_DAYS
    if years <= 0 or growth <= 0:
        return float("nan")
    return growth ** (1 / years) - 1


def annualised_volatility(returns: pd.Series) -> float:
    """Annualised standard deviation of returns."""
    return float(returns.dropna().std() * np.sqrt(TRADING_DAYS))


def sharpe_ratio(returns: pd.Series, risk_free: float = RISK_FREE_RATE) -> float:
    """Annualised Sharpe ratio (excess return per unit of total risk)."""
    vol = annualised_volatility(returns)
    if vol == 0 or np.isnan(vol):
        return float("nan")
    return (annualised_return(returns) - risk_free) / vol


def sortino_ratio(returns: pd.Series, risk_free: float = RISK_FREE_RATE) -> float:
    """Annualised Sortino ratio (excess return per unit of *downside* risk)."""
    returns = returns.dropna()
    downside = returns[returns < 0]
    downside_vol = float(downside.std() * np.sqrt(TRADING_DAYS))
    if downside_vol == 0 or np.isnan(downside_vol):
        return float("nan")
    return (annualised_return(returns) - risk_free) / downside_vol


def max_drawdown(prices: pd.Series) -> float:
    """Largest peak-to-trough decline (returned as a negative fraction)."""
    prices = prices.dropna()
    if prices.empty:
        return float("nan")
    running_max = prices.cummax()
    drawdown = prices / running_max - 1.0
    return float(drawdown.min())


def beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    """Sensitivity of the asset to benchmark moves (CAPM beta)."""
    joined = pd.concat([asset_returns, market_returns], axis=1, join="inner").dropna()
    if len(joined) < 2:
        return float("nan")
    asset, market = joined.iloc[:, 0], joined.iloc[:, 1]
    variance = float(market.var())
    if variance == 0:
        return float("nan")
    covariance = float(asset.cov(market))
    return covariance / variance
