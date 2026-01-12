"""
Rate limiting service for API calls.
"""
import logging
import threading as tg

from dataclasses import dataclass
from datetime import datetime, timedelta

from utils.progressbar import create_progress_bar

app_logger = logging.getLogger("yfinance_api")

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

IMMEDIATE_REQUEST_PERIOD_SECONDS: int = 20
IMMEDIATE_MAX_REQUESTS_PER_PERIOD: int = 10

REQUEST_PERIOD_SECONDS: int = 120
MAX_REQUESTS_PER_PERIOD: int = 65

RATE_LIMITER_LOG_MSG: str = "📊 Rate Limiter status: %s"

##############################################################################
#                                RATE LIMITER                                #
##############################################################################

class tsRateLimiter:
    """Thread-safe rate limiter.
    
    To avoid hitting API rate limits, this class tracks the number of events
    and ensures an immediate rate of events and a more averaged rate.
    
    Immediate rate: per 20 secons
    Averaged rate: per 2 minutes
    """

    lock: tg.Lock
    event_register: list[datetime]

    max_ratio: float

    def __init__(self):
        app_logger.info("🆕 Initializating the Rate Limiter")
        self.lock = tg.Lock()
        self.event_register = []

        self.max_ratio = MAX_REQUESTS_PER_PERIOD / REQUEST_PERIOD_SECONDS

    def _current_ratio(self) -> float:
        """Returns the current event ratio
        
        In charge of deleting obsolete events"""
        should_delete: list[bool] = [ts + timedelta(seconds=REQUEST_PERIOD_SECONDS) < datetime.now() for ts in self.event_register]

        for delete, item in zip(should_delete, self.event_register):
            if delete:
                self.event_register.remove(item)
        
        return len(self.event_register) / REQUEST_PERIOD_SECONDS

    def _rate_limiter_report(self) -> None:
        """Reports the current status of the rate limiter"""
        report_msg: str = RATE_LIMITER_LOG_MSG % create_progress_bar(
            current=len(self.event_register),
            total=MAX_REQUESTS_PER_PERIOD,
            width=10
        )

        app_logger.info(report_msg)

    def ratio_allows(self) -> bool:
        """Returns if given the current ratio we should proceed.
        
        If allowed, registers an event in the current timestamp"""
        self._rate_limiter_report()
        should_allow: bool =  self._current_ratio() < self.max_ratio

        if should_allow:
            self.event_register += [datetime.now()]
        
        return should_allow
