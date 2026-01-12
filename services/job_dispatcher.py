"""
Job dispatcher that coordinates cache, queue, and rate limiter.
Implements both workflows from the design document.
"""
import time
import logging
import threading as tg
from typing import Optional, Any

from services.cache import tsCache
from services.queue import tsQueue
from services.rate_limiter import tsRateLimiter
from services.full_ticker_data import FullTickerData
from services.calculations import safe_calculate_field

import yfinance as yf

app_logger = logging.getLogger("yfinance_api")

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

# Considering delays and retries
MAX_SECONDS_PER_REQUEST: float = 300

# We don't sleep too much, to avoid reaching MAX_SECONDS_PER_REQUEST
SECONDS_SLEEP_WHEN_RATE_HIT: float = 1

MAX_RETRIES_PER_REQUEST: int = 3

##############################################################################
#                             PRIVATE FUNCTIONS                              #
##############################################################################

def _fetch_specific_sections(ticker: str, sections: set[str]) -> FullTickerData:
    """
    Fetches only specific sections from yfinance.
    """
    app_logger.debug(f"Making granular yfinance API calls for {ticker}: {sections}")
    
    yf_ticker = yf.Ticker(ticker)
    result = FullTickerData(ticker=ticker)
    
    for section in sections:
        try:
            if section == "info":
                result.info = yf_ticker.info
            elif section == "financials":
                result.financials = yf_ticker.financials
            elif section == "balance_sheet":
                result.balance_sheet = yf_ticker.balance_sheet
            elif section == "cashflow":
                result.cashflow = yf_ticker.cashflow
            elif section == "history":
                result.history = yf_ticker.history(period="1y")
            elif section == "dividends":
                result.dividends = yf_ticker.dividends
            elif section == "quarterly_income_stmt":
                result.quarterly_income_stmt = yf_ticker.quarterly_income_stmt
            elif section == "quarterly_balance_sheet":
                result.quarterly_balance_sheet = yf_ticker.quarterly_balance_sheet
            else:
                app_logger.warning(f"Unknown section requested: {section}")
                
        except Exception as e:
            app_logger.warning(f"Failed to fetch {section} for {ticker}: {e}")
    
    return result

##############################################################################
#                              JOB DISPATCHER                               #
##############################################################################

