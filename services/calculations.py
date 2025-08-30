"""
Customised calculations
"""
import logging
import datetime
from typing import Callable, Optional

import pandas as pd
import yfinance as yf


##############################################################################
#                               Calculations                                 #
##############################################################################

def _epoch_to_datetime(epoch: int) -> str:
    """
    Converts a Unix epoch timestamp to a formatted date string.

    Args:
        epoch (int): The Unix epoch timestamp to convert.

    Returns:
        str: The date in 'DD/MM/YYYY' format.

    Raises:
        ValueError: If the epoch value is not a valid timestamp.

    Example:
        >>> _epoch_to_datetime(1704067200)
        '01/01/2024'
    """
    return datetime.datetime.fromtimestamp(epoch).strftime('%d/%m/%Y')


def exdividend_to_datetime(data: yf.Ticker) -> str:
    """
    Converts the ex-dividend date from a yfinance Ticker object to a human-readable datetime string.

    Args:
        data (yf.Ticker): A yfinance Ticker object containing stock information.

    Returns:
        str: The ex-dividend date as a formatted datetime string, or None if not available.

    Note:
        This function expects the Ticker object to have an 'exDividendDate' field in its 'info' dictionary,
        represented as a Unix epoch timestamp (seconds since 1970-01-01).
    """
    ex_dividend_date: Optional[int] = data.info.get("exDividendDate", None)
    if ex_dividend_date:
        return _epoch_to_datetime(ex_dividend_date)
    else:
        return "-"


def calculate_roe_ratio(data: yf.Ticker) -> float:
    """
    Calculates the Return on Equity (ROE) ratio for a given stock ticker.

    ROE is defined as:
        Net Income / Shareholders' Equity

    This measures how effectively a company is using its equity to generate profit.

    Returns:
        float: ROE ratio (decimal), or -1 if required data is missing.
    """
    try:
        net_income = data.financials.loc['Net Income Applicable To Common Shares'].iloc[0]
    except KeyError:
        net_income = data.info.get('netIncomeToCommon', None)

    try:
        total_equity = data.balance_sheet.loc['Total Stockholder Equity'].iloc[0]
    except KeyError:
        # Intentar con 'Stockholders Equity' si no existe 'Total Stockholder Equity'
        try:
            total_equity = data.balance_sheet.loc['Stockholders Equity'].iloc[0]
        except KeyError:
            total_equity = data.info.get('totalStockholderEquity', None)

    if not isinstance(net_income, (int, float)):
        logging.warning("NetIncome falta para calcular el ROE")
        return -1

    if not isinstance(total_equity, (int, float)) or total_equity == 0:
        logging.warning("Total Equity falta para calcular el ROE")
        return -1

    return net_income / total_equity


def calculate_annual_growth_ratio(data: yf.Ticker) -> float:
    """
    Calculates the annual growth ratio of a stock based on its current price and the closing price from one year ago.

    Args:
        data (yf.Ticker): A yfinance Ticker object containing stock data.

    Returns:
        float: The annual growth ratio, calculated as (current price - price one year ago) / price one year ago.

    Raises:
        KeyError: If 'Close' is not found in the historical data.
        TypeError: If current price or historical price is None.
        IndexError: If historical data for one year ago is not available.
    """
    current_price: Optional[int] = data.info.get("currentPrice", None)
    one_year_ago: int = data.history(period="1y").iloc[0]['Close']

    if current_price is None or one_year_ago is None:
        logging.warning("Current price or historical price is None")
        return 0.0

    return (current_price - one_year_ago) / one_year_ago


def calculate_intrinsic_value(data: yf.Ticker) -> float:
    """
    Calculates the intrinsic value of a stock using a variation of the Buffett formula.

    The intrinsic value (IV) is estimated as:
        IV = EPS * (8.5 + 2 * G * 100)

    Where:
        - EPS: Earnings per share (taken from 'epsTrailingTwelveMonths' in the ticker info)
        - G: Annual earnings growth rate (taken from 'earningsGrowth' in the ticker info, as a decimal)

    Args:
        data (yf.Ticker): A yfinance Ticker object containing stock information.

    Returns:
        float: The calculated intrinsic value of the stock.

    Note:
        If the required fields are missing in the ticker info, default values of 0 are used.
    """
    eps: float = data.info.get("epsTrailingTwelveMonths", 0)
    earnings_growth: float = data.info.get("earningsGrowth", 0)
    intrinsic_value: float = eps * (8.5 + 2 * earnings_growth * 100)
    return intrinsic_value


