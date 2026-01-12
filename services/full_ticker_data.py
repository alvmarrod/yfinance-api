from typing import Optional
from dataclasses import dataclass

import pandas as pd

##############################################################################
#                           FULL TICKER DATA CLASS                           #
##############################################################################

@dataclass
class FullTickerData:
    ticker: str
    info: Optional[dict] = None
    financials: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cashflow: Optional[pd.DataFrame] = None
    dividends: Optional[pd.Series] = None
    history: Optional[pd.DataFrame] = None
    quarterly_income_stmt: Optional[pd.DataFrame] = None
    quarterly_balance_sheet: Optional[pd.DataFrame] = None
