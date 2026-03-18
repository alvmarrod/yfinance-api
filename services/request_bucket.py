"""
Time-windowed request bucket with deduplication.
"""

from dataclasses import dataclass, field
from datetime import datetime
from services.queued_request import QueuedRequest


@dataclass
class BatchedRequest:
    """A request waiting for batch processing."""

    ticker: str
    needed_sections: set[str]
    response_holder: QueuedRequest


@dataclass
class RequestBucket:
    """A time-windowed bucket of requests with deduplication."""

    requests: list[BatchedRequest] = field(default_factory=list)
    ticker_map: dict[str, list[BatchedRequest]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def size(self) -> int:
        """Return number of unique tickers in bucket."""
        return len(self.ticker_map)

    def add_request(
        self, ticker: str, sections: set[str], holder: QueuedRequest
    ) -> bool:
        """
        Add request to bucket with deduplication.

        Returns True if new ticker (needs API call), False if duplicate.
        """
        if ticker in self.ticker_map:
            existing = self.ticker_map[ticker][0]
            existing.needed_sections.update(sections)
            self.ticker_map[ticker].append(BatchedRequest(ticker, sections, holder))
            return False
        else:
            batched = BatchedRequest(ticker, sections.copy(), holder)
            self.requests.append(batched)
            self.ticker_map[ticker] = [batched]
            return True

    def get_unique_tickers(self) -> dict[str, set[str]]:
        """Get unique tickers with their merged section requirements."""
        return {
            ticker: batched[0].needed_sections
            for ticker, batched in self.ticker_map.items()
        }
