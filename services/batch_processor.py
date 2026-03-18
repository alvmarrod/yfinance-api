"""
Batch processor for parallel fetching and result distribution.
"""

import logging
import threading as tg

import yfinance as yf

from services.cache import tsCache
from services.full_ticker_data import FullTickerData
from services.rate_limiter import tsRateLimiter
from services.request_bucket import RequestBucket

app_logger = logging.getLogger("yfinance-api")

BATCH_THREAD_COUNT: int = 10

SECONDS_SLEEP_WHEN_RATE_HIT: float = 1.0


def _fetch_sections_for_ticker(
    ticker: str,
    sections: set[str],
    rate_limiter: tsRateLimiter,
) -> FullTickerData:
    """Fetch specific sections for a ticker, respecting rate limits."""
    while not rate_limiter.ratio_allows():
        app_logger.debug(
            f"Rate limited, waiting before fetching {sections} for {ticker}"
        )
        tg.Event().wait(SECONDS_SLEEP_WHEN_RATE_HIT)

    yf_ticker = yf.Ticker(ticker)
    result = FullTickerData(ticker=ticker)

    section_map = {
        "info": lambda: yf_ticker.info,
        "financials": lambda: yf_ticker.financials,
        "balance_sheet": lambda: yf_ticker.balance_sheet,
        "cashflow": lambda: yf_ticker.cashflow,
        "history": lambda: yf_ticker.history(period="1y"),
        "dividends": lambda: yf_ticker.dividends,
        "quarterly_income_stmt": lambda: yf_ticker.quarterly_income_stmt,
        "quarterly_balance_sheet": lambda: yf_ticker.quarterly_balance_sheet,
    }

    for section in sections:
        try:
            data = section_map.get(section, lambda: None)()
            setattr(result, section, data)
        except Exception as e:
            app_logger.debug(f"Failed to fetch {section} for {ticker}: {e}")

    return result


class BatchProcessor:
    """Processes batches of requests concurrently."""

    def __init__(self, cache: tsCache, rate_limiter: tsRateLimiter):
        self.cache = cache
        self.rate_limiter = rate_limiter

    def process_bucket(self, bucket: RequestBucket) -> None:
        """Process all unique tickers in bucket concurrently."""
        ticker_sections = bucket.get_unique_tickers()

        app_logger.info(
            f"📦 Processing bucket: {len(ticker_sections)} unique tickers, "
            f"{sum(len(reqs) for reqs in bucket.ticker_map.values())} total requests"
        )

        threads = []
        for ticker, sections in ticker_sections.items():
            t = tg.Thread(
                target=self._fetch_and_distribute,
                args=(ticker, sections, bucket.ticker_map[ticker]),
            )
            threads.append(t)
            t.start()

            if len(threads) >= BATCH_THREAD_COUNT:
                for thread in threads:
                    thread.join()
                threads = []

        for thread in threads:
            thread.join()

    def _fetch_and_distribute(
        self,
        ticker: str,
        sections: set[str],
        requests: list,
    ):
        """Fetch data once, distribute to all waiting requesters."""
        try:
            app_logger.info(f"🌐 Fetching {sections} for {ticker}")

            result = _fetch_sections_for_ticker(ticker, sections, self.rate_limiter)

            self.cache.add_ticker(ticker, result)
            app_logger.debug(f"✅ Cached data for {ticker} with sections: {sections}")

            for req in requests:
                req.response_holder.set_result(result)

        except Exception as e:
            app_logger.debug(f"Error fetching {ticker}: {e}")
            for req in requests:
                req.response_holder.set_error(e)
