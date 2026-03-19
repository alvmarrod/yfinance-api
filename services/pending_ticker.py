"""
Pending ticker management for request batching with timer-based windowing.
"""

import logging
import threading as tg
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

import yfinance as yf

from services.queued_request import QueuedRequest
from services.full_ticker_data import FullTickerData
from services.rate_limiter import tsRateLimiter

app_logger = logging.getLogger("yfinance-api")

PENDING_TICKER_WINDOW_SECONDS: float = 20.0
SECONDS_SLEEP_WHEN_RATE_HIT: float = 1.0

SECTIONS_MAP = {
    "info": lambda t: t.info,
    "financials": lambda t: t.financials,
    "balance_sheet": lambda t: t.balance_sheet,
    "cashflow": lambda t: t.cashflow,
    "history": lambda t: t.history(period="1y"),
    "dividends": lambda t: t.dividends,
    "quarterly_income_stmt": lambda t: t.quarterly_income_stmt,
    "quarterly_balance_sheet": lambda t: t.quarterly_balance_sheet,
}


@dataclass
class TickerWaitingRequest:
    """A request waiting for its ticker's data to be fetched."""

    sections: set[str]
    response_holder: Optional[QueuedRequest]


class PendingTicker:
    """
    Manages multiple waiting requests for the same ticker.
    Has a timer that restarts when new sections are requested.
    """

    ticker: str
    waiting_requests: list[TickerWaitingRequest]
    created_at: datetime
    _timer: Optional[tg.Timer]
    _lock: tg.Lock
    _rate_limiter: tsRateLimiter
    _fetching_lock: tg.Lock
    _cache: Any

    def __init__(
        self,
        ticker: str,
        cache,
        rate_limiter: tsRateLimiter,
        fetching_lock: tg.Lock,
    ):
        self.ticker = ticker
        self.waiting_requests = []
        self.created_at = datetime.now()
        self._timer = None
        self._lock = tg.Lock()
        self._cache = cache
        self._rate_limiter = rate_limiter
        self._fetching_lock = fetching_lock

    def add_request(self, sections: set[str], holder: QueuedRequest) -> bool:
        """
        Add a request to this pending ticker.

        Returns True if new sections were added (timer should restart).
        Returns False if duplicate sections (no timer restart).
        """
        with self._lock:
            existing_sections: set[str] = set()
            for req in self.waiting_requests:
                existing_sections.update(req.sections)

            new_sections = sections - existing_sections

            self.waiting_requests.append(TickerWaitingRequest(sections, holder))

            if new_sections:
                self._restart_timer()

            return bool(new_sections)

    def _restart_timer(self) -> None:
        """Cancel existing timer and start a new window timer."""
        if self._timer:
            self._timer.cancel()

        self._timer = tg.Timer(PENDING_TICKER_WINDOW_SECONDS, self._flush)
        self._timer.start()
        app_logger.info(
            f"🆕 PendingTicker created for {self.ticker}, window: {PENDING_TICKER_WINDOW_SECONDS}s"
        )

    def _flush(self) -> None:
        """Fetch data once and respond to all waiting requests."""
        all_sections: set[str] = set()
        for req in self.waiting_requests:
            all_sections.update(req.sections)

        app_logger.info(
            f"📦 PendingTicker flush for {self.ticker}: {len(self.waiting_requests)} "
            f"requests, sections: {all_sections}"
        )

        try:
            result = self._fetch_data(all_sections)
            self._cache.add_ticker(self.ticker, result)

            for req in self.waiting_requests:
                if req.response_holder:
                    req.response_holder.set_result(result)

        except Exception as e:
            app_logger.debug(f"Error fetching {self.ticker}: {e}")
            for req in self.waiting_requests:
                if req.response_holder:
                    req.response_holder.set_error(e)

    def _fetch_data(self, sections: set[str]) -> FullTickerData:
        """Fetch data with rate limiting and serial fetch control."""
        with self._fetching_lock:
            while not self._rate_limiter.ratio_allows():
                app_logger.info(
                    f"⏳ Rate limited, waiting before fetching {sections} for {self.ticker}"
                )
                time.sleep(SECONDS_SLEEP_WHEN_RATE_HIT)

            app_logger.info(f"🌐 Fetching {sections} for {self.ticker}")

            yf_ticker = yf.Ticker(self.ticker)
            result = FullTickerData(ticker=self.ticker)

            for section in sections:
                try:
                    fetcher = SECTIONS_MAP.get(section)
                    if fetcher:
                        data = fetcher(yf_ticker)
                        setattr(result, section, data)
                except Exception as e:
                    app_logger.debug(
                        f"Failed to fetch {section} for {self.ticker}: {e}"
                    )

            return result


def fetch_sections_for_ticker(
    ticker: str,
    sections: set[str],
    rate_limiter: tsRateLimiter,
    fetching_lock: tg.Lock,
) -> FullTickerData:
    """Fetch specific sections for a ticker with rate limiting."""
    with fetching_lock:
        while not rate_limiter.ratio_allows():
            app_logger.info(
                f"⏳ Rate limited, waiting before fetching {sections} for {ticker}"
            )
            time.sleep(SECONDS_SLEEP_WHEN_RATE_HIT)

        app_logger.info(f"🌐 Fetching {sections} for {ticker}")

        yf_ticker = yf.Ticker(ticker)
        result = FullTickerData(ticker=ticker)

        for section in sections:
            try:
                fetcher = SECTIONS_MAP.get(section)
                if fetcher:
                    data = fetcher(yf_ticker)
                    setattr(result, section, data)
            except Exception as e:
                app_logger.debug(f"Failed to fetch {section} for {ticker}: {e}")

        return result
