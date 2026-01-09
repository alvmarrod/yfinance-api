"""
Business logic for the yfinance wrapper
- Section for ticker data retrieval from yfinance API
"""
from typing import Optional
from functools import cache
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

@dataclass
class FullTickerData:
    info: dict
    financials: pd.DataFrame
    balance_sheet: pd.DataFrame
    cashflow: pd.DataFrame
    quarterly_income_stmt: pd.DataFrame
    quarterly_balance_sheet: pd.DataFrame

##############################################################################
#                                 FUNCTIONS                                  #
##############################################################################

@cache
def get_ticker(ticker: str) -> FullTickerData:
    """
    Retrieves a yfinance Ticker object for the given ticker symbol.

    Args:
        ticker (str): The stock ticker symbol to retrieve data for.

    Returns:
        yf.Ticker: A yfinance Ticker object containing stock information.
    """
    yfinance_ticker: yf.Ticker = yf.Ticker(ticker)

    return FullTickerData(
        info=yfinance_ticker.info,
        financials=yfinance_ticker.financials,
        balance_sheet=yfinance_ticker.balance_sheet,
        cashflow=yfinance_ticker.cashflow,
        quarterly_income_stmt=yfinance_ticker.quarterly_income_stmt,
        quarterly_balance_sheet=yfinance_ticker.quarterly_balance_sheet
    )


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
