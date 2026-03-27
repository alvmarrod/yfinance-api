"""
Ticker ranking service for tracking user request frequency.
"""

import logging
import pickle
import threading as tg
from pathlib import Path
from typing import Optional

app_logger = logging.getLogger("yfinance-api")


class TickerRanking:
    """
    Tracks historical request counts for tickers (info block only).
    Only user-initiated requests are tracked, not cron prefetches.
    """

    RANKING_FILE: str = "cache/ticker_ranking.pkl"

    _instance: Optional["TickerRanking"] = None
    _lock: tg.Lock = tg.Lock()

    ranking: dict[str, int]

    def __new__(cls) -> "TickerRanking":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        app_logger.info("🆕 Initializing Ticker Ranking")
        self.ranking = {}
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "TickerRanking":
        """Get the singleton instance."""
        return cls()

    def track_request(self, ticker: str) -> None:
        """Increment count for a ticker."""
        with self._lock:
            self.ranking[ticker] = self.ranking.get(ticker, 0) + 1

    def get_top_n(self, n: int) -> list[str]:
        """Return top N tickers by request count."""
        with self._lock:
            if not self.ranking:
                return []

            sorted_tickers = sorted(
                self.ranking.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            return [ticker for ticker, _ in sorted_tickers[:n]]

    def persist_to_disk(self) -> None:
        """Save ranking to pickle file."""
        with self._lock:
            if not self.ranking:
                app_logger.debug("Ranking is empty, skipping persistence")
                return

            Path("cache").mkdir(exist_ok=True)

            try:
                with open(self.RANKING_FILE, "wb") as f:
                    pickle.dump(self.ranking, f)
                app_logger.info(
                    f"💾 Ticker ranking persisted ({len(self.ranking)} tickers)"
                )
            except Exception as e:
                app_logger.error(f"❌ Failed to persist ticker ranking: {e}")

    def load_from_disk(self) -> None:
        """Load ranking from pickle file."""
        ranking_path = Path(self.RANKING_FILE)

        if not ranking_path.exists():
            app_logger.debug("No ticker ranking file found")
            return

        try:
            with open(ranking_path, "rb") as f:
                self.ranking = pickle.load(f)
            app_logger.info(f"📂 Loaded ticker ranking ({len(self.ranking)} tickers)")
        except Exception as e:
            app_logger.error(f"❌ Failed to load ticker ranking: {e}")
