"""
Rate limiting service for yfinance API calls.
Implements queue-based rate limiting to avoid hitting API limits.
"""
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable
from queue import Queue, Empty
from dataclasses import dataclass
from collections import deque
from datetime import datetime, timedelta


@dataclass
class QueuedRequest:
    """Represents a queued API request."""
    ticker: str
    callback: Callable
    timestamp: datetime
    future_result: threading.Event
    result: Any = None
    error: Optional[Exception] = None


@dataclass 
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests_per_2min: int = 20  # Maximum requests per 2 minutes
    check_interval: float = 2.0      # How often to check queue (seconds)
    cache_expiry_hours: int = 1      # Cache expiry time in hours
    max_retries: int = 3            # Maximum retries for HTTP 500 errors
    retry_delay: float = 5.0        # Delay between retries (seconds)
    retry_backoff_factor: float = 2.0  # Exponential backoff multiplier


class RateLimitedYFinanceService:
    """
    Service that provides rate-limited access to yfinance API.
    Uses a background thread to process requests while respecting rate limits.
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.cache: Dict[str, tuple] = {}  # ticker -> (data, timestamp)
        self.request_queue = Queue()
        self.request_history = deque()  # Track API calls in last 2 minutes
        self.lock = threading.Lock()
        
        # Background thread for processing queue
        self.processor_thread = None
        self.running = False
        self.start_background_processor()
        
        logging.info(
            f"Rate limiter initialized: max {self.config.max_requests_per_2min} "
            f"requests per 2 minutes (instance id: {id(self)})"
        )
    
    def start_background_processor(self):
        """Start the background thread that processes the queue."""
        if self.processor_thread and self.processor_thread.is_alive():
            return
            
        self.running = True
        self.processor_thread = threading.Thread(
            target=self._process_queue_background, 
            daemon=True,
            name="YFinanceRateLimiter"
        )
        self.processor_thread.start()
        logging.info("Background rate limiter thread started")
    
    def stop_background_processor(self):
        """Stop the background processing thread."""
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5.0)
            logging.info("Background rate limiter thread stopped")
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if the error is a retryable HTTP 500 error."""
        error_str = str(error).lower()
        return (
            "500" in error_str or 
            "internal server error" in error_str or
            "server error" in error_str or
            "http 500" in error_str
        )
    
    def _clean_old_requests(self):
        """Remove requests older than 2 minutes from history."""
        # Note: This method should be called with self.lock already held
        cutoff_time = datetime.now() - timedelta(minutes=2)
        while self.request_history and self.request_history[0] < cutoff_time:
            self.request_history.popleft()
    
    def _try_reserve_rate_limit_slot(self) -> bool:
        """
        Atomically check if we can make a request and reserve a slot if possible.
        
        Returns:
            bool: True if slot was reserved, False if rate limit reached
        """
        with self.lock:
            self._clean_old_requests()
            if len(self.request_history) < self.config.max_requests_per_2min:
                # Reserve the slot immediately
                self.request_history.append(datetime.now())
                return True
            return False
    
    def _can_make_request(self) -> bool:
        """Check if we can make a new API request based on rate limits."""
        with self.lock:  # Add thread safety to prevent race conditions
            self._clean_old_requests()
            return len(self.request_history) < self.config.max_requests_per_2min
    
    def _record_request(self):
        """Record that an API request was made."""
        with self.lock:  # Ensure thread-safe recording
            self.request_history.append(datetime.now())
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        expiry = timedelta(hours=self.config.cache_expiry_hours)
        return datetime.now() - timestamp < expiry
    
    def _process_queue_background(self):
        """Background thread function that processes queued requests."""
        logging.info(f"Starting rate limiter background processor (thread: {threading.current_thread().name}, instance: {id(self)})")
        
        while self.running:
            try:
                # Get next request from queue (non-blocking)
                try:
                    request = self.request_queue.get_nowait()
                except Empty:
                    time.sleep(self.config.check_interval)
                    continue
                
                # Atomically check and reserve rate limit slot
                if not self._try_reserve_rate_limit_slot():
                    # Log detailed rate limit information
                    with self.lock:
                        current_requests = len(self.request_history)
                        max_requests = self.config.max_requests_per_2min
                        ratio = current_requests / max_requests if max_requests > 0 else 0
                        
                        logging.info(
                            f"Rate limit reached for {request.ticker}: "
                            f"current={current_requests}, max={max_requests}, "
                            f"ratio={ratio:.2f}, threshold=1.0 "
                            f"(thread: {threading.current_thread().name})"
                        )
                    
                    # Put request back at front of queue and wait
                    temp_queue = Queue()
                    temp_queue.put(request)
                    
                    # Move other items to temp queue
                    while not self.request_queue.empty():
                        try:
                            temp_queue.put(self.request_queue.get_nowait())
                        except Empty:
                            break
                    
                    # Restore queue order
                    self.request_queue = temp_queue
                    
                    logging.debug(f"Rate limit active, waiting {self.config.check_interval * 2}s...")
                    time.sleep(self.config.check_interval * 2)  # Wait longer when rate limited
                    continue
                
                # Rate limit slot successfully reserved
                logging.debug(f"Rate limit slot reserved for {request.ticker}")
                
                # Process the request with retry logic
                retry_count = 0
                max_retries = self.config.max_retries
                retry_delay = self.config.retry_delay
                request_recorded = True  # Flag to track if we've recorded this request
                
                while retry_count <= max_retries:
                    try:
                        if retry_count > 0:
                            logging.info(
                                f"Retrying ticker request: {request.ticker} "
                                f"(attempt {retry_count + 1}/{max_retries + 1})"
                            )
                        else:
                            logging.debug(f"Processing ticker request: {request.ticker}")
                        
                        # Execute the callback function (actual yfinance call)
                        result = request.callback(request.ticker)
                        
                        # Store result and notify waiting thread
                        with self.lock:
                            request.result = result
                            # Cache the result
                            self.cache[request.ticker] = (result, datetime.now())
                        
                        request.future_result.set()
                        logging.debug(f"Successfully processed and cached: {request.ticker}")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if self._is_retryable_error(e) and retry_count < max_retries:
                            # HTTP 500 error, retry after delay
                            current_delay = retry_delay * (self.config.retry_backoff_factor ** retry_count)
                            logging.warning(
                                f"HTTP 500 error for {request.ticker}: {e}. "
                                f"Retrying in {current_delay:.1f}s "
                                f"(attempt {retry_count + 1}/{max_retries + 1})"
                            )
                            retry_count += 1
                            time.sleep(current_delay)
                            # Don't record another request for retries - we already reserved the slot
                            continue
                        else:
                            # Non-retryable error or max retries exceeded
                            if retry_count >= max_retries:
                                logging.error(
                                    f"Max retries ({max_retries}) exceeded for {request.ticker}: {e}"
                                )
                            else:
                                logging.error(
                                    f"Non-retryable error for {request.ticker}: {e}"
                                )
                            request.error = e
                            request.future_result.set()
                            break
                
                # Mark task as done
                self.request_queue.task_done()
                
                # Small delay between requests
                time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Error in background processor: {e}")
                time.sleep(self.config.check_interval)
    
    def get_data(self, ticker: str, fetch_function: Callable, timeout: float = 30.0) -> Any:
        """
        Get data for a ticker, either from cache or by queuing a request.
        
        OPTIMIZATION: Cache hits bypass rate limiting entirely since no yfinance API call is made.
        
        Args:
            ticker: The ticker symbol
            fetch_function: Function that fetches the data (takes ticker as argument)
            timeout: Maximum time to wait for result (seconds)
            
        Returns:
            The ticker data
            
        Raises:
            TimeoutError: If request times out
            Exception: If there was an error fetching the data
        """
        # FIRST PRIORITY: Check cache before doing anything else
        # Cache hits don't count against rate limits since no API call is made
        with self.lock:
            if ticker in self.cache:
                data, timestamp = self.cache[ticker]
                if self._is_cache_valid(timestamp):
                    logging.debug(f"Cache hit for {ticker} - bypassing rate limiter (no API call needed)")
                    return data
                else:
                    # Remove expired cache entry
                    del self.cache[ticker]
                    logging.debug(f"Cache expired for {ticker} - will need fresh API call")
        
        # NOT IN CACHE: Queue the request for rate-limited processing
        logging.debug(f"Cache miss for {ticker} - adding to rate limiter queue")
        request = QueuedRequest(
            ticker=ticker,
            callback=fetch_function,
            timestamp=datetime.now(),
            future_result=threading.Event()
        )
        
        self.request_queue.put(request)
        
        # Wait for result
        if not request.future_result.wait(timeout=timeout):
            raise TimeoutError(f"Timeout waiting for data for ticker: {ticker}")
        
        # Check for errors
        if request.error:
            raise request.error
        
        return request.result
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self.request_queue.qsize()
    
    def get_cache_size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)
    
    def get_request_rate_info(self) -> Dict[str, Any]:
        """Get information about current request rate."""
        with self.lock:
            self._clean_old_requests()
            return {
                "requests_last_2min": len(self.request_history),
                "max_requests_per_2min": self.config.max_requests_per_2min,
                "can_make_request": len(self.request_history) < self.config.max_requests_per_2min,
                "queue_size": self.get_queue_size(),
                "cache_size": self.get_cache_size()
            }


# Global instance and lock for thread-safe singleton
_rate_limiter = None
_rate_limiter_lock = threading.Lock()

def get_rate_limiter(config: RateLimitConfig = None) -> RateLimitedYFinanceService:
    """Get the global rate limiter instance (thread-safe singleton)."""
    global _rate_limiter
    
    # Double-checked locking pattern for thread-safe singleton
    if _rate_limiter is None:
        with _rate_limiter_lock:
            # Check again inside the lock in case another thread created it
            if _rate_limiter is None:
                _rate_limiter = RateLimitedYFinanceService(config)
    
    return _rate_limiter

def cleanup_rate_limiter():
    """Clean up the global rate limiter instance."""
    global _rate_limiter
    with _rate_limiter_lock:
        if _rate_limiter:
            _rate_limiter.stop_background_processor()
            _rate_limiter = None