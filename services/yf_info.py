"""
Wrapper to get the yfinance Ticker information.

It abstracts away the rate limiting and caching logic, providing a simple
interface to get ticker data without hitting API limits.
"""

from typing import Optional, Any

import pandas as pd
import yfinance as yf

from services.job_dispatcher import get_dispatcher
from services.full_ticker_data import FullTickerData

##############################################################################
#                              PUBLIC FUNCTIONS                              #
##############################################################################


def get_field_value(ticker: str, field_name: str) -> Any:
    """
    Get a single field value using lazy loading.
    Fetches minimal data needed for this field.
    """
    dispatcher = get_dispatcher()
    return dispatcher.get_field_value(ticker, field_name)


def get_basic_ticker_info(ticker: str) -> FullTickerData:
    """
    Get only basic ticker info (info section).
    Fast operation for basic data.
    """
    dispatcher = get_dispatcher()
    return dispatcher.get_basic_ticker_data(ticker)


def get_full_ticker_data(ticker: str) -> FullTickerData:
    """
    Get complete ticker data (all sections).
    Backwards compatible with current implementation.
    """
    dispatcher = get_dispatcher()
    return dispatcher.get_complete_ticker_data(ticker)


def get_specific_sections(ticker: str, sections: set[str]) -> FullTickerData:
    """
    Get specific data sections only.
    For advanced use cases.
    """
    dispatcher = get_dispatcher()
    return dispatcher.get_specific_sections(ticker, sections)


def get_ticker_historic_candle(
    ticker: yf.Ticker, period: str = "60d", interval: str = "5m", prepost: bool = False
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
        tickers=ticker, period=period, interval=interval, prepost=prepost
    )
