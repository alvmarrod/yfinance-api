"""
Job dispatcher that coordinates cache, queue, and rate limiter.
Implements both workflows from the design document.
"""
import time
import logging
import threading as tg
from typing import Optional

from services.cache import tsCache
from services.queue import tsQueue
from services.rate_limiter import tsRateLimiter
from services.full_ticker_data import FullTickerData

import yfinance as yf

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

# Considering delays and retries
MAX_SECONDS_PER_REQUEST: float = 180

# We don't sleep too much, to avoid reaching MAX_SECONDS_PER_REQUEST
SECONDS_SLEEP_WHEN_RATE_HIT: float = 2

MAX_RETRIES_PER_REQUEST: int = 3

##############################################################################
#                             PRIVATE FUNCTIONS                              #
##############################################################################

def _fetch_ticker_data(ticker: str) -> FullTickerData:
    """
    Internal function to fetch ticker data from yfinance.
    This is the actual function that makes the API call.
    
    Args:
        ticker (str): The stock ticker symbol to retrieve data for.

    Returns:
        FullTickerData: Complete ticker information.
    """
    logging.debug(f"Making yfinance API call for ticker: {ticker}")
    yfinance_ticker: yf.Ticker = yf.Ticker(ticker)

    return FullTickerData(
        info=yfinance_ticker.info,
        financials=yfinance_ticker.financials,
        balance_sheet=yfinance_ticker.balance_sheet,
        cashflow=yfinance_ticker.cashflow,
        dividends=yfinance_ticker.dividends,
        history=yfinance_ticker.history(period="1y"),
        quarterly_income_stmt=yfinance_ticker.quarterly_income_stmt,
        quarterly_balance_sheet=yfinance_ticker.quarterly_balance_sheet
    )

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
            
        logging.info("🆕 Initializing Job Dispatcher")
        
        # Initialize components
        self.cache = tsCache()
        self.queue = tsQueue()
        self.rate_limiter = tsRateLimiter()
        
        # Worker thread control
        self._worker_thread: Optional[tg.Thread] = None
        self._shutdown_event = tg.Event()
        
        self._initialized = True
    
    def start_worker(self) -> None:
        """Start the background worker thread (Workflow 2)."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            logging.info("🚀 Starting worker thread")
            self._shutdown_event.clear()
            self._worker_thread = tg.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
    
    def stop_worker(self) -> None:
        """Stop the background worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            logging.info("✋ Stopping worker thread")
            self._shutdown_event.set()
            self._worker_thread.join(timeout=5.0)
    
    def get_ticker_data(self, ticker: str) -> Optional[FullTickerData]:
        """
        Workflow 1: Request receiver (main thread).
        
        1. Check cache first
        2. If not cached, queue the request
        3. Wait for worker to process it
        """
        logging.debug(f"📥 Received request for ticker: {ticker}")
        
        # Step 1: Check cache first
        cached_data = self.cache.get_ticker(ticker)
        if cached_data:
            logging.debug(f"🎯 Cache hit for ticker: {ticker}")
            return cached_data
        
        # Step 2: Not in cache, queue the request
        logging.debug(f"📤 Cache miss, queuing request for ticker: {ticker}")
        queued_request = self.queue.add_job(ticker)
        
        # Step 3: Wait for worker to process it
        if queued_request.wait_for_result(timeout=MAX_SECONDS_PER_REQUEST):
            if queued_request.error:
                raise queued_request.error
            return queued_request.result
        else:
            raise TimeoutError(f"⌛ Request timeout for ticker: {ticker}")
    
    def _worker_loop(self) -> None:
        """
        Workflow 2: Background worker thread.
        
        Continuously processes queued requests with rate limiting.
        """
        logging.info("👷 Worker thread started")
        
        while not self._shutdown_event.is_set():
            try:
                # Step 1: Check if anything is in the queue
                job = self.queue.get_job()
                
                if not job:
                    # Step 1.1: If nothing in queue, sleep 1s
                    time.sleep(1)
                    continue
                
                logging.debug(f"👷 Processing job for ticker: {job.ticker}")
                
                # Step 2: Check rate limiting
                retry_count = 0
                
                while retry_count < MAX_RETRIES_PER_REQUEST:
                    try:
                        # Step 2.1: Check if rate allows us to proceed
                        while not self.rate_limiter.ratio_allows():
                            logging.debug(f"⏳ Rate limit hit, sleeping {SECONDS_SLEEP_WHEN_RATE_HIT}s")
                            time.sleep(SECONDS_SLEEP_WHEN_RATE_HIT)
                            
                            # Check for shutdown during rate limit wait
                            if self._shutdown_event.is_set():
                                job.set_error(Exception("⛔ Worker shutdown during rate limit wait"))
                                break
                        
                        if self._shutdown_event.is_set():
                            break
                        
                        # Step 3: Make the API call
                        logging.debug(f"🌐 Making API call for ticker: {job.ticker}")
                        result = _fetch_ticker_data(job.ticker)
                        
                        # Step 4: Cache the result and notify requester
                        self.cache.add_ticker(job.ticker, result)
                        job.set_result(result)
                        logging.debug(f"✅ Successfully processed ticker: {job.ticker}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        retry_count += 1
                        if retry_count < MAX_RETRIES_PER_REQUEST:
                            logging.warning(f"⚠️ Error processing {job.ticker} (attempt {retry_count}/{MAX_RETRIES_PER_REQUEST}): {e}")
                            time.sleep(20)  # Sleep 20s before retry as per design
                        else:
                            logging.error(f"❌ Failed to process {job.ticker} after {MAX_RETRIES_PER_REQUEST} attempts: {e}")
                            job.set_error(e)
                            break
                            
            except Exception as e:
                logging.error(f"❌ Unexpected error in worker thread: {e}")
                time.sleep(1)  # Prevent tight loop on persistent errors
        
        logging.info("👷 Worker thread stopped")

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
