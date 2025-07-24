"""
Business logic for the yfinance wrapper
- Section for ticker data retrieval from yfinance API
"""

from typing import Optional

import pandas as pd
import yfinance as yf


##############################################################################
#                                 FUNCTIONS                                  #
##############################################################################

def get_ticker(ticker: str) -> yf.Ticker:
    """
    Retrieves a yfinance Ticker object for the given ticker symbol.

    Args:
        ticker (str): The stock ticker symbol to retrieve data for.

    Returns:
        yf.Ticker: A yfinance Ticker object containing stock information.
    """
    return yf.Ticker(ticker)


def get_ticker_info(ticker: yf.Ticker) -> dict:
    """
    Retrieves the subobject info from a ticker

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.info object containing stock general information.
    """
    return ticker.info


def get_ticker_financials(ticker: yf.Ticker) -> pd.DataFrame:
    """
    Retrieves the subobject financials from a ticker

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.financials Dataframe.
    """
    return ticker.financials


def get_ticker_balance_sheet(ticker: yf.Ticker) -> pd.DataFrame:
    """
    Retrieves the subobject balance_sheet from a ticker

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.balance_sheet Dataframe.
    """
    return ticker.balance_sheet


def get_ticker_cashflow(ticker: yf.Ticker) -> pd.DataFrame:
    """
    Retrieves the subobject cashflow from a ticker

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.cashflow Dataframe.
    """
    return ticker.cashflow


def get_ticker_quarterly_income_stmt(ticker: yf.Ticker) -> pd.DataFrame:
    """
    Retrieves the subobject quarterly_income_stmt from a ticker

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.quarterly_income_stmt Dataframe.
    """
    return ticker.quarterly_income_stmt


def get_ticker_quarterly_balance_sheet(ticker: yf.Ticker) -> pd.DataFrame:
    """
    Retrieves the subobject quarterly_balance_sheet from a ticker

    Args:
        ticker (yf.Ticker): The stock ticker symbol to retrieve data for.

    Returns:
        dict: A Ticker.quarterly_balance_sheet Dataframe.
    """
    return ticker.quarterly_balance_sheet


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
