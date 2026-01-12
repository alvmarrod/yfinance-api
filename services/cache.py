"""
Module that implements a thread-safe cache manager
"""
import logging

import threading as tg
from typing import Optional
from datetime import datetime, timedelta

from services.cache_entry import CacheEntry
from services.full_ticker_data import FullTickerData

from utils.progressbar import create_progress_bar

app_logger = logging.getLogger('yfinance-api')

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

CACHE_DIR: str = "cache"
MAX_MEM_CACHE_SIZE: int = 225

CACHE_SIZE_LOG_MSG: str = "📊 Cache usage: %s"

##############################################################################
#                                AUX FUNCTIONS                               #
##############################################################################

def _cache_has_expired(entry: CacheEntry) -> Optional[CacheEntry]:
    """Returns the very same CacheEntry if it has not expired.

    Logs accordingly."""
    if entry.retrieval_time - datetime.now() > timedelta(hours=1):
        app_logger.info(f"⏳ Cache entry for {entry.ticker} has expired.")
        return None
    else:
        return entry

def _get_oldest_ticker(entries: list[CacheEntry]) -> str:
    """Returns the ticker of the oldest entry"""
    sorted_entries: list[CacheEntry] = sorted(entries, key=lambda x: x.retrieval_time)

    app_logger.info("Returning the oldest ticker %s vs newest %s" % (
        sorted_entries[0].retrieval_time,
        sorted_entries[-1].retrieval_time
    ))

    return sorted_entries[0].ticker

##############################################################################
#                                    CACHE                                   #
##############################################################################

class tsCache:
    """Thread-safe cache"""

    lock: tg.Lock
    cache: dict[str, CacheEntry]

    def __init__(self):
        app_logger.info("🆕 Initializating the cache")
        self.lock = tg.Lock()
        self.cache = {}

    def _cache_usage_report(self) -> None:
        """Reports the current status of the cache usage"""
        report_msg: str = CACHE_SIZE_LOG_MSG % create_progress_bar(
            current=len(self.cache),
            total=MAX_MEM_CACHE_SIZE,
            width=10
        )

        app_logger.info(report_msg)

    def get_ticker(self, ticker: str) -> Optional[FullTickerData]:
        """Thread-safely return a ticker if it exists in the cache.
        """
        result: Optional[FullTickerData] = None
        cache_result: Optional[CacheEntry] = None

        self.lock.acquire()
        cache_result = self.cache.get(ticker, None)

        if cache_result:
            cache_result = _cache_has_expired(cache_result)

            if cache_result:
                result = cache_result.data

            else:
                app_logger.info(f"🔥 Removed expired cache entry in memory")
                del self.cache[ticker]
        
        self.lock.release()
        return result
    
    def add_ticker(self, ticker: str, data: FullTickerData):
        """Thread-safely adds a ticker to the cache"""
        self.lock.acquire()

        if len(self.cache) > MAX_MEM_CACHE_SIZE:
            oldest_ticker: str = _get_oldest_ticker(list(self.cache.values()))
            del self.cache[oldest_ticker]

        self.cache[ticker] = CacheEntry(
            ticker=ticker,
            retrieval_time=datetime.now(),
            data=data
        )

        self._cache_usage_report()

        self.lock.release()
