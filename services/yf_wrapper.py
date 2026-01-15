"""
Business logic for the yfinance wrapper
- Section for ticker data composition back to the routes
"""

import utils.dataframe as dfu

from services.full_ticker_data import FullTickerData
from services.missing_data import MissingDataException

##############################################################################
#                                PARAMETERS                                  #
##############################################################################

USUAL_FIELDS: dict[str, str] = {
    "PERatio": "trailingPE",
    "debtToEquityPercentage": "debtToEquity",
}


def get_usual_fields(ticker_data: FullTickerData) -> dict:
    """
    Extracts usual fields from the ticker data and returns them as a
    dictionary.
    """
    if ticker_data.info is None:
        raise MissingDataException(ticker_data.ticker, {"info"})

    result: dict = {}
    for field, real_field in USUAL_FIELDS.items():
        result[field] = ticker_data.info.get(real_field, None)

    return result


def get_real_field_name(field: str) -> str:
    """
    Returns the real field name for a given field if it exists in USUAL_FIELDS,
    otherwise returns the field itself.
    """
    return USUAL_FIELDS.get(field, field)


##############################################################################
#                               COMPOSITION                                  #
##############################################################################


def compose_ticker_dict(ticker_data: FullTickerData) -> dict:
    """
    Composes a dictionary representation of the ticker data, including usual
    fields and all available sections.
    """
    result: dict = {}

    # Add usual fields
    result.update(get_usual_fields(ticker_data))

    # Add all other sections
    if ticker_data.info is not None:
        result["info"] = ticker_data.info

    if ticker_data.financials is not None:
        result["financials"] = dfu.df_to_json_safe(ticker_data.financials)

    if ticker_data.balance_sheet is not None:
        result["balance_sheet"] = dfu.df_to_json_safe(ticker_data.balance_sheet)

    if ticker_data.cashflow is not None:
        result["cashflow"] = dfu.df_to_json_safe(ticker_data.cashflow)

    if ticker_data.dividends is not None:
        result["dividends"] = dfu.series_to_json_safe(ticker_data.dividends)

    if ticker_data.history is not None:
        result["history"] = dfu.df_to_json_safe(ticker_data.history)

    if ticker_data.quarterly_income_stmt is not None:
        result["quarterly_income_stmt"] = dfu.df_to_json_safe(
            ticker_data.quarterly_income_stmt
        )

    if ticker_data.quarterly_balance_sheet is not None:
        result["quarterly_balance_sheet"] = dfu.df_to_json_safe(
            ticker_data.quarterly_balance_sheet
        )

    return result
