"""Command-line interface for Finlytics.

Subcommands::

    finlytics apy        Compound/APY projection and multi-currency comparison
    finlytics fx         Convert money between currencies at the spot rate
    finlytics stock      Full technical + risk analysis of a ticker
    finlytics forecast   ML next-day forecast + Monte-Carlo projection
    finlytics portfolio  Risk/return analytics for a basket of assets
    finlytics analyze    Everything above for one ticker, with an AI briefing
    finlytics serve      Launch the modern web interface
"""

from __future__ import annotations

import argparse
import json
import sys

from finlytics import __version__


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _cmd_apy(args: argparse.Namespace) -> int:
    from finlytics.apy import compare_currencies, project_apy

    if args.compare:
        results = compare_currencies(
            args.amount,
            args.currency,
            years=args.years,
            monthly_contribution=args.monthly,
        )
        _print(
            {
                cur: {
                    "final_value": round(r.final_value, 2),
                    "profit": round(r.profit, 2),
                }
                for cur, r in results.items()
            }
        )
    else:
        r = project_apy(
            args.amount,
            args.apy,
            args.years,
            monthly_contribution=args.monthly,
        )
        _print(
            {
                "principal": round(r.principal, 2),
                "apy_percent": r.apy_percent,
                "years": r.years,
                "contributions": round(r.contributions, 2),
                "final_value": round(r.final_value, 2),
                "profit": round(r.profit, 2),
            }
        )
    return 0


def _cmd_fx(args: argparse.Namespace) -> int:
    from finlytics.fx import convert

    result = convert(args.amount, args.from_currency, args.to_currency)
    _print(
        {
            "amount": result.amount,
            "from": result.from_currency,
            "to": result.to_currency,
            "rate": round(result.rate, 6),
            "converted": round(result.converted, 2),
        }
    )
    return 0


def _cmd_stock(args: argparse.Namespace) -> int:
    from finlytics.stocks import StockAnalyzer

    analysis = StockAnalyzer().analyze(args.symbol, period=args.period)
    out = analysis.summary()
    out["reasons"] = analysis.reasons
    _print(out)
    return 0


def _cmd_forecast(args: argparse.Namespace) -> int:
    from finlytics.ai.forecast import Forecaster, monte_carlo
    from finlytics.data import get_history

    close = get_history(args.symbol, period=args.period)["Close"].dropna()
    forecast = Forecaster().fit_predict(args.symbol, close)
    mc = monte_carlo(args.symbol, close, horizon_days=args.horizon)
    _print({"ml_forecast": forecast.summary(), "monte_carlo": mc.summary()})
    return 0


def _cmd_portfolio(args: argparse.Namespace) -> int:
    from finlytics.portfolio import analyze_portfolio

    weights = args.weights if args.weights else None
    result = analyze_portfolio(args.symbols, weights, period=args.period)
    _print(result.summary())
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from finlytics.web.server import run

    print(f"Finlytics web UI ->  http://{args.host}:{args.port}  (Ctrl+C to stop)")
    run(host=args.host, port=args.port)
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    from finlytics.ai.forecast import Forecaster, monte_carlo
    from finlytics.ai.insights import generate_insight
    from finlytics.stocks import StockAnalyzer

    analyzer = StockAnalyzer()
    analysis = analyzer.analyze(args.symbol, period=args.period)
    close = analysis.history["Close"].dropna()

    forecast = Forecaster().fit_predict(args.symbol, close)
    mc = monte_carlo(args.symbol, close, horizon_days=args.horizon)
    briefing = generate_insight(analysis, mc.summary())

    _print(
        {
            "analysis": analysis.summary(),
            "ml_forecast": forecast.summary(),
            "monte_carlo": mc.summary(),
            "ai_briefing": briefing,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finlytics",
        description="AI-powered personal finance & stock analytics toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"finlytics {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_apy = sub.add_parser("apy", help="Compound/APY projection")
    p_apy.add_argument("amount", type=float, help="Initial capital")
    p_apy.add_argument("--apy", type=float, default=5.0, help="APY in %% (single mode)")
    p_apy.add_argument("--years", type=float, default=1.0)
    p_apy.add_argument("--monthly", type=float, default=0.0, help="Monthly contribution")
    p_apy.add_argument("--currency", default="EUR", help="Base currency for --compare")
    p_apy.add_argument(
        "--compare",
        action="store_true",
        help="Compare growth across EUR/USD/GBP at live FX rates",
    )
    p_apy.set_defaults(func=_cmd_apy)

    p_fx = sub.add_parser("fx", help="Convert currency at the spot rate")
    p_fx.add_argument("amount", type=float)
    p_fx.add_argument("from_currency")
    p_fx.add_argument("to_currency")
    p_fx.set_defaults(func=_cmd_fx)

    p_stock = sub.add_parser("stock", help="Technical + risk analysis")
    p_stock.add_argument("symbol")
    p_stock.add_argument("--period", default="1y")
    p_stock.set_defaults(func=_cmd_stock)

    p_fc = sub.add_parser("forecast", help="ML + Monte-Carlo forecast")
    p_fc.add_argument("symbol")
    p_fc.add_argument("--period", default="2y")
    p_fc.add_argument("--horizon", type=int, default=30, help="Projection days")
    p_fc.set_defaults(func=_cmd_forecast)

    p_pf = sub.add_parser("portfolio", help="Portfolio analytics")
    p_pf.add_argument("symbols", nargs="+", help="Tickers, e.g. AAPL MSFT GOOG")
    p_pf.add_argument(
        "--weights", nargs="*", type=float, help="Weights (default: equal)"
    )
    p_pf.add_argument("--period", default="1y")
    p_pf.set_defaults(func=_cmd_portfolio)

    p_an = sub.add_parser("analyze", help="Full analysis + AI briefing")
    p_an.add_argument("symbol")
    p_an.add_argument("--period", default="2y")
    p_an.add_argument("--horizon", type=int, default=30)
    p_an.set_defaults(func=_cmd_analyze)

    p_serve = sub.add_parser("serve", help="Launch the web interface")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - surface clean errors to the shell
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
