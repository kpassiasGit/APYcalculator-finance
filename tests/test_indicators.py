"""Unit tests for technical indicators and metrics (no network required)."""

import numpy as np
import pandas as pd

from finlytics import indicators, metrics
from finlytics.ai.forecast import Forecaster, monte_carlo


def _trending_series(n=300, start=100.0, drift=0.0005, vol=0.01, seed=0):
    rng = np.random.default_rng(seed)
    shocks = rng.normal(drift, vol, size=n)
    prices = start * np.exp(np.cumsum(shocks))
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    return pd.Series(prices, index=idx)


def test_sma_matches_manual_mean():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert indicators.sma(s, 2).iloc[-1] == 4.5


def test_rsi_bounded_0_100():
    s = _trending_series()
    r = indicators.rsi(s).dropna()
    assert r.between(0, 100).all()


def test_macd_columns():
    s = _trending_series()
    frame = indicators.macd(s)
    assert list(frame.columns) == ["macd", "signal", "histogram"]


def test_metrics_are_finite():
    s = _trending_series()
    rets = indicators.daily_returns(s)
    assert np.isfinite(metrics.annualised_return(rets))
    assert np.isfinite(metrics.annualised_volatility(rets))
    assert metrics.max_drawdown(s) <= 0


def test_forecaster_runs_with_fallback():
    s = _trending_series()
    result = Forecaster().fit_predict("TEST", s)
    assert result.direction in {"UP", "DOWN"}
    assert 0.0 <= result.direction_accuracy <= 1.0


def test_monte_carlo_band_ordering():
    s = _trending_series()
    mc = monte_carlo("TEST", s, horizon_days=20, simulations=2000)
    assert mc.lower_5 <= mc.median_price <= mc.upper_95
    assert 0.0 <= mc.prob_profit <= 1.0
