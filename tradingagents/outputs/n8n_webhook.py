"""
n8n Webhook Output Integration
-------------------------------
Sends TradingAgents signals to an n8n webhook after each analysis run.

Usage in config:
    config = {
        ...
        "n8n_webhook_url": "https://your-n8n-instance.com/webhook/trading-signal",
        "n8n_webhook_include_reports": True,   # optional, default True
        "n8n_webhook_timeout": 10,             # optional, default 10s
    }

The webhook payload sent to n8n:
    {
        "ticker": "AAPL",
        "date": "2026-03-09",
        "signal": "BUY",                  # BUY | SELL | HOLD
        "final_trade_decision": "...",    # Full portfolio manager decision
        "trader_investment_plan": "...",  # Trader's plan
        "investment_plan": "...",         # Research manager's plan
        "market_report": "...",           # Technical analysis
        "sentiment_report": "...",        # Social sentiment
        "news_report": "...",             # News analysis
        "fundamentals_report": "...",     # Fundamental analysis
        "bull_case": "...",               # Bull researcher conclusion
        "bear_case": "...",               # Bear researcher conclusion
        "risk_assessment": "...",         # Risk debate conclusion
        "timestamp": "2026-03-09T21:00:00Z"
    }

Compatible with any n8n Webhook node (HTTP POST, JSON body).
Credit: Based on TradingAgents by TradingAgents Team.
        n8n integration by Aya Chafi (github.com/chafiaya920-del).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib import request, error

logger = logging.getLogger(__name__)


def send_to_n8n(
    webhook_url: str,
    ticker: str,
    trade_date: str,
    signal: str,
    final_state: Dict[str, Any],
    include_reports: bool = True,
    timeout: int = 10,
) -> bool:
    """
    Send a trading signal and analysis to an n8n webhook.

    Args:
        webhook_url:     Full URL of the n8n Webhook node.
        ticker:          Stock ticker symbol (e.g. "AAPL").
        trade_date:      Analysis date string (e.g. "2026-03-09").
        signal:          Extracted signal — "BUY", "SELL", or "HOLD".
        final_state:     The full state dict returned by TradingAgentsGraph.propagate().
        include_reports: Whether to include full analyst reports in the payload.
        timeout:         HTTP request timeout in seconds.

    Returns:
        True if the webhook was called successfully (HTTP 2xx), False otherwise.
    """
    payload: Dict[str, Any] = {
        "ticker": ticker,
        "date": str(trade_date),
        "signal": signal,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_trade_decision": final_state.get("final_trade_decision", ""),
        "trader_investment_plan": final_state.get("trader_investment_plan", ""),
        "investment_plan": final_state.get("investment_plan", ""),
    }

    if include_reports:
        payload.update(
            {
                "market_report": final_state.get("market_report", ""),
                "sentiment_report": final_state.get("sentiment_report", ""),
                "news_report": final_state.get("news_report", ""),
                "fundamentals_report": final_state.get("fundamentals_report", ""),
                "bull_case": final_state.get("investment_debate_state", {}).get(
                    "judge_decision", ""
                ),
                "risk_assessment": final_state.get("risk_debate_state", {}).get(
                    "judge_decision", ""
                ),
            }
        )

    try:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=timeout) as response:
            status = response.status
            if 200 <= status < 300:
                logger.info(
                    f"[n8n] Signal '{signal}' for {ticker} sent successfully "
                    f"(HTTP {status})"
                )
                return True
            else:
                logger.warning(
                    f"[n8n] Webhook returned unexpected status {status} for {ticker}"
                )
                return False

    except error.URLError as e:
        logger.error(f"[n8n] Failed to reach webhook at {webhook_url}: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"[n8n] Unexpected error sending webhook: {e}")
        return False
