"""FastAPI backend that exposes the Finlytics library over a small JSON API
and serves the single-page front-end.

Run with::

    finlytics serve                 # then open http://127.0.0.1:8000
    python -m finlytics serve --port 8000
"""

from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "The web interface needs FastAPI & uvicorn. Install with "
        '`pip install -e ".[web]"` or `pip install fastapi uvicorn`.'
    ) from exc

_STATIC = Path(__file__).parent / "static"


# ---- Request models --------------------------------------------------------
class APYRequest(BaseModel):
    amount: float
    apy: float = 5.0
    years: float = 1.0
    monthly: float = 0.0
    currency: str = "EUR"
    compare: bool = False


class FXRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


class StockRequest(BaseModel):
    symbol: str
    period: str = "1y"


class ForecastRequest(BaseModel):
    symbol: str
    period: str = "2y"
    horizon: int = 30


class PortfolioRequest(BaseModel):
    symbols: list[str]
    weights: list[float] | None = None
    period: str = "1y"


class AnalyzeRequest(BaseModel):
    symbol: str
    period: str = "2y"
    horizon: int = 30


def create_app() -> "FastAPI":
    app = FastAPI(title="Finlytics", version="2.0.0")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @app.post("/api/apy")
    def api_apy(req: APYRequest):
        from finlytics.apy import compare_currencies, project_apy

        try:
            if req.compare:
                results = compare_currencies(
                    req.amount, req.currency, years=req.years,
                    monthly_contribution=req.monthly,
                )
                return {
                    "mode": "compare",
                    "base": req.currency.upper(),
                    "results": {
                        c: {
                            "final_value": round(r.final_value, 2),
                            "profit": round(r.profit, 2),
                            "apy_percent": r.apy_percent,
                        }
                        for c, r in results.items()
                    },
                }
            r = project_apy(
                req.amount, req.apy, req.years, monthly_contribution=req.monthly
            )
            return {
                "mode": "single",
                "principal": round(r.principal, 2),
                "apy_percent": r.apy_percent,
                "years": r.years,
                "contributions": round(r.contributions, 2),
                "final_value": round(r.final_value, 2),
                "profit": round(r.profit, 2),
            }
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/fx")
    def api_fx(req: FXRequest):
        from finlytics.fx import convert

        try:
            c = convert(req.amount, req.from_currency, req.to_currency)
            return {
                "amount": c.amount,
                "from": c.from_currency,
                "to": c.to_currency,
                "rate": round(c.rate, 6),
                "converted": round(c.converted, 2),
            }
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/stock")
    def api_stock(req: StockRequest):
        from finlytics.stocks import StockAnalyzer

        try:
            a = StockAnalyzer().analyze(req.symbol, period=req.period)
            out = a.summary()
            out["reasons"] = a.reasons
            out["history"] = _price_series(a.history)
            return out
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/forecast")
    def api_forecast(req: ForecastRequest):
        from finlytics.ai.forecast import Forecaster, monte_carlo
        from finlytics.data import get_history

        try:
            close = get_history(req.symbol, period=req.period)["Close"].dropna()
            forecast = Forecaster().fit_predict(req.symbol, close)
            mc = monte_carlo(req.symbol, close, horizon_days=req.horizon)
            return {"ml_forecast": forecast.summary(), "monte_carlo": mc.summary()}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/portfolio")
    def api_portfolio(req: PortfolioRequest):
        from finlytics.portfolio import analyze_portfolio

        try:
            result = analyze_portfolio(req.symbols, req.weights, period=req.period)
            return result.summary()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/analyze")
    def api_analyze(req: AnalyzeRequest):
        from finlytics.ai.forecast import Forecaster, monte_carlo
        from finlytics.ai.insights import generate_insight
        from finlytics.stocks import StockAnalyzer

        try:
            a = StockAnalyzer().analyze(req.symbol, period=req.period)
            close = a.history["Close"].dropna()
            forecast = Forecaster().fit_predict(req.symbol, close)
            mc = monte_carlo(req.symbol, close, horizon_days=req.horizon)
            briefing = generate_insight(a, mc.summary())
            out = a.summary()
            out["reasons"] = a.reasons
            return {
                "analysis": out,
                "history": _price_series(a.history),
                "ml_forecast": forecast.summary(),
                "monte_carlo": mc.summary(),
                "ai_briefing": briefing,
            }
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    if _STATIC.exists():
        app.mount("/static", StaticFiles(directory=_STATIC), name="static")

    return app


def _price_series(history, max_points: int = 180) -> dict:
    """Down-sample a price history to a compact {dates, closes} payload."""
    close = history["Close"].dropna()
    if len(close) > max_points:
        step = len(close) // max_points
        close = close.iloc[::step]
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in close.index],
        "closes": [round(float(v), 4) for v in close.values],
    }


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Launch the dev server with uvicorn."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)
