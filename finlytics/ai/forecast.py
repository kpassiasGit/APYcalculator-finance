"""Price forecasting: a supervised ML model plus a Monte-Carlo projection.

Two complementary techniques are offered:

* :class:`Forecaster` trains a model on engineered technical features to predict
  the *next-day return* and direction. It uses scikit-learn's
  ``GradientBoostingRegressor`` when available and transparently falls back to a
  NumPy least-squares linear model so the package works with zero extra
  dependencies.
* :func:`monte_carlo` simulates many future price paths with Geometric Brownian
  Motion to produce a probabilistic projection (median + confidence band).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from finlytics import indicators

__all__ = ["ForecastResult", "Forecaster", "monte_carlo", "MonteCarloResult"]

try:  # Optional, but preferred when present.
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import r2_score

    _HAVE_SKLEARN = True
except ImportError:  # pragma: no cover - exercised only without sklearn
    _HAVE_SKLEARN = False


@dataclass
class ForecastResult:
    """Output of the supervised next-day forecaster."""

    symbol: str
    model: str
    predicted_return: float
    predicted_price: float
    direction: str
    test_r2: float
    direction_accuracy: float

    def summary(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "model": self.model,
            "predicted_next_day_return": round(self.predicted_return, 5),
            "predicted_price": round(self.predicted_price, 4),
            "direction": self.direction,
            "test_r2": round(self.test_r2, 4),
            "direction_accuracy": round(self.direction_accuracy, 4),
        }


def _build_features(close: pd.Series) -> pd.DataFrame:
    """Engineer a compact, leakage-free feature set from closing prices."""
    feat = pd.DataFrame(index=close.index)
    rets = close.pct_change()
    for lag in (1, 2, 3, 5, 10):
        feat[f"ret_lag_{lag}"] = rets.shift(lag - 1)
    feat["sma_ratio_10"] = close / indicators.sma(close, 10) - 1
    feat["sma_ratio_30"] = close / indicators.sma(close, 30) - 1
    feat["rsi"] = indicators.rsi(close) / 100.0
    feat["volatility_10"] = rets.rolling(10).std()
    feat["target"] = rets.shift(-1)  # next-day return
    return feat.dropna()


class _LinearFallback:
    """Tiny ordinary-least-squares regressor (NumPy only)."""

    name = "numpy-linear-regression"

    def __init__(self) -> None:
        self.coef_: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_LinearFallback":
        X1 = np.column_stack([np.ones(len(X)), X])
        self.coef_, *_ = np.linalg.lstsq(X1, y, rcond=None)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X1 = np.column_stack([np.ones(len(X)), X])
        return X1 @ self.coef_


class Forecaster:
    """Train a model on technical features to predict the next-day return."""

    def __init__(self, test_size: float = 0.2) -> None:
        self.test_size = test_size

    def fit_predict(self, symbol: str, close: pd.Series) -> ForecastResult:
        data = _build_features(close)
        if len(data) < 60:
            raise ValueError("Need at least ~60 usable rows to train a forecaster.")

        feature_cols = [c for c in data.columns if c != "target"]
        X = data[feature_cols].to_numpy()
        y = data["target"].to_numpy()

        split = int(len(X) * (1 - self.test_size))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        if _HAVE_SKLEARN:
            model = GradientBoostingRegressor(random_state=42)
            model_name = "sklearn-gradient-boosting"
        else:
            model = _LinearFallback()
            model_name = _LinearFallback.name

        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        test_r2 = _r2(y_test, preds)
        direction_accuracy = float(np.mean(np.sign(preds) == np.sign(y_test)))

        next_return = float(model.predict(X[-1:].reshape(1, -1))[0])
        last_price = float(close.iloc[-1])
        return ForecastResult(
            symbol=symbol.upper(),
            model=model_name,
            predicted_return=next_return,
            predicted_price=last_price * (1 + next_return),
            direction="UP" if next_return >= 0 else "DOWN",
            test_r2=test_r2,
            direction_accuracy=direction_accuracy,
        )


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if _HAVE_SKLEARN:
        return float(r2_score(y_true, y_pred))
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot else 0.0


@dataclass
class MonteCarloResult:
    """Probabilistic price projection from simulated GBM paths."""

    symbol: str
    horizon_days: int
    start_price: float
    expected_price: float
    median_price: float
    lower_5: float
    upper_95: float
    prob_profit: float

    def summary(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "horizon_days": self.horizon_days,
            "start_price": round(self.start_price, 4),
            "expected_price": round(self.expected_price, 4),
            "median_price": round(self.median_price, 4),
            "ci90": [round(self.lower_5, 4), round(self.upper_95, 4)],
            "prob_profit": round(self.prob_profit, 4),
        }


def monte_carlo(
    symbol: str,
    close: pd.Series,
    horizon_days: int = 30,
    simulations: int = 10_000,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Project future prices via Geometric Brownian Motion."""
    log_ret = indicators.log_returns(close)
    mu = float(log_ret.mean())
    sigma = float(log_ret.std())
    start_price = float(close.iloc[-1])

    rng = np.random.default_rng(seed)
    # Simulate cumulative log returns then exponentiate.
    shocks = rng.normal(
        loc=mu - 0.5 * sigma**2,
        scale=sigma,
        size=(simulations, horizon_days),
    )
    paths = start_price * np.exp(np.cumsum(shocks, axis=1))
    ending = paths[:, -1]

    return MonteCarloResult(
        symbol=symbol.upper(),
        horizon_days=horizon_days,
        start_price=start_price,
        expected_price=float(np.mean(ending)),
        median_price=float(np.median(ending)),
        lower_5=float(np.percentile(ending, 5)),
        upper_95=float(np.percentile(ending, 95)),
        prob_profit=float(np.mean(ending > start_price)),
    )
