from dataclasses import dataclass

import pandas as pd

@dataclass
class FullTickerData:
    info: dict
    financials: pd.DataFrame
    balance_sheet: pd.DataFrame
    cashflow: pd.DataFrame
    dividends: pd.Series
    history: pd.DataFrame
    quarterly_income_stmt: pd.DataFrame
    quarterly_balance_sheet: pd.DataFrame