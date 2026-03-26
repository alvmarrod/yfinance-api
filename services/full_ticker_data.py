from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

##############################################################################
#                           FULL TICKER DATA CLASS                           #
##############################################################################

BLOCKS = [
    "info",
    "financials",
    "balance_sheet",
    "cashflow",
    "dividends",
    "history",
    "quarterly_income_stmt",
    "quarterly_balance_sheet",
]


@dataclass
class FullTickerData:
    ticker: str
    # Data blocks
    info: Optional[dict] = None
    financials: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    cashflow: Optional[pd.DataFrame] = None
    dividends: Optional[pd.Series] = None
    history: Optional[pd.DataFrame] = None
    quarterly_income_stmt: Optional[pd.DataFrame] = None
    quarterly_balance_sheet: Optional[pd.DataFrame] = None
    # Per-block retrieval times
    info_retrieval_time: Optional[datetime] = None
    financials_retrieval_time: Optional[datetime] = None
    balance_sheet_retrieval_time: Optional[datetime] = None
    cashflow_retrieval_time: Optional[datetime] = None
    dividends_retrieval_time: Optional[datetime] = None
    history_retrieval_time: Optional[datetime] = None
    quarterly_income_stmt_retrieval_time: Optional[datetime] = None
    quarterly_balance_sheet_retrieval_time: Optional[datetime] = None

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

    def get_max_block_time(self) -> Optional[datetime]:
        """Get the most recent retrieval time across all blocks."""
        times = []
        for block in BLOCKS:
            time_field = f"{block}_retrieval_time"
            block_time = getattr(self, time_field, None)
            if block_time:
                times.append(block_time)
        return max(times) if times else None

    def get_block_sections(self) -> set[str]:
        """Get set of blocks that have data."""
        return {block for block in BLOCKS if getattr(self, block, None) is not None}
