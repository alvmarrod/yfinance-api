"""
Job dispatcher that coordinates cache, queue, and rate limiter.
Implements both workflows from the design document.
"""

import time
import logging
import threading as tg
from datetime import timedelta, datetime
from typing import Optional, Any, Callable

from services.cache import tsCache
from services.rate_limiter import tsRateLimiter
from services.queue import tsQueue, QueuedRequest
from services.full_ticker_data import FullTickerData
from services.calculations import try_calculate_field
from services.pending_ticker import PendingTicker

app_logger = logging.getLogger("yfinance_api")

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

MAX_SECONDS_PER_REQUEST: float = 300

SECONDS_SLEEP_WHEN_RATE_HIT: float = 1

MAX_RETRIES_PER_REQUEST: int = 3
WAIT_TIME_SECONDS_AFTER_API_ERROR: int = 5

ALL_SECTIONS: set[str] = {
    "info",
    "financials",
    "balance_sheet",
    "cashflow",
    "dividends",
    "history",
    "quarterly_income_stmt",
    "quarterly_balance_sheet",
}

##############################################################################
#                             PRIVATE FUNCTIONS                              #
##############################################################################


def check_rate_limit_exceptions(
    rate_limiter: tsRateLimiter,
) -> tuple[Callable, Callable]:
    """
    Wraps exception checking for rate limit hits.
    """
    consecutive_408_errors: int = 0

    def check_rate_limit_exception(excp: Exception) -> None:
        """
        Checks if the exception is a rate limit hit and notifies the rate limiter.
        """
        nonlocal consecutive_408_errors
        error_str: str = str(excp).lower()

        if "408" in str(excp) or "rate" in error_str or "limit" in error_str:
            consecutive_408_errors += 1
            app_logger.warning(
                f"🚨 Detected potential rate limit error #{consecutive_408_errors}: {excp}"
            )

            if consecutive_408_errors >= 2:
                app_logger.error(
                    "🚨 Multiple rate limit errors detected - reporting to rate limiter"
                )
                rate_limiter.yfinance_api_report_rate_limit_hit()

                while rate_limiter.ratio_allows() is False:
                    app_logger.info(
                        f"⏳ Waiting for rate limiter cooldown ({SECONDS_SLEEP_WHEN_RATE_HIT}s sleep)"
                    )
                    time.sleep(SECONDS_SLEEP_WHEN_RATE_HIT)

        else:
            consecutive_408_errors = 0

    def reset_consecutive_errors() -> None:
        """Reset the consecutive error counter on success."""
        nonlocal consecutive_408_errors
        consecutive_408_errors = 0

    return check_rate_limit_exception, reset_consecutive_errors


##############################################################################
#                              JOB DISPATCHER                               #
##############################################################################


