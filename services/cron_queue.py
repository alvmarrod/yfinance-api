"""
Thread-safe unlimited queue for cron job requests.
"""

import logging

import threading as tg
from typing import Optional
from datetime import datetime
from collections import deque

from services.queued_request import QueuedRequest

app_logger = logging.getLogger("yfinance-api")


class tsCronQueue:
    """
    Thread-safe unlimited queue for cron job requests.
    Unlike the regular queue, this has no max size and no timeout.
    """

    lock: tg.Lock
    item_deque: deque[QueuedRequest]

    def __init__(self):
        app_logger.info("🆕 Initializating cron queue")
        self.lock = tg.Lock()
        self.item_deque = deque()

    def queue_size(self) -> int:
        """Return the current size of the queue."""
        with self.lock:
            return len(self.item_deque)

    def add_job(self, ticker: str, sections: set[str]) -> QueuedRequest:
        """Add a job to the cron queue (unlimited capacity, no timeout)."""
        request = QueuedRequest(
            ticker=ticker,
            sections=sections,
            timestamp=datetime.now(),
            result_event=tg.Event(),
            no_timeout=True,
        )

        with self.lock:
            self.item_deque.append(request)
            app_logger.debug(f"📥 Cron queue: added {ticker} for {sections}")

        return request

    def get_job(self) -> Optional[QueuedRequest]:
        """Get a job from the front of the queue."""
        with self.lock:
            try:
                result = self.item_deque.popleft()
                app_logger.debug(
                    f"📤 Cron queue: retrieved {result.ticker} for {result.sections}"
                )
                return result
            except IndexError:
                return None

    def put_job_back(self, job: QueuedRequest) -> None:
        """Put job back at front of queue."""
        with self.lock:
            self.item_deque.appendleft(job)
