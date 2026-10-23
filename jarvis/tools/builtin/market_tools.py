"""
Jarvis OS — Real-Time Market Intelligence Tool.

Queries Yahoo Finance's open v8 chart API directly (zero API key required)
for Indian equities & indices, US tech stocks, and crypto.
Computes 5-period and 15-period SMA momentum to generate Buy/Sell signals.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx
import structlog

from jarvis.tools.base import (
    Tool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger(__name__)

DEFAULT_TICKERS: dict[str, str] = {
    "^NSEI": "Nifty 50",
    "^BSESN": "Sensex",
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "TCS",
    "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "NVDA": "Nvidia",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
}

ALIAS_MAP: dict[str, str] = {
    "nifty": "^NSEI",
    "nifty 50": "^NSEI",
    "sensex": "^BSESN",
    "bse": "^BSESN",
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "hdfc bank": "HDFCBANK.NS",
    "nvidia": "NVDA",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def resolve_symbol(query: str) -> str:
    """Resolve conversational query or ticker to Yahoo Finance symbol."""
    clean = query.strip().lower()
    if clean in ALIAS_MAP:
        return ALIAS_MAP[clean]
    for name, sym in ALIAS_MAP.items():
        if name in clean:
            return sym
    return query.strip().upper()


async def fetch_chart_data(
    symbol: str,
    range_period: str = "5d",
    interval: str = "15m",
) -> dict[str, Any] | None:
    """Fetch raw candle data from Yahoo Finance open chart API."""
    encoded_symbol = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}?range={range_period}&interval={interval}"
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning("market_tools.fetch_failed", symbol=symbol, status=resp.status_code)
                return None
            data = resp.json()
            results = data.get("chart", {}).get("result", [])
            if not results:
                return None
            return results[0]
    except Exception as exc:
        logger.warning("market_tools.fetch_error", symbol=symbol, error=str(exc))
        return None


def calculate_momentum_signal(
    price: float,
    pct_change: float,
    quotes: list[float],
) -> tuple[str, str]:
    """Calculate 5-period & 15-period SMA momentum signal."""
    valid_quotes = [q for q in quotes if q is not None]
    signal = "HOLD"
    reason = "Consolidating near previous close."

    if len(valid_quotes) >= 10:
        sma_short = sum(valid_quotes[-5:]) / 5.0
        sma_long = sum(valid_quotes[-15:]) / min(len(valid_quotes), 15)

        if price > sma_short and sma_short > sma_long and pct_change > 0.5:
            signal = "STRONG BUY"
            reason = "Bullish momentum above short-term and medium-term moving averages."
        elif price > sma_short and pct_change >= 0.0:
            signal = "BUY / ACCUMULATE"
            reason = "Holding above short-term support with positive price action."
        elif price < sma_short and sma_short < sma_long and pct_change < -0.5:
            signal = "STRONG SELL / SHORT"
            reason = "Bearish crossover below major moving averages with active selling pressure."
        elif price < sma_short:
            signal = "SELL / TAKE PROFIT"
            reason = "Slipping below intraday support; risk of further pullback."

    return signal, reason


async def analyze_ticker(symbol: str) -> dict[str, Any] | None:
    """Analyze real-time price, price change, and momentum for a ticker."""
    chart = await fetch_chart_data(symbol)
    if not chart:
        return None

    meta = chart.get("meta", {})
    name = DEFAULT_TICKERS.get(symbol, symbol)
    currency = meta.get("currency", "INR" if ".NS" in symbol or "^" in symbol else "USD")
    curr_symbol = "₹" if currency == "INR" else "$"

    price = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose") or price

    if price is None:
        return None

    change = price - prev_close
    pct_change = (change / prev_close) * 100 if prev_close else 0.0

    quotes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    signal, reason = calculate_momentum_signal(price, pct_change, quotes)

    return {
        "symbol": symbol,
        "name": name,
        "price": round(price, 2),
        "change": round(change, 2),
        "pct_change": round(pct_change, 2),
        "currency": curr_symbol,
        "signal": signal,
        "reason": reason,
        "high": meta.get("regularMarketDayHigh", price),
        "low": meta.get("regularMarketDayLow", price),
    }


class MarketAnalysisTool(Tool):
    """Real-time financial market intelligence and technical analysis tool."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="market_analysis",
            description=(
                "Fetch real-time stock market data, crypto prices, and technical signals "
                "(Buy/Hold/Sell) for Indian indices/stocks (Nifty, Sensex, Reliance), "
                "US equities (Nvidia, Apple), and crypto (Bitcoin). "
                "Calculates 5-day / 15-period SMA momentum without requiring any API keys."
            ),
            category=ToolCategory.RESEARCH,
            parameters=[
                ToolParameter(
                    name="symbol",
                    type="string",
                    description=(
                        "The stock ticker or company name "
                        "(e.g. 'RELIANCE.NS', 'Nifty', 'NVDA', 'Bitcoin')."
                    ),
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="overview",
                    type="boolean",
                    description=(
                        "If true, returns a high-level briefing across primary benchmarks "
                        "(Nifty, Reliance, Nvidia, Bitcoin)."
                    ),
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        symbol_query = str(params.get("symbol", "")).strip()
        overview = bool(params.get("overview", False))

        if overview or not symbol_query:
            # Generate executive market overview
            benchmarks = ["^NSEI", "RELIANCE.NS", "NVDA", "BTC-USD"]
            reports = []
            briefings = []
            for sym in benchmarks:
                data = await analyze_ticker(sym)
                if data:
                    reports.append(data)
                    direction = "up" if data["pct_change"] >= 0 else "down"
                    line = (
                        f"• {data['name']}: {data['currency']}{data['price']:,} "
                        f"({direction} {abs(data['pct_change'])}%) — Signal: {data['signal']}"
                    )
                    briefings.append(line)

            if not reports:
                return ToolResult(
                    success=False,
                    error="Unable to retrieve live market overview at this time.",
                )

            summary_text = "\n".join(briefings)
            return ToolResult(
                success=True,
                output={
                    "type": "market_overview",
                    "benchmarks": reports,
                    "summary": f"Live Market Overview:\n{summary_text}",
                },
            )

        # Single ticker analysis
        resolved = resolve_symbol(symbol_query)
        data = await analyze_ticker(resolved)
        if not data:
            return ToolResult(
                success=False,
                error=(
                    f"Could not retrieve market data for symbol '{symbol_query}' "
                    f"(resolved to '{resolved}')."
                ),
            )

        direction = "▲ up" if data["pct_change"] >= 0 else "▼ down"
        summary = (
            f"{data['name']} ({data['symbol']}) is trading at {data['currency']}{data['price']:,}, "
            f"{direction} {abs(data['pct_change'])}%. "
            f"Technical signal: {data['signal']}. {data['reason']}"
        )

        return ToolResult(
            success=True,
            output={
                "type": "ticker_analysis",
                "ticker": data,
                "summary": summary,
            },
        )


def get_market_tools() -> list[Tool]:
    """Return instances of built-in market tools."""
    return [MarketAnalysisTool()]
