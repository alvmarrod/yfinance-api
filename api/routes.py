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
        logging.debug(f"Processing {tag}/{field} -> {real_field}")

        info: dict = yfw.get_ticker_as_dict(tag)
        result = json.dumps((info.get(real_field, '-'))).strip('"')
        logging.debug(f"Successfully processed {tag}/{field}")
        return result
        
    except TimeoutError as e:
        logging.error(f"Timeout error for {tag}/{field}: {e}")
        return json.dumps({"error": f"Request timeout for {tag}"}), 408
    except Exception as e:
        logging.error(f"Error processing {tag}/{field}: {e}")
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

    info: dict = yfw.get_ticker_as_dict(tag)
    return json.dumps({
        field: info.get(real_field, None)
    })


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
    info: dict = yfw.get_ticker_as_dict(tag)
    return json.dumps(info)


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
        logging.error("Error downloading or saving data for %s", tag)
        logging.error("Error details: %s", str(e))
        return json.dumps({
            "result": "Couldn't download data for ticker: " + tag,
            "error": str(e)
        })

    return json.dumps({
        "result": "Data saved to file: " + filename,
    })


@api.route('/status/rate-limit', methods=['GET'])
def get_rate_limit_status():
    """
    Endpoint to get current rate limiting status and statistics.
    
    Returns:
        JSON object containing rate limiting information including:
        - requests_last_2min: Number of requests in the last 2 minutes
        - max_requests_per_2min: Maximum allowed requests per 2 minutes
        - can_make_request: Whether we can currently make a request
        - queue_size: Number of pending requests in queue
        - cache_size: Number of cached ticker data entries
    
    Example:
        GET /status/rate-limit
    """
    try:
        status = yfi.get_rate_limit_status()
        return json.dumps(status)

    except Exception as e:
        logging.error("Error getting rate limit status: %s", e)
        return json.dumps({
            "error": f"Error getting rate limit status: {str(e)}"
        })


@api.route('/config/rate-limit', methods=['POST'])
def configure_rate_limit():
    """
    Endpoint to configure rate limiting parameters.
    
    Expected JSON payload (all optional):
    {
        "max_requests_per_2min": 20,
        "cache_expiry_hours": 1,
        "check_interval": 2.0,
        "max_retries": 3,
        "retry_delay": 5.0,
        "retry_backoff_factor": 2.0
    }
    
    Returns:
        JSON confirmation of the configuration.
    """
    try:
        if not request.is_json:
            return json.dumps({"error": "Content-Type must be application/json"})
        
        data = request.get_json()
        
        # Set defaults if not provided
        max_requests = data.get('max_requests_per_2min', 20)
        cache_expiry = data.get('cache_expiry_hours', 24)
        check_interval = data.get('check_interval', 1.0)
        max_retries = data.get('max_retries', 3)
        retry_delay = data.get('retry_delay', 5.0)
        retry_backoff_factor = data.get('retry_backoff_factor', 2.0)
        
        yfi.configure_rate_limiter(
            max_requests_per_2min=max_requests,
            cache_expiry_hours=cache_expiry,
            check_interval=check_interval,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff_factor=retry_backoff_factor,
        )
        
        return json.dumps({
            "result": "Rate limiter configured successfully",
            "config": {
                "max_requests_per_2min": max_requests,
                "cache_expiry_hours": cache_expiry,
                "check_interval": check_interval,
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "retry_backoff_factor": retry_backoff_factor
            }
        })
        
    except Exception as e:
        logging.error("Error configuring rate limiter: %s", e)
        return json.dumps({
            "error": f"Error configuring rate limiter: {str(e)}"
        })
