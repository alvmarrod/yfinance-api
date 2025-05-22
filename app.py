import os
import json
import logging
import datetime
from typing import Callable
from functools import cache

import pandas as pd

import yfinance as yf
from flask import Flask

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


##############################################################################
#                                 PARAMTERS                                  #
##############################################################################

USUAL_FIELDS: dict[str, str] = {
    "PERatio": "trailingPE",
    "debtToEquityPercentage": "debtToEquity"
}


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
    ex_dividend_date: int = data.info.get("exDividendDate", None)
    return _epoch_to_datetime(ex_dividend_date)


def calculate_roi_ratio(data: yf.Ticker) -> float:
    """
    Calculates the Return on Investment (ROI) ratio for a given stock ticker over the past year.

    Args:
        data (yf.Ticker): A yfinance Ticker object containing stock data.

    Returns:
        float: The ROI ratio calculated as (current price - price one year ago) / price one year ago.

    Raises:
        KeyError: If required price data is missing from the Ticker object.
        IndexError: If historical data for one year ago is not available.
        TypeError: If price values are not numeric.
    """
    current_price: int = data.info.get("currentPrice", None)
    one_year_ago: int = data.history(period="1y").iloc[0]['Close']
    return (current_price - one_year_ago) / one_year_ago


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
    current_price: int = data.info.get("currentPrice", None)
    one_year_ago: int = data.history(period="1y").iloc[0]['Close']
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



CALCULATED_FIELDS: dict[str, Callable] = {
    "exDividendDate": exdividend_to_datetime,
    "ROIRatio": calculate_roi_ratio,
    "annualGrowthRatio": calculate_annual_growth_ratio,
    "intrinsicValue": calculate_intrinsic_value,
    "discountToIntrinsicValueRatio": calculate_discount_to_intrinsic_value_ratio,
    "targetRatio": calculate_target_ratio
}


##############################################################################
#                                    API                                     #
##############################################################################

@cache
def get_symbol_data_full(tag: str) -> dict:
    """
    Fetches and returns comprehensive information for a given stock symbol, including calculated and mapped fields.

    This function retrieves the data for the specified symbol using yfinance, augments the data with additional
    calculated fields defined in CALCULATED_FIELDS, and maps usual fields from USUAL_FIELDS to the result.

    Args:
        tag (str): The stock symbol (ticker) to fetch data for.

    Returns:
        dict: A dictionary containing the symbol's information, including both original, calculated, and mapped fields.

    Note:
        - The function is cached to avoid redundant API calls.
        - Requires global CALCULATED_FIELDS and USUAL_FIELDS to be defined.
    """
    data: yf.Ticker = yf.Ticker(tag)
    # Include calculated fields
    for field, func in CALCULATED_FIELDS.items():
        data.info[field] = func(data)
    # Include mapped usual fields
    for field, real_field in USUAL_FIELDS.items():
        data.info[field] = data.info.get(real_field, None)
    return data.info


@app.route('/symbol/<tag>/<field>/raw', methods=['GET'])
def get_symbol_value_raw(tag, field):
    """
    Endpoint to retrieve the raw value of a specific field for a given symbol.

    Args:
        tag (str): The symbol identifier (e.g., stock ticker).
        field (str): The requested field name, which may be mapped to a real field name via USUAL_FIELDS.

    Returns:
        str: The raw value of the requested field for the given symbol, serialized as a JSON string with quotes stripped.

    Example:
        GET /symbol/AAPL/price/raw

    Notes:
        - If the requested field is in USUAL_FIELDS, it is mapped to its corresponding real field name.
        - If the field is not found in the symbol's data, returns 'null' (as a string).
    """
    real_field: str = field
    if field in USUAL_FIELDS:
        real_field = USUAL_FIELDS[field]

    info: dict = get_symbol_data_full(tag)
    return json.dumps((info.get(real_field, None))).strip('"')


@app.route('/symbol/<tag>/<field>/', methods=['GET'])
def get_symbol_value(tag, field):
    """
    Endpoint to retrieve a specific field value for a given symbol tag.

    Args:
        tag (str): The symbol tag (e.g., stock ticker) to query.
        field (str): The requested field name. If the field is in USUAL_FIELDS, it will be mapped to its corresponding value.

    Returns:
        str: A JSON-encoded dictionary containing the requested field and its value (or None if not found).

    Example:
        GET /symbol/AAPL/price/
        Response: {"price": 123.45}
    """
    real_field: str = field
    if field in USUAL_FIELDS:
        real_field = USUAL_FIELDS[field]

    info: dict = get_symbol_data_full(tag)
    return json.dumps({
        field: info.get(real_field, None)
    })


@app.route('/symbol/<tag>', methods=['GET'])
def get_symbol(tag):
    """
    Endpoint to retrieve detailed information for a given stock symbol.

    Args:
        tag (str): The stock symbol or tag to fetch data for.

    Returns:
        str: A JSON-formatted string containing the full data for the requested symbol.

    Example:
        GET /symbol/AAPL

    Notes:
        - The response is serialized as a JSON string.
        - Utilizes the `get_symbol_data_full` function to fetch symbol data.
    """
    info: dict = get_symbol_data_full(tag)
    return json.dumps(info)


@app.route('/symbol/historic/candle/<tag>', methods=['GET'])
def get_symbol_historic_as_candle(tag):
    """
    Endpoint to download and save historical candlestick data for a given symbol.

    Args:
        tag (str): The ticker symbol to fetch historical data for.

    Returns:
        str: A JSON-formatted string indicating the result of the operation and the filename if successful, or an error message if not.

    Details:
        - Downloads 60 days of historical data at 5-minute intervals for the specified ticker symbol using yfinance.
        - Saves the data as a CSV file named in the format: '{tag}_5m_{start_date}_{end_date}.csv'.
        - Returns a JSON object with the result and filename on success, or an error message on failure.
    """

    try:

        data: pd.DataFrame  = yf.download(
            tickers=tag,
            period="60d",    # Max allowed for intraday
            interval="5m",   # 1m, 5m, 15m, 1h, 1d, etc.
            prepost=False    # Include pre-market & after-hours?
        )

        today = datetime.datetime.now()
        today_str: str = today.strftime("%Y%m%d")
        sixty = datetime.timedelta(days=60)
        sixty_str: str = (today-sixty).strftime("%Y%m%d")
        filename: str = f"{tag}_5m_{sixty_str}_{today_str}.csv"

        # Full path to save the file
        cwd = os.getcwd()
        full_filepath = os.path.join(cwd, 'data', filename)
        data.to_csv(full_filepath)

    except Exception as e:
        logging.error(f"Error downloading or saving data for {tag}")
        logging.error(f"Error details: {str(e)}")
        return json.dumps({
            "result": "Couldn't download data for ticker: " + tag,
            "error": str(e)
        })

    return json.dumps({
        "result": "Data saved to file: " + filename,
    })

##############################################################################
#                                    MAIN                                    #
##############################################################################

if __name__ == "__main__":
    try:
        logging.info("Starting yfinance-api Flask server...")
        logging.info("Listening on http://0.0.0.0:5000")
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logging.info("Server interrupted by user (Ctrl+C). Shutting down gracefully.")
    except Exception as e:
        logging.exception(f"An error occurred while running the server: {e}")