def calculate_discount_to_intrinsic_value_ratio(data: yf.Ticker) -> float:
    """
    Calculates the discount ratio of the current price to the intrinsic value of a stock.

    This function computes how much lower the current market price is compared to the estimated intrinsic value,
    expressed as a fraction of the intrinsic value. A positive result indicates the stock is trading below its
    intrinsic value (potentially undervalued), while a negative result indicates it is trading above.

    Args:
        data (yf.Ticker): A yfinance Ticker object containing stock data, including current price.

    Returns:
        float: The discount ratio, calculated as (intrinsic_value - current_price) / intrinsic_value.
               Returns 0 if the intrinsic value is zero to avoid division by zero.
    """
    intrinsic_value: float = calculate_intrinsic_value(data)
    current_price: float = data.info.get("currentPrice", 0)
    if intrinsic_value == 0:
        return 0
    return (intrinsic_value - current_price) / intrinsic_value


def calculate_target_ratio(data: yf.Ticker) -> float:
    """
    Calculates the target ratio for a given stock based on its current price and target mean price.

    The target ratio is defined as the relative difference between the target mean price and the current price,
    normalized by the current price. If the target mean price is not available (i.e., zero), the function returns 0.

    Args:
        data (yf.Ticker): A yfinance Ticker object containing stock information.

    Returns:
        float: The target ratio, or 0 if the target mean price is unavailable.
    """
    current_price: float = data.info.get("currentPrice", 0)
    target_mean_price: float = data.info.get("targetMeanPrice", 0)
    if target_mean_price == 0:
        return 0
    return (target_mean_price - current_price) / current_price


def calculate_dividend_frequency(data: yf.Ticker) -> str:
    """
    Determines the frequency of dividend payments for a given stock based on
    t.dividends data.
    """
    freq: str = "-"
    divs: pd.Series = data.dividends
    if not divs.empty:
        diffs = divs.index.to_series().diff().dt.days.dropna()
        avg_gap = diffs.mean()

        if avg_gap < 100:
            freq = "Quarterly"
        elif avg_gap < 250:
            freq = "Semesterly"
        else:
            freq = "Annual"

    return freq


def _growth_to_pct(g: Optional[float]) -> Optional[float]:
    """
    Converts a growth value to a percentage.
    """
    if g is None:
        return None

    try:
        g = float(g)

        if g <= 0:
            return None

        return g * 100 if g < 1 else g  # 0.10 -> 10, 10 -> 10

    except Exception as err:
        logging.warning("Error converting growth to percentage: %s", err)

    return None


def calculate_peg_ratio(data: yf.Ticker) -> Optional[float]:
    """
    Calculates the Price/Earnings to Growth (PEG) ratio for a given stock.
    """
    peg: Optional[float] = float("nan")
    pe: Optional[float] = data.info.get("forwardPE", None)
    eps_growth: Optional[float] = data.info.get("earningsGrowth", None)

    if pe is not None and pe > 0 and eps_growth is not None and eps_growth > 0:
        g_pct = _growth_to_pct(eps_growth)
        if g_pct is not None:
            peg = pe / g_pct
    else:
        logging.warning("Insufficient data to calculate PEG ratio (PE: %s, Growth: %s)", pe, eps_growth)

    return peg

##############################################################################
#                           CALCULATIONS MAPPIGN                             #
##############################################################################

CALCULATED_FIELDS: dict[str, Callable] = {
    "exDividendDate": exdividend_to_datetime,
    "ROE": calculate_roe_ratio,
    "annualGrowthRatio": calculate_annual_growth_ratio,
    "intrinsicValue": calculate_intrinsic_value,
    "discountToIntrinsicValueRatio": calculate_discount_to_intrinsic_value_ratio,
    "targetRatio": calculate_target_ratio,
    "dividendFrequency": calculate_dividend_frequency,
    "pegRatio": calculate_peg_ratio,
    "peToGrowth": calculate_peg_ratio,  # Alias
}


##############################################################################
#                                PUBLIC APPLY                                #
##############################################################################

def calculate_fields(ticker_data: yf.Ticker) -> dict:
    """
    Applies the calculation fields to the given ticker, and returns all the
    results as a dictionary.

    Args:
        data (yf.Ticker): A yfinance Ticker

    Returns:
        dict: The dictionary with the fields specified in CALCULATED_FIELDS
                and all their values
    """
    result: dict = {}
    for field, func in CALCULATED_FIELDS.items():
        try:
            result[field] = func(ticker_data)
        except Exception as err:
            logging.warning("Error while calculating %s", field)
            logging.info("Detail:\n%s", str(err))

    return result
