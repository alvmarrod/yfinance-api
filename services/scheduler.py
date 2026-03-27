"""
Prefetch scheduler using APScheduler for proactive cache warming.
"""

import logging
from typing import Optional
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.cache_config import CacheConfig
from services.cron_queue import tsCronQueue

app_logger = logging.getLogger("yfinance-api")


class PrefetchScheduler:
    """
    Scheduler for proactive cache prefetching.
    Creates one cron job per block type using the config's prefetch_schedule.
    """

    scheduler: Optional[BackgroundScheduler]
    config: CacheConfig
    cron_queue: tsCronQueue
    last_prefetch_timestamps: dict[str, datetime]

    def __init__(self, config: CacheConfig, cron_queue: tsCronQueue):
        self.scheduler = None
        self.config = config
        self.cron_queue = cron_queue
        self.last_prefetch_timestamps = {}

    def start(self) -> None:
        """Start all cron jobs from config."""
        if self.scheduler and self.scheduler.running:
            app_logger.warning("⚠️ Scheduler already running")
            return

        self.scheduler = BackgroundScheduler()

        for block, cron_expr in self.config.prefetch_schedule.schedule.items():
            self.scheduler.add_job(
                self._prefetch_block,
                CronTrigger.from_crontab(cron_expr),
                args=[block],
                id=f"prefetch_{block}",
                name=f"Prefetch {block}",
            )
            app_logger.debug(f"📅 Scheduled prefetch job for '{block}': {cron_expr}")

        self.scheduler.start()
        app_logger.info(
            f"🚀 Prefetch scheduler started with {len(self.config.prefetch_schedule.schedule)} jobs"
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            app_logger.info("🛑 Prefetch scheduler stopped")

    def _prefetch_block(self, block: str) -> None:
        """Prefetch a block for top N tickers."""
        from services.ticker_ranking import TickerRanking

        ranking = TickerRanking.get_instance()
        top_tickers = ranking.get_top_n(self.config.proactive_fetch_top_n)

        if not top_tickers:
            app_logger.debug(f"📊 No tickers to prefetch for {block}")
            return

        before_count = self.cron_queue.queue_size()
        count = 0

        for ticker in top_tickers:
            self.cron_queue.add_job(ticker, {block})
            count += 1

        self.last_prefetch_timestamps[block] = datetime.now()

        after_count = self.cron_queue.queue_size()
        app_logger.info(
            f"📊 Cron job '{block}': added {count} jobs, queue: {before_count} → {after_count}"
        )
