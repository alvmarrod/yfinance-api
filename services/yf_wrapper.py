"""
Business logic for the yfinance wrapper
- Section for ticker data composition back to the routes
"""

import utils.dataframe as dfu
import services.yf_info as yfi
import services.calculations as calc

##############################################################################
#                                PARAMETERS                                  #
##############################################################################

USUAL_FIELDS: dict[str, str] = {
    "PERatio": "trailingPE",
    "debtToEquityPercentage": "debtToEquity"
}


def get_usual_fields(ticker_data: yfi.FullTickerData) -> dict:
    """
    Extracts usual fields from the ticker data and returns them as a
    dictionary.
    """
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


def get_ticker_as_dict(tag: str) -> dict:
    """
    Fetches and returns comprehensive information for a given stock symbol,
    including calculated and mapped fields.

    From the default API info, `.info` is used as base, while `.financials`,
    `.balance_sheet` and `.cashflow` are added as well as subsets.

    Quarterly statements and sheets are included as well.

    This function retrieves the data for the specified symbol using yfinance,
    augments the data with additional
    calculated fields defined in CALCULATED_FIELDS, and maps usual fields from
    USUAL_FIELDS to the result.

    Args:
        tag (str): The stock symbol (ticker) to fetch data for.

    Returns:
        dict: A dictionary containing the symbol's information, including both
        original, calculated, and mapped fields.

    Note:
        - The function is cached to avoid redundant API calls.
        - Requires global CALCULATED_FIELDS and USUAL_FIELDS to be defined.
    """
    result: dict = {}
    data: yfi.FullTickerData = yfi.get_ticker(tag)

    if data.info is None:
        return result

    result = data.info

    result.update({
        #"info": dfu.df_to_json_safe(data.info),     # type: ignore
        "financials": dfu.df_to_json_safe(data.financials),
        "balance_sheet": dfu.df_to_json_safe(data.balance_sheet),
        "cashflow": dfu.df_to_json_safe(data.cashflow),
        "dividends": dfu.series_to_json_safe(data.dividends),
        "quarterly_income_stmt": dfu.df_to_json_safe(data.quarterly_income_stmt),
        "quarterly_balance_sheet": dfu.df_to_json_safe(data.quarterly_balance_sheet),
    })

    extra_data: dict = calc.calculate_fields(data)
    result.update(extra_data)

    usual_fields: dict = get_usual_fields(data)
    result.update(usual_fields)

    return result
