"""
Routes served by the API.
"""
import os
import json
import logging
import datetime

from typing import Optional

from flask import request
from flask import Blueprint
from pandas import DataFrame

import services.yf_info as yfi
import services.yf_wrapper as yfw

api = Blueprint('api', __name__)

app_logger = logging.getLogger('yfinance-api')

##############################################################################
#                                    API                                     #
##############################################################################

@api.route('/symbol/<tag>/<field>/raw', methods=['GET'])
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
    try:
        real_field: str = yfw.get_real_field_name(field)
        app_logger.debug(f"Processing {tag}/{field} -> {real_field}")

        # Request only this specific field (lazy loading)
        field_value = yfi.get_field_value(tag, real_field)

        result = json.dumps(field_value).strip('"')
        return result
        
    except TimeoutError as e:
        app_logger.error(f"Timeout error for {tag}/{field}: {e}")
        return json.dumps({"error": f"Request timeout for {tag}"}), 408
    except Exception as e:
        app_logger.error(f"Error processing {tag}/{field}: {e}")
        return json.dumps({"error": f"Server error for {tag}: {str(e)}"}), 500


@api.route('/symbol/<tag>/<field>/', methods=['GET'])
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
    real_field: str = yfw.get_real_field_name(field)

    field_value = yfi.get_field_value(tag, real_field)
    return json.dumps({field: field_value})


@api.route('/symbol/<tag>', methods=['GET'])
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
    full_data = yfi.get_full_ticker_data(tag)
    composed_dict = yfw.compose_ticker_dict(full_data)
    
    return json.dumps(composed_dict)


@api.route('/symbol/historic/candle/<tag>', methods=['GET'])
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

        data: Optional[DataFrame] = yfi.get_ticker_historic_candle(
            ticker=tag,
            period="60d",
            interval="5m",
            prepost=False
        )

        assert data is not None, "Couldn't download the historic for the ticker"

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
        app_logger.error("Error downloading or saving data for %s", tag)
        app_logger.error("Error details: %s", str(e))
        return json.dumps({
            "result": "Couldn't download data for ticker: " + tag,
            "error": str(e)
        })

    return json.dumps({
        "result": "Data saved to file: " + filename,
    })
