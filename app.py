import logging
import atexit
import signal
import sys

from flask import Flask

from api.routes import api

app_logger = logging.getLogger("yfinance-api")

app_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app_logger.addHandler(handler)

app = Flask(__name__)
app.register_blueprint(api)

_pickle_cache_on_exit = True


def _persist_cache() -> None:
    """Persist cache to disk."""
    global _pickle_cache_on_exit
    if not _pickle_cache_on_exit:
        return

    try:
        from services.cache import tsCache

        cache = tsCache()
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
    try:
        from services.cache import tsCache
        from services.job_dispatcher import get_dispatcher

        cache = tsCache()
        expired_tickers = cache.load_from_disk()

        if expired_tickers:
            app_logger.info(
                f"🔥 {len(expired_tickers)} expired cache entries, scheduling warmup..."
            )

            dispatcher = get_dispatcher()

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
        from services.job_dispatcher import shutdown_dispatcher

        shutdown_dispatcher()
        app_logger.info("✅ Job dispatcher cleaned up successfully")
    except Exception as e:
        app_logger.error(f"Error during cleanup: {e}")


atexit.register(cleanup)

signal.signal(signal.SIGINT, _signal_handler)

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
