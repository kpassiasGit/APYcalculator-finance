"""Vectorised technical indicators.

Pure functions over a pandas ``Series`` of closing prices (or an OHLCV frame),
with no network access so they are fast and trivially unit-testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "sma",
    "ema",
    "rsi",
    "macd",
    "bollinger_bands",
    "daily_returns",
    "log_returns",
]


def sma(prices: pd.Series, window: int = 20) -> pd.Series:
    """Simple moving average."""
    return prices.rolling(window=window, min_periods=window).mean()


def ema(prices: pd.Series, span: int = 20) -> pd.Series:
    """Exponential moving average."""
    return prices.ewm(span=span, adjust=False).mean()


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple percentage returns."""
    return prices.pct_change().dropna()


def log_returns(prices: pd.Series) -> pd.Series:
    """Continuously-compounded (log) returns."""
    return np.log(prices / prices.shift(1)).dropna()


def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(100.0)  # all-gain windows -> RSI 100


def macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Return MACD line, signal line and histogram."""
    macd_line = ema(prices, fast) - ema(prices, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "histogram": histogram}
    )


def bollinger_bands(
    prices: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """Return middle (SMA), upper and lower Bollinger bands."""
    middle = sma(prices, window)
    std = prices.rolling(window=window, min_periods=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return pd.DataFrame({"middle": middle, "upper": upper, "lower": lower})
