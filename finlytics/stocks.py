"""High-level stock analysis: data + indicators + metrics + a signal score."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from finlytics import indicators, metrics
from finlytics.config import DEFAULT_BENCHMARK
from finlytics.data import DataError, get_history

__all__ = ["StockAnalysis", "StockAnalyzer"]


@dataclass
class StockAnalysis:
    """Container for everything computed about a single ticker."""

    symbol: str
    period: str
    last_price: float
    history: pd.DataFrame
    returns: pd.Series
    metrics: dict[str, float]
    indicators: dict[str, float]
    signal: str = "HOLD"
    signal_score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        """A flat, serialisable view suitable for printing or JSON export."""
        return {
            "symbol": self.symbol,
            "last_price": round(self.last_price, 4),
            "signal": self.signal,
            "signal_score": round(self.signal_score, 3),
            **{k: round(v, 4) for k, v in self.metrics.items()},
            **{k: round(v, 4) for k, v in self.indicators.items()},
        }


class StockAnalyzer:
    """Fetch a ticker and derive indicators, risk metrics and a trade signal."""

    def __init__(self, benchmark: str = DEFAULT_BENCHMARK) -> None:
        self.benchmark = benchmark

    def analyze(self, symbol: str, period: str = "1y") -> StockAnalysis:
        history = get_history(symbol, period=period)
        close = history["Close"].dropna()
        if len(close) < 30:
            raise DataError(f"Not enough history for {symbol!r} to analyse.")

        rets = indicators.daily_returns(close)

        metric_values = {
            "annual_return": metrics.annualised_return(rets),
            "annual_volatility": metrics.annualised_volatility(rets),
            "sharpe": metrics.sharpe_ratio(rets),
            "sortino": metrics.sortino_ratio(rets),
            "max_drawdown": metrics.max_drawdown(close),
            "beta": self._beta_vs_benchmark(rets, period),
        }

        rsi_series = indicators.rsi(close)
        macd_frame = indicators.macd(close)
        sma50 = indicators.sma(close, 50)
        sma200 = indicators.sma(close, 200)

        indicator_values = {
            "rsi": float(rsi_series.iloc[-1]),
            "macd_hist": float(macd_frame["histogram"].iloc[-1]),
            "sma50": float(sma50.iloc[-1]) if sma50.notna().any() else float("nan"),
            "sma200": float(sma200.iloc[-1]) if sma200.notna().any() else float("nan"),
        }

        analysis = StockAnalysis(
            symbol=symbol.upper(),
            period=period,
            last_price=float(close.iloc[-1]),
            history=history,
            returns=rets,
            metrics=metric_values,
            indicators=indicator_values,
        )
        self._score_signal(analysis)
        return analysis

    def _beta_vs_benchmark(self, rets: pd.Series, period: str) -> float:
        try:
            bench = get_history(self.benchmark, period=period)["Close"].dropna()
        except DataError:
            return float("nan")
        return metrics.beta(rets, indicators.daily_returns(bench))

    @staticmethod
    def _score_signal(analysis: StockAnalysis) -> None:
        """Combine several technical signals into a score in roughly [-3, 3]."""
        score = 0.0
        reasons: list[str] = []
        ind = analysis.indicators

        rsi = ind["rsi"]
        if rsi < 30:
            score += 1
            reasons.append(f"RSI {rsi:.0f} → oversold (bullish)")
        elif rsi > 70:
            score -= 1
            reasons.append(f"RSI {rsi:.0f} → overbought (bearish)")

        if ind["macd_hist"] > 0:
            score += 1
            reasons.append("MACD histogram positive (upward momentum)")
        else:
            score -= 1
            reasons.append("MACD histogram negative (downward momentum)")

        sma50, sma200 = ind["sma50"], ind["sma200"]
        if sma50 == sma50 and sma200 == sma200:  # not NaN
            if sma50 > sma200:
                score += 1
                reasons.append("Golden cross (SMA50 > SMA200)")
            else:
                score -= 1
                reasons.append("Death cross (SMA50 < SMA200)")

        if analysis.metrics["sharpe"] > 1:
            score += 0.5
            reasons.append("Sharpe > 1 (attractive risk-adjusted return)")

        analysis.signal_score = score
        analysis.reasons = reasons
        if score >= 1.5:
            analysis.signal = "BUY"
        elif score <= -1.5:
            analysis.signal = "SELL"
        else:
            analysis.signal = "HOLD"