class JobDispatcher:
    """
    Coordinates cache, queue, and rate limiter to implement the job dispatcher workflows.
    This is a singleton that manages both the request receiver and PendingTicker processing.
    """

    _instance: Optional["JobDispatcher"] = None
    _lock: tg.Lock = tg.Lock()

    cache: tsCache
    queue: tsQueue
    rate_limiter: tsRateLimiter

    _rate_limit_checker: Callable
    _rate_limit_reset: Callable

    _worker_thread: Optional[tg.Thread]
    _shutdown_event: tg.Event

    _pending_tickers: dict[str, PendingTicker]
    _pending_lock: tg.Lock
    _fetching_lock: tg.Lock

    def __new__(cls) -> "JobDispatcher":
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        app_logger.info("🆕 Initializing Job Dispatcher")

        self.cache = tsCache()
        self.queue = tsQueue()
        self.rate_limiter = tsRateLimiter()

        self._worker_thread: Optional[tg.Thread] = None
        self._shutdown_event = tg.Event()

        self._rate_limit_checker, self._rate_limit_reset = check_rate_limit_exceptions(
            self.rate_limiter
        )

        self._pending_tickers = {}
        self._pending_lock = tg.Lock()
        self._fetching_lock = tg.Lock()

        self._initialized = True

    def _process_cache_ready_job(self, job: QueuedRequest) -> None:
        """Process a job that can be served entirely from cache."""
        try:
            cached_data: Optional[FullTickerData] = self.cache.get_ticker(job.ticker)
            if cached_data and cached_data.has_required_sections(job.sections):
                job.set_result(cached_data)
                app_logger.debug(f"🚀 Fast-serving cached job for {job.ticker}")
            else:
                self.queue.add_job(job.ticker, job.sections)
                app_logger.debug(f"🔄 Cache miss for {job.ticker} - re-queued")
                job.set_error(
                    Exception("Cache state changed, re-queued as new request")
                )
        except Exception as e:
            app_logger.error(f"❌ Error processing cache-ready job: {e}")
            job.set_error(e)

    def _process_api_job(self, job: QueuedRequest) -> None:
        """Process a job that requires API calls."""
        for retry_count in range(MAX_RETRIES_PER_REQUEST):
            if self._shutdown_event.is_set():
                return

            if (
                job.timestamp + timedelta(seconds=MAX_SECONDS_PER_REQUEST)
                < datetime.now()
            ):
                app_logger.error(f"⏱️ Job for {job.ticker} timed out")
                job.set_error(TimeoutError(f"Job for {job.ticker} timed out in queue"))
                return

            try:
                app_logger.debug(f"🌐 Making API call for: {job.ticker}")

                from services.pending_ticker import fetch_sections_for_ticker

                result = fetch_sections_for_ticker(
                    job.ticker,
                    job.sections,
                    self.rate_limiter,
                    self._fetching_lock,
                )

                self.cache.add_ticker(job.ticker, result)
                job.set_result(result)
                app_logger.debug(f"✅ Successfully processed: {job.ticker}")
                return

            except Exception as e:
                if retry_count < MAX_RETRIES_PER_REQUEST - 1:
                    app_logger.warning(
                        f"⚠️ Error processing {job.ticker} (attempt {retry_count + 1}): {e}"
                    )
                    time.sleep(WAIT_TIME_SECONDS_AFTER_API_ERROR)
                else:
                    app_logger.error(
                        f"❌ Failed {job.ticker} after {MAX_RETRIES_PER_REQUEST} attempts: {e}"
                    )
                    job.set_error(e)

    def _worker_loop(self) -> None:
        """
        Background worker thread for queue-based processing.
        """
        app_logger.info("👷 Worker thread started")

        while not self._shutdown_event.is_set():
            time.sleep(0.01)

            try:
                cache_ready_job = self.queue.get_cache_ready_job(self.cache)
                if cache_ready_job:
                    self._process_cache_ready_job(cache_ready_job)
                    continue

                job: Optional[QueuedRequest] = self.queue.get_job()
                if not job:
                    time.sleep(1)
                    continue

                app_logger.debug(f"👷 Processing job for: {job.ticker}")

                if not self.rate_limiter.ratio_allows():
                    self.queue.put_job_back(job)
                    app_logger.debug("⏳ Rate limited - will retry")
                    continue

                self._process_api_job(job)

            except Exception as e:
                app_logger.error(f"❌ Unexpected error in worker: {e}")
                time.sleep(1)

        app_logger.info("👷 Worker thread stopped")

    def _fetch_sections(self, ticker: str, sections: set[str]) -> FullTickerData:
        """
        Fetch specific sections via PendingTicker windowing.
        """
        cached_data: Optional[FullTickerData] = self.cache.get_ticker(ticker)

        if cached_data:
            cached_sections = {
                k
                for k, v in cached_data.__dict__.items()
                if v is not None and k != "ticker"
            }
            missing_sections = sections - cached_sections
            app_logger.debug(
                f"Cache hit for {ticker}: have {cached_sections}, need {sections}, "
                f"missing {missing_sections}"
            )
        else:
            missing_sections = sections
            app_logger.debug(f"Cache miss for {ticker}, need {sections}")

        if cached_data and not missing_sections:
            app_logger.debug(f"Returning cached data for {ticker}")
            return cached_data

        holder = QueuedRequest(
            ticker=ticker,
            sections=sections,
            timestamp=datetime.now(),
            result_event=tg.Event(),
        )

        with self._pending_lock:
            if ticker in self._pending_tickers:
                self._pending_tickers[ticker].add_request(missing_sections, holder)
                app_logger.debug(
                    f"Added request to existing PendingTicker for {ticker}"
                )
            else:
                pt = PendingTicker(
                    ticker=ticker,
                    cache=self.cache,
                    rate_limiter=self.rate_limiter,
                    fetching_lock=self._fetching_lock,
                )
                pt.add_request(missing_sections, holder)
                self._pending_tickers[ticker] = pt
                app_logger.debug(f"Created new PendingTicker for {ticker}")

        if holder.wait_for_result(timeout=MAX_SECONDS_PER_REQUEST):
            if holder.error:
                raise holder.error
            if holder.result is None:
                raise Exception(f"Unknown error fetching {sections} for {ticker}")

            with self._pending_lock:
                if ticker in self._pending_tickers:
                    del self._pending_tickers[ticker]

            return holder.result
        else:
            with self._pending_lock:
                if ticker in self._pending_tickers:
                    del self._pending_tickers[ticker]

            raise TimeoutError(f"Timeout fetching {sections} for {ticker}")

    def start_worker(self) -> None:
        """Start the background worker thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            app_logger.info("🚀 Starting worker thread")
            self._shutdown_event.clear()
            self._worker_thread = tg.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def stop_worker(self) -> None:
        """Stop the background worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            app_logger.info("✋ Stopping worker thread")
            self._shutdown_event.set()
            self._worker_thread.join(timeout=5.0)

    ##########################################################################
    #                          PUBLIC API METHODS                            #
    ##########################################################################

    def get_field_value(self, ticker: str, field_name: str) -> Any:
        """Smart field retrieval with automatic data fetching."""
        cached_data: Optional[FullTickerData] = self.cache.get_ticker(ticker)
        if not cached_data:
            cached_data = self._fetch_sections(ticker, {"info"})

        max_retries = 3
        for attempt in range(max_retries):
            success, value, missing_sections = try_calculate_field(
                field_name, cached_data
            )

            if success:
                return value

            if missing_sections is None:
                raise Exception(f"Failed to calculate {field_name}: unknown error")

            app_logger.debug(f"🔍 Field {field_name} needs: {missing_sections}")
            updated_data = self._fetch_sections(ticker, missing_sections)
            cached_data.update_with_data(updated_data)
            self.cache.add_ticker(ticker, cached_data)

        raise Exception(
            f"Failed to calculate {field_name} after {max_retries} attempts"
        )

    def get_basic_ticker_data(self, ticker: str) -> FullTickerData:
        """Ensure basic info is available."""
        return self._fetch_sections(ticker, {"info"})

    def get_complete_ticker_data(self, ticker: str) -> FullTickerData:
        """Fetch all available data sections."""
        return self._fetch_sections(ticker, ALL_SECTIONS)

    def get_specific_sections(self, ticker: str, sections: set[str]) -> FullTickerData:
        """Fetch specific sections only."""
        return self._fetch_sections(ticker, sections)


##############################################################################
#                              GLOBAL INSTANCE                               #
##############################################################################

_dispatcher: Optional[JobDispatcher] = None


def get_dispatcher() -> JobDispatcher:
    """Get or create the global JobDispatcher singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = JobDispatcher()
        _dispatcher.start_worker()
    return _dispatcher


def shutdown_dispatcher() -> None:
    """Shutdown the global dispatcher and worker thread."""
    global _dispatcher
    if _dispatcher:
        _dispatcher.stop_worker()
        _dispatcher = None
