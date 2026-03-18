"""
Module that implements a thread-safe queue manager
"""

import logging

import threading as tg
from typing import Optional
from datetime import datetime
from collections import deque

from utils.progressbar import create_progress_bar

from services.cache import tsCache
from services.queued_request import QueuedRequest
from services.full_ticker_data import FullTickerData

app_logger = logging.getLogger("yfinance-api")

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

QUEUE_MAX_SIZE: int = 225

QUEUE_SIZE_LOG_MSG: str = "📊 Queue status [approximated]: %s"

##############################################################################
#                                   QUEUE                                    #
##############################################################################


class tsQueue:
    """
    Thread safe Deque object for processing ticker data requests
    """

    lock: tg.Lock
    item_deque: deque[QueuedRequest]

    def __init__(self):
        app_logger.info("🆕 Initializating a queue")
        self.lock = tg.Lock()
        self.item_deque = deque()

    def queue_size(self) -> int:
        """Return the current size of the queue"""
        with self.lock:
            return len(self.item_deque)

    def _queue_usage_report(self) -> None:
        """Reports the current status of the queue usage"""
        report_msg: str = QUEUE_SIZE_LOG_MSG % create_progress_bar(
            current=self.queue_size(), total=QUEUE_MAX_SIZE, width=10
        )

        app_logger.debug(report_msg)

    def get_job(self) -> Optional[QueuedRequest]:
        """Thread-safely get a request from the queue"""
        result: Optional[QueuedRequest] = None
        with self.lock:
            try:
                result = self.item_deque.popleft()
                app_logger.debug(
                    f"📤 Retrieved job for ticker: {result.ticker if result else 'None'} for sections {result.sections if result else 'None'}"
                )
            except IndexError:
                app_logger.debug("🈚 There is nothing in the job queue")

        return result

    def add_job(self, ticker: str, sections: set[str]) -> QueuedRequest:
        """Thread-safely add a request to the queue and return the request object"""
        request = QueuedRequest(
            ticker=ticker,
            sections=sections,
            timestamp=datetime.now(),
            result_event=tg.Event(),
        )

        with self.lock:
            if len(self.item_deque) < QUEUE_MAX_SIZE:
                self.item_deque.append(request)
                app_logger.debug(
                    f"📥 Added job for ticker: {ticker} - Sections: {sections}"
                )
            else:
                app_logger.debug("🈵 Tried to add a job to the queue but it's full!")
                request.set_error(Exception("Queue is full"))

        return request

    def get_cache_ready_job(self, cache: tsCache) -> Optional[QueuedRequest]:
        """Scan and extract cache-ready job without full reconstruction."""
        with self.lock:
            for i, job in enumerate(self.item_deque):
                cached_data: Optional[FullTickerData] = cache.get_ticker(job.ticker)
                if cached_data and cached_data.has_required_sections(job.sections):
                    del self.item_deque[i]
                    return job
            return None

    def put_job_back(self, job: QueuedRequest) -> None:
        """Put job back at front (O(1) operation)."""
        with self.lock:
            self.item_deque.appendleft(job)
