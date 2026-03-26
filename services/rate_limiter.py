"""
Rate limiting service for API calls.
"""

import logging
import threading as tg
from typing import Optional

from datetime import datetime, timedelta

from utils.progressbar import create_progress_bar

app_logger = logging.getLogger("yfinance_api")

##############################################################################
#                                CONSTANTS                                   #
##############################################################################

RATE_LIMITER_LOG_MSG: str = "📊 Rate Limiter status: %s"

##############################################################################
#                                RATE LIMITER                                #
##############################################################################


class tsRateLimiter:
    """Thread-safe rate limiter.

    To avoid hitting API rate limits, this class tracks the number of events
    and ensures an immediate rate of events and a more averaged rate.

    Averaged rate: per 2 minutes
    """

    lock: tg.Lock
    event_register: list[datetime]

    max_ratio: float
    yfinance_408_hit: Optional[datetime]

    _request_period_seconds: int
    _max_requests_per_period: int
    _cooldown_seconds: int
    _cooldown_fake_events: int

    def __init__(
        self,
        request_period_seconds: int = 120,
        max_requests_per_period: int = 65,
        cooldown_seconds: int = 80,
        cooldown_fake_events: int = 10,
    ):
        app_logger.info("🆕 Initializating the Rate Limiter")
        self.lock = tg.Lock()
        self.event_register = []

        self._request_period_seconds = request_period_seconds
        self._max_requests_per_period = max_requests_per_period
        self._cooldown_seconds = cooldown_seconds
        self._cooldown_fake_events = cooldown_fake_events

        self.max_ratio = max_requests_per_period / request_period_seconds
        self.yfinance_408_hit = None

    def _current_ratio(self) -> float:
        """Returns the current event ratio

        In charge of deleting obsolete events"""
        should_delete: list[bool] = [
            ts + timedelta(seconds=self._request_period_seconds) < datetime.now()
            for ts in self.event_register
        ]

        for delete, item in zip(should_delete, self.event_register):
            if delete:
                self.event_register.remove(item)

        return len(self.event_register) / self._request_period_seconds

    def _rate_limiter_report(self) -> None:
        """Reports the current status of the rate limiter"""
        report_msg: str = RATE_LIMITER_LOG_MSG % create_progress_bar(
            current=len(self.event_register),
            total=self._max_requests_per_period,
            width=10,
        )

        app_logger.debug(report_msg)

    def yfinance_api_report_rate_limit_hit(self) -> None:
        """Registers a hit to the yfinance API rate limit (HTTP 408)"""
        app_logger.warning("🚨 yfinance API reported rate limit hit")

        self.yfinance_408_hit = datetime.now()
        app_logger.warning("⚠️  Hit yfinance API rate limit (HTTP 408).")

    def _yfinance_api_slow_start(self) -> None:
        """Adds fake events to slowly ramp up the rate after a yfinance API rate limit hit"""
        app_logger.warning(
            "🚨 Entering conservative mode - Adding %d fake events",
            self._cooldown_fake_events,
        )

        current_time = datetime.now()
        for i in range(self._cooldown_fake_events):
            self.event_register.append(current_time + timedelta(seconds=i))

    def ratio_allows(self) -> bool:
        """Returns if given the current ratio we should proceed.

        If allowed, registers an event in the current timestamp

        Also checks if we are still in cooldown after hitting the yfinance API rate limit
        """
        should_allow: bool = False

        with self.lock:
            if self.yfinance_408_hit is not None:
                cooldown_over: bool = (
                    self.yfinance_408_hit + timedelta(seconds=self._cooldown_seconds)
                    < datetime.now()
                )

                if cooldown_over:
                    app_logger.info("✅ yfinance API rate limit cooldown is over")
                    self.yfinance_408_hit = None

                    self._yfinance_api_slow_start()

            self._rate_limiter_report()
            should_allow = self._current_ratio() < self.max_ratio

            if should_allow:
                self.event_register += [datetime.now()]

        return should_allow
