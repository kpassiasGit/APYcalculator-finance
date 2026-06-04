"""Market-data access layer.

A thin, well-behaved wrapper around :mod:`yfinance` that adds:

* a small time-based in-process cache (avoids hammering the API);
* consistent error handling via :class:`DataError`;
* a single place to swap the data provider in the future.
"""

from __future__ import annotations

import time
from typing import Final

import pandas as pd

# Optional: route TLS verification through the OS trust store. This lets the
# toolkit work behind corporate TLS-intercepting proxies whose root CA is in
# the system store but not in certifi. No-op if `truststore` isn't installed.
try:  # pragma: no cover - environment dependent
    import truststore as _truststore

    _truststore.inject_into_ssl()
except Exception:  # noqa: BLE001 - never fail import because of this helper
    pass

try:
    import yfinance as yf
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "yfinance is required for market data. Install it with "
        "`pip install yfinance`."
    ) from exc

from finlytics.config import CACHE_TTL

__all__ = ["DataError", "get_history", "get_fx_rate", "clear_cache"]

_CACHE: Final[dict[tuple, tuple[float, pd.DataFrame]]] = {}


class DataError(RuntimeError):
    """Raised when market data cannot be retrieved or is empty."""


def _cache_get(key: tuple) -> pd.DataFrame | None:
    hit = _CACHE.get(key)
    if hit is None:
        return None
    ts, frame = hit
    if time.time() - ts > CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return frame.copy()


def _cache_put(key: tuple, frame: pd.DataFrame) -> None:
    _CACHE[key] = (time.time(), frame.copy())


def clear_cache() -> None:
    """Empty the in-process price cache."""
    _CACHE.clear()


def get_history(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Return an OHLCV history frame for ``symbol``.

    Parameters
    ----------
    symbol:
        A Yahoo Finance ticker (e.g. ``"AAPL"``, ``"BTC-USD"``).
    period:
        Look-back window understood by yfinance (``"1mo"``, ``"1y"``, ``"5y"`` …).
    interval:
        Sampling interval (``"1d"``, ``"1h"`` …).

    Raises
    ------
    DataError
        If the ticker is unknown or no rows are returned.
    """
    key = ("hist", symbol.upper(), period, interval)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        frame = yf.Ticker(symbol).history(period=period, interval=interval)
    except Exception as exc:  # noqa: BLE001 - normalise any provider error
        raise DataError(f"Could not download data for {symbol!r}: {exc}") from exc

    if frame is None or frame.empty:
        raise DataError(
            f"No data returned for {symbol!r} (check the ticker / period)."
        )

    frame = frame.dropna(how="all")
    _cache_put(key, frame)
    return frame


def get_fx_rate(from_currency: str, to_currency: str) -> float:
    """Return the latest spot FX rate to convert 1 ``from`` into ``to``."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    if from_currency == to_currency:
        return 1.0

    symbol = f"{from_currency}{to_currency}=X"
    frame = get_history(symbol, period="5d", interval="1d")
    try:
        return float(frame["Close"].dropna().iloc[-1])
    except (KeyError, IndexError) as exc:
        raise DataError(
            f"No exchange rate available for {from_currency}->{to_currency}."
        ) from exc
