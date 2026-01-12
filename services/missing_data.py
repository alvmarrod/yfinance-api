

class MissingDataException(Exception):
    """Raised when a calculation needs data that hasn't been fetched yet."""

    ticker: str
    message: str
    missing_sections: set[str]
    
    def __init__(self, ticker: str, missing_sections: set[str], message: str = ""):
        self.ticker = ticker
        self.missing_sections = missing_sections
        self.message = message or f"Missing data sections for {ticker}: {missing_sections}"
        super().__init__(self.message)
