import logging
import os
import atexit
import signal
import sys
from typing import TYPE_CHECKING, Optional

from flask import Flask

from api.routes import api

if TYPE_CHECKING:
    from services.cache_config import CacheConfig

app_logger = logging.getLogger("yfinance-api")

app_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app_logger.addHandler(handler)

app = Flask(__name__)
app.register_blueprint(api)

_pickle_cache_on_exit = True
_cache_config: Optional["CacheConfig"] = None


def _load_cache_config() -> "Optional[CacheConfig]":
    """Load cache configuration from file."""
    global _cache_config

    try:
        from services.cache_config import load_config
        from services.cache import tsCache

        config_path = os.environ.get("CACHE_CONFIG_PATH", "./cache_config.json")
        app_logger.info(f"📁 Loading cache config from: {config_path}")

        config = load_config(config_path)
        _cache_config = config

        cache = tsCache.get_instance()
        cache.configure(
            adaptive_cache=config.adaptive_cache,
            cache_size=config.cache_size,
            ttl_seconds=config.ttl_seconds.ttl,
        )

        app_logger.info("🗂️ Cache configuration loaded:")
        app_logger.info(f"   Blocks: {len(config.blocks)}")
        app_logger.info(f"   Concurrency: {config.concurrency}")
        app_logger.info(f"   Cache size: {config.cache_size}")
        app_logger.info(f"   Adaptive cache: {config.adaptive_cache}")
        app_logger.info(f"   Proactive fetch top N: {config.proactive_fetch_top_n}")
        app_logger.info(
            f"   Prefetch schedules: {len(config.prefetch_schedule.schedule)}"
        )
        app_logger.info(f"   TTL entries: {len(config.ttl_seconds.ttl)}")

        return config

    except Exception as e:
        app_logger.error(f"❌ Failed to load cache config: {e}")
        return None


def _reload_handler(signum, frame) -> None:
    """Handle SIGHUP to reload configuration without restarting."""
    global _cache_config

    app_logger.info("🔄 Received SIGHUP, reloading cache configuration...")

    try:
        config = _load_cache_config()
        if config:
            from services.job_dispatcher import get_dispatcher

            dispatcher = get_dispatcher()
            dispatcher.configure_scheduler(config)
            app_logger.info("🔄 Scheduler reconfigured with new config")
    except Exception as e:
        app_logger.error(f"Error reloading config: {e}")


def _persist_cache() -> None:
    """Persist cache to disk."""
    global _pickle_cache_on_exit
    if not _pickle_cache_on_exit:
        return

    try:
        from services.cache import tsCache

        cache = tsCache.get_instance()
        cache.persist_to_disk()
    except Exception as e:
        app_logger.error(f"Error persisting cache: {e}")


def _signal_handler(signum, frame) -> None:
    """Handle Ctrl+C signal to persist cache before exit."""
    app_logger.info("🛑 Received shutdown signal, persisting cache...")
    _persist_cache()
    sys.exit(0)


def _load_cache_on_startup() -> None:
    """Load cache from pickle file and warmup expired entries."""
    global _cache_config

    try:
        from services.cache import tsCache
        from services.job_dispatcher import get_dispatcher
        from services.ticker_ranking import TickerRanking

        # Load ticker ranking
        ranking = TickerRanking.get_instance()
        ranking.load_from_disk()

        cache = tsCache.get_instance()
        expired_tickers = cache.load_from_disk()

        dispatcher = get_dispatcher()

        if _cache_config:
            dispatcher.configure_scheduler(_cache_config)

        if expired_tickers:
            app_logger.info(
                f"🔥 {len(expired_tickers)} expired cache entries, scheduling warmup..."
            )

            for expired in expired_tickers:
                dispatcher.warmup_ticker(expired.ticker, expired.cached_sections)

    except Exception as e:
        app_logger.error(f"Error loading cache on startup: {e}")


def cleanup():
    """Clean up resources on shutdown."""
    global _pickle_cache_on_exit

    try:
        _persist_cache()
        app_logger.info("💾 Cache persisted on shutdown")
    except Exception as e:
        app_logger.error(f"Error during cache persistence: {e}")

    try:
        from services.ticker_ranking import TickerRanking

        ranking = TickerRanking.get_instance()
        ranking.persist_to_disk()
        app_logger.info("💾 Ticker ranking persisted on shutdown")
    except Exception as e:
        app_logger.error(f"Error persisting ticker ranking: {e}")

    try:
        from services.job_dispatcher import shutdown_dispatcher

        shutdown_dispatcher()
        app_logger.info("✅ Job dispatcher cleaned up successfully")
    except Exception as e:
        app_logger.error(f"Error during cleanup: {e}")


atexit.register(cleanup)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGHUP, _reload_handler)

_load_cache_config()


def get_cache_config() -> "Optional[CacheConfig]":
    """Get the current cache configuration."""
    return _cache_config


_load_cache_on_startup()

##############################################################################
#                                    MAIN                                    #
##############################################################################

if __name__ == "__main__":
    try:
        app_logger.info("Starting yfinance-api Flask server...")
        app_logger.info("Listening on http://0.0.0.0:5000")
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        app_logger.info("User used (Ctrl+C). Shutting down gracefully.")
        cleanup()
    except Exception as e:
        app_logger.exception("An error occurred while running the server: %s", e)
        cleanup()
