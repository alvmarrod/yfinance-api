"""
Business logic for the yfinance wrapper
- Section for ticker data retrieval from yfinance API
"""
from typing import Optional
from dataclasses import dataclass
import logging

import pandas as pd
import yfinance as yf

from services.rate_limiter import get_rate_limiter, RateLimitConfig

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

# Default timeout for incoming HTTP requests waiting in rate limiter queue
# This includes time spent waiting for rate limits + actual yfinance API call
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180.0

@dataclass
class FullTickerData:
    info: dict
    financials: pd.DataFrame
    balance_sheet: pd.DataFrame
    cashflow: pd.DataFrame
    dividends: pd.Series
    history: pd.DataFrame
    quarterly_income_stmt: pd.DataFrame
    quarterly_balance_sheet: pd.DataFrame

##############################################################################
#                                 FUNCTIONS                                  #
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


def get_ticker(ticker: str, timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS) -> FullTickerData:
    """
    Retrieves a yfinance Ticker object for the given ticker symbol.
    Uses rate limiting and caching to avoid hitting API limits.

    Args:
        ticker (str): The stock ticker symbol to retrieve data for.
        timeout (float): Maximum time to wait for result in seconds, including 
                        time spent waiting in rate limiter queue.

    Returns:
        FullTickerData: A dataclass containing complete stock information.
        
    Raises:
        TimeoutError: If the request times out waiting in queue or processing
        Exception: If there's an error fetching the data
    """
    rate_limiter = get_rate_limiter()
    
    return rate_limiter.get_data(
        ticker=ticker,
        fetch_function=_fetch_ticker_data,
        timeout=timeout
    )


def configure_rate_limiter(max_requests_per_2min: int = 20, 
                          cache_expiry_hours: int = 24,
                          check_interval: float = 1.0,
                          max_retries: int = 3,
                          retry_delay: float = 5.0,
                          retry_backoff_factor: float = 2.0):
    """
    Configure the rate limiter with custom settings.
    
    Args:
        max_requests_per_2min (int): Maximum API requests allowed per 2 minutes
        cache_expiry_hours (int): How long to keep cached data (hours)
        check_interval (float): How often to check the queue (seconds)
        max_retries (int): Maximum retries for HTTP 500 errors
        retry_delay (float): Initial delay between retries (seconds)
        retry_backoff_factor (float): Exponential backoff multiplier for retries
    """
    config = RateLimitConfig(
        max_requests_per_2min=max_requests_per_2min,
        cache_expiry_hours=cache_expiry_hours,
        check_interval=check_interval,
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_backoff_factor=retry_backoff_factor
    )
    # This will create a new rate limiter with the new config
    # Note: This should ideally be called before any get_ticker calls
    global _rate_limiter
    if '_rate_limiter' in globals():
        from services.rate_limiter import cleanup_rate_limiter
        cleanup_rate_limiter()
    
    from services.rate_limiter import get_rate_limiter
    get_rate_limiter(config)
    logging.info(f"Rate limiter configured: {max_requests_per_2min} requests per 2min, "
                f"{max_retries} retries with {retry_delay}s delay")


def get_rate_limit_status() -> dict:
    """
    Get current rate limiting status and statistics.
    
    Returns:
        dict: Rate limiting information including queue size, cache size, etc.
    """
    rate_limiter = get_rate_limiter()
    return rate_limiter.get_request_rate_info()


def get_ticker_historic_candle(
        ticker: yf.Ticker,
        period: str = "60d",
        interval: str = "5m",
        prepost: bool = False
    ) -> Optional[pd.DataFrame]:
    """
    Retrieves the price data for a ticker with the given parameters.

    Notice that for intraday data, maximum period is 60d.
    Intervals available: 1m, 5m, 15m, 1h, 1d, etc.
    Prepost: Include pre-market & after-hours?

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.quarterly_balance_sheet Dataframe.
    """
    return yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        prepost=prepost
    )
