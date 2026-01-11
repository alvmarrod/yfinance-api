"""
Wrapper to get the yfinance Ticker information.

It abstracts away the rate limiting and caching logic, providing a simple
interface to get ticker data without hitting API limits.
"""
from typing import Optional

import pandas as pd
import yfinance as yf

from services.job_dispatcher import get_dispatcher
from services.full_ticker_data import FullTickerData

##############################################################################
#                              PUBLIC FUNCTIONS                              #
##############################################################################

def get_ticker(ticker: str) -> FullTickerData:
    """
    Retrieves a yfinance Ticker object for the given ticker symbol.
    
    Abstracts the usage of:
    - Job queue
    - Cache
    - Rate limiter

    Args:
        ticker (str): The stock ticker symbol to retrieve data for.

    Returns:
        FullTickerData: A dataclass containing complete stock information.
        
    Raises:
        Exception: If there's an error fetching the data
    """
    # TODO: review the propagatio of exceptions or None
    dispatcher = get_dispatcher()
    return dispatcher.get_ticker_data(ticker)

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
