"""Natural-language analyst.

When an Anthropic API key is configured the computed metrics are handed to an
LLM which writes a concise, plain-English briefing. With no key (the default)
a deterministic, rule-based narrative is produced instead, so the feature is
always available and never blocks on a network call.
"""

from __future__ import annotations

from finlytics.config import LLMConfig
from finlytics.stocks import StockAnalysis

__all__ = ["generate_insight"]


def generate_insight(
    analysis: StockAnalysis,
    forecast_summary: dict | None = None,
    *,
    config: LLMConfig | None = None,
) -> str:
    """Return a human-readable briefing for a stock analysis.

    Uses the LLM when available, otherwise a built-in template.
    """
    config = config or LLMConfig()
    if config.enabled:
        try:  # pragma: no cover - network/optional path
            return _llm_insight(analysis, forecast_summary, config)
        except Exception:  # noqa: BLE001 - never fail because of the optional path
            pass
    return _rule_based_insight(analysis, forecast_summary)


def _facts(analysis: StockAnalysis, forecast_summary: dict | None) -> str:
    m, ind = analysis.metrics, analysis.indicators
    lines = [
        f"Symbol: {analysis.symbol}",
        f"Last price: {analysis.last_price:.2f}",
        f"Signal: {analysis.signal} (score {analysis.signal_score:+.1f})",
        f"Annualised return: {m['annual_return'] * 100:.1f}%",
        f"Annualised volatility: {m['annual_volatility'] * 100:.1f}%",
        f"Sharpe: {m['sharpe']:.2f} | Sortino: {m['sortino']:.2f}",
        f"Max drawdown: {m['max_drawdown'] * 100:.1f}%",
        f"Beta: {m['beta']:.2f}",
        f"RSI: {ind['rsi']:.0f} | MACD hist: {ind['macd_hist']:+.3f}",
    ]
    if forecast_summary:
        lines.append(f"Model forecast: {forecast_summary}")
    return "\n".join(lines)


def _llm_insight(
    analysis: StockAnalysis,
    forecast_summary: dict | None,
    config: LLMConfig,
) -> str:  # pragma: no cover - requires network + key
    import anthropic

    client = anthropic.Anthropic(api_key=config.api_key)
    prompt = (
        "You are an equity research assistant. Using ONLY the metrics below, "
        "write a concise 4-6 sentence briefing covering momentum, risk and a "
        "balanced takeaway. Do not invent data. End with one line of risk "
        "disclaimer.\n\n" + _facts(analysis, forecast_summary)
    )
    message = client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def _rule_based_insight(
    analysis: StockAnalysis, forecast_summary: dict | None
) -> str:
    m, ind = analysis.metrics, analysis.indicators
    parts: list[str] = []

    trend = "uptrend" if ind["macd_hist"] > 0 else "downtrend"
    parts.append(
        f"{analysis.symbol} is trading at {analysis.last_price:.2f} and the "
        f"technical picture points to a short-term {trend}. The composite "
        f"signal is {analysis.signal} (score {analysis.signal_score:+.1f})."
    )

    if ind["rsi"] > 70:
        parts.append(f"Momentum looks stretched with RSI at {ind['rsi']:.0f} (overbought).")
    elif ind["rsi"] < 30:
        parts.append(f"RSI at {ind['rsi']:.0f} suggests the name is oversold and may rebound.")
    else:
        parts.append(f"RSI at {ind['rsi']:.0f} is neutral.")

    sharpe = m["sharpe"]
    risk_word = "attractive" if sharpe > 1 else "modest" if sharpe > 0 else "poor"
    parts.append(
        f"On a risk-adjusted basis the {risk_word} Sharpe of {sharpe:.2f} pairs "
        f"with {m['annual_volatility'] * 100:.0f}% annualised volatility and a "
        f"max drawdown of {m['max_drawdown'] * 100:.0f}%."
    )

    if forecast_summary:
        direction = forecast_summary.get("direction") or forecast_summary.get(
            "prob_profit"
        )
        parts.append(f"Quant projection: {forecast_summary}.")

    if analysis.reasons:
        parts.append("Key drivers: " + "; ".join(analysis.reasons) + ".")

    parts.append(
        "This is an automated, educational summary — not financial advice."
    )
    return " ".join(parts)
