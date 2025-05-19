import json
import time
import logging
import datetime
from typing import Callable
from functools import cache

from requests import Session
from requests_cache import CachedSession, CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter


import yfinance as yf
from flask import Flask


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass


RATE_LIMITED_SESSION = CachedLimiterSession(
    # max 2 requests per 10 seconds
    limiter=Limiter(RequestRate(2, Duration.SECOND*10)),
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# RATE_LIMITED_SESSION: CachedSession = CachedSession('yfinance.cache')
# RATE_LIMITED_SESSION.headers['User-agent'] = 'yfinance-api/0.1.0'


@app.route('/')
def hello_geek():
    return ''


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
    return datetime.datetime.fromtimestamp(epoch).strftime('%d/%m/%Y')


def exdividend_to_datetime(data: yf.Ticker) -> str:
    ex_dividend_date: int = data.info.get("exDividendDate", None)
    return _epoch_to_datetime(ex_dividend_date)


def calculate_roi_ratio(data: yf.Ticker) -> float:
    current_price: int = data.info.get("currentPrice", None)
    one_year_ago: int = data.history(period="1y").iloc[0]['Close']
    return (current_price - one_year_ago) / one_year_ago


def calculate_annual_growth_ratio(data: yf.Ticker) -> float:
    current_price: int = data.info.get("currentPrice", None)
    one_year_ago: int = data.history(period="1y").iloc[0]['Close']
    return (current_price - one_year_ago) / one_year_ago


def calculate_intrinsic_value(data: yf.Ticker) -> float:
    """Calculates the intrinsic value of a stock using the Buffet formula.
    The formula is:
    IV = EPS * (8.5 + 2 * G)
    where:
    - IV is the intrinsic value
    - EPS is the earnings per share -> trailingEps
    - G is the annual growth ratio in earnings
    """
    eps: float = data.info.get("epsTrailingTwelveMonths", 0)
    earnings_growth: float = data.info.get("earningsGrowth", 0)
    intrinsic_value: float = eps * (8.5 + 2 * earnings_growth * 100)
    return intrinsic_value


def calculate_discount_to_intrinsic_value_ratio(data: yf.Ticker) -> float:
    intrinsic_value: float = calculate_intrinsic_value(data)
    current_price: float = data.info.get("currentPrice", 0)
    if intrinsic_value == 0:
        return 0
    return (intrinsic_value - current_price) / intrinsic_value


def calculate_target_ratio(data: yf.Ticker) -> float:
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
    real_field: str = field
    if field in USUAL_FIELDS:
        real_field = USUAL_FIELDS[field]

    info: dict = get_symbol_data_full(tag)
    return json.dumps((info.get(real_field, None))).strip('"')


@app.route('/symbol/<tag>/<field>/', methods=['GET'])
def get_symbol_value(tag, field):
    real_field: str = field
    if field in USUAL_FIELDS:
        real_field = USUAL_FIELDS[field]

    info: dict = get_symbol_data_full(tag)
    return json.dumps({
        field: info.get(real_field, None)
    })


@app.route('/symbol/<tag>', methods=['GET'])
def get_symbol(tag):
    info: dict = get_symbol_data_full(tag)
    return json.dumps(info)


##############################################################################
#                                    MAIN                                    #
##############################################################################

if __name__ == "__main__":
    app.run(debug=True)
