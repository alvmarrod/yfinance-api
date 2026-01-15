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

    def has_required_sections(self, required_sections: set[str]) -> bool:
        """Check if cached data contains all required sections."""
        for section in required_sections:
            if getattr(self, section, None) is None:
                return False
        return True

    def update_with_data(self, other: "FullTickerData"):
        """Update current data with another FullTickerData instance."""
        for field in self.__dataclass_fields__:
            other_value = getattr(other, field)
            if other_value is not None:
                setattr(self, field, other_value)
