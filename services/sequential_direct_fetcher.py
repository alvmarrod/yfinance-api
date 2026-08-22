"""
Sequential direct fetcher for custom date-range ticker requests.

This module bypasses the cache/job dispatcher and fetches ticker data directly
from yfinance. Requests are serialized and a cooldown is enforced between
them to avoid hitting rate limits.
"""

import logging
import threading
import time
from datetime import datetime

import yfinance as yf

from services.full_ticker_data import FullTickerData
from services.pending_ticker import SECTIONS_MAP

app_logger = logging.getLogger("yfinance-api")

_DIRECT_FETCH_LOCK = threading.Lock()
_LAST_DIRECT_FETCH_DONE: float = 0.0
_COOLDOWN_SECONDS = 5.0


def fetch_ticker_for_range(ticker: str, start: str, end: str) -> FullTickerData:
    """
    Fetch all ticker sections directly from yfinance with a custom history range.

    Requests are serialized through a global lock. A cooldown is enforced
    between the end of the previous request and the start of the current one.
    """
    global _LAST_DIRECT_FETCH_DONE

    with _DIRECT_FETCH_LOCK:
        elapsed = time.time() - _LAST_DIRECT_FETCH_DONE
        if elapsed < _COOLDOWN_SECONDS:
            sleep_time = _COOLDOWN_SECONDS - elapsed
            app_logger.debug(
                "Direct-fetch cooldown: sleeping %.1fs for %s", sleep_time, ticker
            )
            time.sleep(sleep_time)

        try:
            return _fetch_all_sections(ticker, start, end)
        finally:
            _LAST_DIRECT_FETCH_DONE = time.time()


def _fetch_all_sections(ticker: str, start: str, end: str) -> FullTickerData:
    """Fetch all sections for a ticker, overriding history with a date range."""
    yf_ticker = yf.Ticker(ticker)
    result = FullTickerData(ticker=ticker)
    now = datetime.now()

    for section, fetcher in SECTIONS_MAP.items():
        try:
            if section == "history":
                data = yf_ticker.history(start=start, end=end)
            else:
                data = fetcher(yf_ticker)
            setattr(result, section, data)
            setattr(result, f"{section}_retrieval_time", now)
        except Exception as e:
            app_logger.debug("Failed to fetch %s for %s: %s", section, ticker, e)

    return result
