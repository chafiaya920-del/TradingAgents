"""
Crypto Analyst Agent
--------------------
Analyzes cryptocurrency assets using CoinGecko market data.
Produces a crypto market report covering price action, market structure,
developer activity, and community metrics.

Credit: Based on TradingAgents by TradingAgents Team.
        Crypto analyst by Aya Chafi (github.com/chafiaya920-del)
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from typing import Annotated

from tradingagents.dataflows.coingecko import (
    get_crypto_price_data,
    get_crypto_market_data,
    get_crypto_coin_info,
)


# Wrap data functions as LangChain tools
@tool
def crypto_get_price(
    symbol: Annotated[str, "Crypto ticker symbol (e.g. BTC, ETH, SOL)"],
    start_date: Annotated[str, "Start date YYYY-MM-DD"],
    end_date: Annotated[str, "End date YYYY-MM-DD"],
) -> str:
    """Get historical price and volume data for a cryptocurrency from CoinGecko."""
    return get_crypto_price_data(symbol, start_date, end_date)


@tool
def crypto_get_market_data(
    symbol: Annotated[str, "Crypto ticker symbol (e.g. BTC, ETH, SOL)"],
    curr_date: Annotated[str, "Current date YYYY-MM-DD"],
) -> str:
    """Get market cap, volume, price changes, ATH, and supply data for a cryptocurrency."""
    return get_crypto_market_data(symbol, curr_date)


@tool
def crypto_get_coin_info(
    symbol: Annotated[str, "Crypto ticker symbol (e.g. BTC, ETH, SOL)"],
) -> str:
    """Get description, categories, developer activity, and community stats for a cryptocurrency."""
    return get_crypto_coin_info(symbol)


CRYPTO_ANALYST_TOOLS = [crypto_get_price, crypto_get_market_data, crypto_get_coin_info]

SYSTEM_PROMPT = """You are an expert cryptocurrency analyst with deep knowledge of blockchain technology,
DeFi, tokenomics, and on-chain metrics. Your role is to perform comprehensive technical and fundamental
analysis of cryptocurrency assets using real market data.

For the given cryptocurrency and date, you MUST call the available tools to gather data:
1. Call `crypto_get_price` to get historical price and volume data (use the last 30 days)
2. Call `crypto_get_market_data` to get current market metrics
3. Call `crypto_get_coin_info` to understand the project fundamentals and community

After gathering data, produce a structured crypto market report covering:

**Price Action & Technicals**
- Current price, recent trend (30d), support/resistance levels
- Volume analysis (is buying or selling pressure dominant?)
- Momentum signals (is the asset accelerating or decelerating?)

**Market Structure**
- Market cap rank and dominance position
- Distance from ATH (recovery potential vs. overhead resistance)
- Supply dynamics (circulating vs. max supply, emission schedule implications)

**Fundamental Strength**
- Project category and use case (L1, DeFi, GameFi, AI, etc.)
- Developer activity (commit frequency, contributor count)
- Community size and engagement (Twitter, Reddit)

**Risk Assessment**
- Volatility level and key risk factors
- Liquidity (24h volume relative to market cap)
- Macro crypto market context (bull/bear phase)

**Summary**
- Overall signal: BULLISH / NEUTRAL / BEARISH with brief rationale

Format your report with clear headers and bullet points for readability.
"""


def create_crypto_analyst(llm):
    """Create a crypto analyst agent node.

    Args:
        llm: LangChain LLM instance (bound with tools internally).

    Returns:
        crypto_analyst_node function for use in LangGraph.
    """
    tools = CRYPTO_ANALYST_TOOLS
    llm_with_tools = llm.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        (
            "human",
            "Analyze the cryptocurrency {company_of_interest} as of {trade_date}. "
            "Use the available tools to gather data, then produce a comprehensive crypto market report.",
        ),
    ])

    chain = prompt | llm_with_tools

    def crypto_analyst_node(state):
        result = chain.invoke(state)
        report = result.content if hasattr(result, "content") else str(result)
        return {
            "messages": [result],
            "market_report": report,
        }

    return crypto_analyst_node