class JobDispatcher:
    """
    Coordinates cache, queue, and rate limiter to implement the job dispatcher workflows.
    This is a singleton that manages both the request receiver (workflow 1) and worker (workflow 2).
    """
    
    # Singleton instance control
    _instance: Optional['JobDispatcher'] = None
    _lock: tg.Lock = tg.Lock()

    # Instance attributes
    cache: tsCache
    queue: tsQueue
    rate_limiter: tsRateLimiter

    _worker_thread: Optional[tg.Thread]
    _shutdown_event: tg.Event
    
    def __new__(cls) -> 'JobDispatcher':
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
            
        app_logger.info("🆕 Initializing Job Dispatcher")
        
        # Initialize components
        self.cache = tsCache()
        self.queue = tsQueue()
        self.rate_limiter = tsRateLimiter()
        
        # Worker thread control
        self._worker_thread: Optional[tg.Thread] = None
        self._shutdown_event = tg.Event()
        
        self._initialized = True
    
    def _worker_loop(self) -> None:
        """
        Workflow 2: Background worker thread.
        
        Continuously processes queued requests with rate limiting.
        """
        app_logger.info("👷 Worker thread started")
        
        while not self._shutdown_event.is_set():
            try:
                # Step 1: Check if anything is in the queue
                job = self.queue.get_job()
                
                if not job:
                    # Step 1.1: If nothing in queue, sleep 1s
                    time.sleep(1)
                    continue
                
                app_logger.debug(f"👷 Processing job for ticker: {job.ticker}")
                
                # Step 2: Check rate limiting
                retry_count = 0
                
                while retry_count < MAX_RETRIES_PER_REQUEST:
                    try:
                        # Step 2.1: Check if rate allows us to proceed
                        while not self.rate_limiter.ratio_allows():
                            app_logger.debug(f"⏳ Rate limit hit, sleeping {SECONDS_SLEEP_WHEN_RATE_HIT}s")
                            time.sleep(SECONDS_SLEEP_WHEN_RATE_HIT)
                            
                            # Check for shutdown during rate limit wait
                            if self._shutdown_event.is_set():
                                job.set_error(Exception("⛔ Worker shutdown during rate limit wait"))
                                break
                        
                        if self._shutdown_event.is_set():
                            break
                        
                        # Step 3: Make the API call
                        app_logger.debug(f"🌐 Making API call for ticker: {job.ticker}")
                        result = _fetch_specific_sections(job.ticker, job.sections)
                        
                        # Step 4: Cache the result and notify requester
                        self.cache.add_ticker(job.ticker, result)
                        job.set_result(result)
                        app_logger.debug(f"✅ Successfully processed ticker: {job.ticker}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count < MAX_RETRIES_PER_REQUEST:
                            app_logger.warning(f"⚠️ Error processing {job.ticker} (attempt {retry_count}/{MAX_RETRIES_PER_REQUEST}): {e}")
                            time.sleep(20)  # Sleep 20s before retry as per design
                        else:
                            app_logger.error(f"❌ Failed to process {job.ticker} after {MAX_RETRIES_PER_REQUEST} attempts: {e}")
                            job.set_error(e)
                            break
                            
            except Exception as e:
                app_logger.error(f"❌ Unexpected error in worker thread: {e}")
                time.sleep(1)  # Prevent tight loop on persistent errors
        
        app_logger.info("👷 Worker thread stopped")

    def _get_or_create_minimal_data(self, ticker: str) -> FullTickerData:
        """
        Get cached data or create minimal structure with basic info.
        """
        cached_data = self.cache.get_ticker(ticker)
        if cached_data:
            return cached_data
            
        # Start with just basic info
        return self.get_basic_ticker_data(ticker)
    
    def _fetch_sections(self, ticker: str, sections: set[str]) -> FullTickerData:
        """
        Internal method to fetch specific sections via queue.
        """
        # Check what's already cached
        cached_data = self.cache.get_ticker(ticker) or FullTickerData(ticker=ticker)
        missing_sections = sections - set([section for section in cached_data.__dict__.keys() if cached_data.__dict__[section] is not None])
        
        if not missing_sections:
            return cached_data
            
        # Queue request for missing sections
        request = self.queue.add_job(ticker, sections=missing_sections)
        
        if request.wait_for_result(timeout=MAX_SECONDS_PER_REQUEST):
            if request.error or request.result is None:
                if request.error:
                    raise request.error
                else:
                    raise Exception(f"⁉️ Unknown error fetching {missing_sections} for {ticker}")
            return request.result
        else:
            raise TimeoutError(f"Timeout fetching {missing_sections} for {ticker}")

    def start_worker(self) -> None:
        """Start the background worker thread (Workflow 2)."""
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

    def get_field_value(self, ticker: str, field_name: str) -> Any:
        """
        Smart field retrieval with automatic data fetching.
        """
        # 1. Get minimal cached data (start with basic if nothing cached)
        cached_data = self._get_or_create_minimal_data(ticker)
        
        # 2. Try calculation with exception-driven loading
        return safe_calculate_field(field_name, cached_data, self)

    def get_basic_ticker_data(self, ticker: str) -> FullTickerData:
        """
        Ensure basic info is available.
        """
        cached_data = self.cache.get_ticker(ticker)
        if cached_data and cached_data.info is not None:
            return cached_data
            
        # Fetch just basic info
        return self._fetch_sections(ticker, {"info"})

    def get_complete_ticker_data(self, ticker: str) -> FullTickerData:
        """
        Fetch all available data sections.
        """
        all_sections = {"info", "financials", "balance_sheet", "cashflow", 
                       "dividends", "history", "quarterly_income_stmt", 
                       "quarterly_balance_sheet"}
        return self._fetch_sections(ticker, all_sections)
    
    def get_specific_sections(self, ticker: str, sections: set[str]) -> FullTickerData:
        """
        Fetch specific sections only.
        """
        return self._fetch_sections(ticker, sections)
    
    def fetch_missing_sections(self, ticker: str, missing_sections: set[str]) -> FullTickerData:
        """
        Called by safe_calculate_field when data is missing.
        """
        return self._fetch_sections(ticker, missing_sections)

##############################################################################
#                              GLOBAL INSTANCE                               #
##############################################################################

# Global singleton instance
_dispatcher: Optional[JobDispatcher] = None

def get_dispatcher() -> JobDispatcher:
    """Get or create the global JobDispatcher singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = JobDispatcher()
        _dispatcher.start_worker()  # Auto-start worker
    return _dispatcher

def shutdown_dispatcher() -> None:
    """Shutdown the global dispatcher and worker thread."""
    global _dispatcher
    if _dispatcher:
        _dispatcher.stop_worker()
        _dispatcher = None
