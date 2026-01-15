import threading as tg
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from services.full_ticker_data import FullTickerData


@dataclass
class QueuedRequest:
    """Represents a queued API request."""

    ticker: str
    sections: set[str]
    timestamp: datetime
    result_event: tg.Event  # Used to signal when processing is complete
    result: Optional[FullTickerData] = None
    error: Optional[Exception] = None

    def set_result(self, data: FullTickerData) -> None:
        """Set the successful result and signal completion."""
        self.result = data
        self.result_event.set()

    def set_error(self, error: Exception) -> None:
        """Set an error and signal completion."""
        self.error = error
        self.result_event.set()

    def wait_for_result(self, timeout: Optional[float] = None) -> bool:
        """Wait for the result to be ready. Returns True if ready, False if timeout."""
        return self.result_event.wait(timeout)
