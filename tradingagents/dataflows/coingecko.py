"""
CoinGecko Data Source
---------------------
Fetches cryptocurrency market data from the CoinGecko public API (no API key required).

Credit: CoinGecko API (https://www.coingecko.com/en/api)
        Crypto extension by Aya Chafi (github.com/chafiaya920-del)
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Annotated
from urllib import request, error

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

SYMBOL_TO_ID = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
    "DOGE": "dogecoin", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "MATIC": "matic-network", "UNI": "uniswap",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "ATOM": "cosmos",
    "FIL": "filecoin", "NEAR": "near", "APT": "aptos",
    "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
    "INJ": "injective-protocol", "SEI": "sei-network",
    "PEPE": "pepe", "WIF": "dogwifcoin", "BONK": "bonk",
}


def _fetch(endpoint: str, params: dict = None, retries: int = 2) -> dict:
    """Make a GET request to the CoinGecko API."""
    url = f"{COINGECKO_BASE}/{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    for attempt in range(retries + 1):
        try:
            req = request.Request(url, headers={"Accept": "application/json"})
            with request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception:
            if attempt < retries:
                time.sleep(1)
                continue
            raise
    raise RuntimeError(f"CoinGecko request failed: {url}")


def resolve_coin_id(symbol: str) -> str:
    """Resolve a ticker symbol (e.g. BTC) to a CoinGecko coin ID."""
    sym = symbol.upper().replace("-USD", "").replace("USDT", "").replace("USDC", "")
    if sym in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[sym]
    try:
        result = _fetch("search", {"query": sym})
        coins = result.get("coins", [])
        if coins:
            return coins[0]["id"]
    except Exception:
        pass
    return sym.lower()


def get_crypto_price_data(
    symbol: Annotated[str, "Crypto ticker symbol (e.g. BTC, ETH, SOL)"],
    start_date: Annotated[str, "Start date in YYYY-MM-DD format"],
    end_date: Annotated[str, "End date in YYYY-MM-DD format"],
) -> str:
    """Fetch historical price and volume data for a cryptocurrency from CoinGecko."""
    coin_id = resolve_coin_id(symbol)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    days = max(1, (end_dt - start_dt).days + 1)

    try:
        data = _fetch(
            f"coins/{coin_id}/market_chart",
            {"vs_currency": "usd", "days": days, "interval": "daily"},
        )
    except Exception as e:
        return f"Error fetching price data for {symbol}: {e}"

    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])
    if not prices:
        return f"No price data available for {symbol}"

    vol_map = {int(v[0]): v[1] for v in volumes}
    rows = ["date,price,volume"]
    for ts, price in prices:
        date_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        vol = vol_map.get(ts, 0)
        rows.append(f"{date_str},{price:.4f},{vol:.0f}")
    return "\n".join(rows)


def get_crypto_market_data(
    symbol: Annotated[str, "Crypto ticker symbol (e.g. BTC, ETH, SOL)"],
    curr_date: Annotated[str, "Current date in YYYY-MM-DD format"],
) -> str:
    """Fetch market cap, volume, price changes, ATH, and supply data for a cryptocurrency."""
    coin_id = resolve_coin_id(symbol)
    try:
        data = _fetch(
            "coins/markets",
            {
                "vs_currency": "usd",
                "ids": coin_id,
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d,30d",
            },
        )
    except Exception as e:
        return f"Error fetching market data for {symbol}: {e}"

    if not data:
        return f"No market data available for {symbol}"

    c = data[0]
    lines = [
        f"=== {c.get('name', symbol)} ({symbol.upper()}) Market Data - {curr_date} ===",
        f"Current Price:      ${c.get('current_price', 'N/A'):,}",
        f"Market Cap:         ${c.get('market_cap', 0):,}",
        f"Market Cap Rank:    #{c.get('market_cap_rank', 'N/A')}",
        f"24h Volume:         ${c.get('total_volume', 0):,}",
        f"Circulating Supply: {c.get('circulating_supply', 'N/A'):,}",
        f"Max Supply:         {c.get('max_supply', 'Unlimited')}",
        "",
        "Price Changes:",
        f"  1h:   {c.get('price_change_percentage_1h_in_currency', 'N/A')}%",
        f"  24h:  {c.get('price_change_24h', 'N/A')}%",
        f"  7d:   {c.get('price_change_percentage_7d_in_currency', 'N/A')}%",
        f"  30d:  {c.get('price_change_percentage_30d_in_currency', 'N/A')}%",
        "",
        f"ATH:       ${c.get('ath', 'N/A'):,} ({c.get('ath_date', 'N/A')})",
        f"From ATH:  {c.get('ath_change_percentage', 'N/A')}%",
        f"24h High:  ${c.get('high_24h', 'N/A'):,}",
        f"24h Low:   ${c.get('low_24h', 'N/A'):,}",
    ]
    return "\n".join(str(l) for l in lines)


def get_crypto_coin_info(
    symbol: Annotated[str, "Crypto ticker symbol (e.g. BTC, ETH, SOL)"],
) -> str:
    """Fetch description, technology info, developer activity, and community stats for a crypto."""
    coin_id = resolve_coin_id(symbol)
    try:
        data = _fetch(
            f"coins/{coin_id}",
            {
                "localization": "false", "tickers": "false",
                "market_data": "false", "community_data": "true",
                "developer_data": "true",
            },
        )
    except Exception as e:
        return f"Error fetching coin info for {symbol}: {e}"

    desc = data.get("description", {}).get("en", "No description available.")
    if len(desc) > 800:
        desc = desc[:800] + "..."

    dev = data.get("developer_data", {})
    comm = data.get("community_data", {})
    categories = ", ".join(data.get("categories", [])[:5]) or "N/A"

    lines = [
        f"=== {data.get('name', symbol)} ({symbol.upper()}) Info ===",
        f"Categories:   {categories}",
        f"Genesis Date: {data.get('genesis_date', 'N/A')}",
        f"Algorithm:    {data.get('hashing_algorithm', 'N/A')}",
        "",
        "Description:",
        desc,
        "",
        "Developer Activity (last 4 weeks):",
        f"  GitHub Stars:   {dev.get('stars', 'N/A')}",
        f"  Forks:          {dev.get('forks', 'N/A')}",
        f"  Commits (4w):   {dev.get('commit_count_4_weeks', 'N/A')}",
        "",
        "Community:",
        f"  Twitter Followers:  {comm.get('twitter_followers', 'N/A')}",
        f"  Reddit Subscribers: {comm.get('reddit_subscribers', 'N/A')}",
    ]
    return "\n".join(str(l) for l in lines)
