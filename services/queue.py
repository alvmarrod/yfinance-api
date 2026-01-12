"""
Module that implements a thread-safe queue manager
"""
import logging

import threading as tg
from typing import Optional
from datetime import datetime
from queue import Queue, Empty, Full

from utils.progressbar import create_progress_bar

from services.queued_request import QueuedRequest

app_logger = logging.getLogger('yfinance-api')

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
    Thread safe Queue object for processing ticker data requests
    """

    lock: tg.Lock
    item_queue: Queue[QueuedRequest]

    def __init__(self):
        app_logger.info("🆕 Initializating a queue")
        self.lock = tg.Lock()
        self.item_queue = Queue()

    def queue_size(self) -> int:
        """Return the current size of the queue"""
        with self.lock:
            return self.item_queue.qsize()
        
    def _queue_usage_report(self) -> None:
        """Reports the current status of the queue usage"""
        report_msg: str = QUEUE_SIZE_LOG_MSG % create_progress_bar(
            current=self.queue_size(),
            total=QUEUE_MAX_SIZE,
            width=10
        )

        app_logger.info(report_msg)

    def get_job(self) -> Optional[QueuedRequest]:
        """Thread-safely get a request from the queue"""
        result: Optional[QueuedRequest] = None
        with self.lock:
            try:
                result = self.item_queue.get(block=False)
                app_logger.debug(f"📤 Retrieved job for ticker: {result.ticker if result else 'None'}")
            except Empty:
                app_logger.debug("🈚 There is nothing in the job queue")
        
        return result

    def add_job(self, ticker: str, sections: set[str]) -> QueuedRequest:
        """Thread-safely add a request to the queue and return the request object"""
        request = QueuedRequest(
            ticker=ticker,
            sections=sections,
            timestamp=datetime.now(),
            result_event=tg.Event()
        )

        with self.lock:
            try:
                self.item_queue.put(request, block=False)
                app_logger.debug(f"📥 Added job for ticker: {ticker} - Sections: {sections}")
            except Full:
                app_logger.debug("🈵 Tried to add a job to the queue but it's full!")
                request.set_error(Exception("Queue is full"))

        return request
