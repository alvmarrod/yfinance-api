import logging
import atexit

from flask import Flask

from api.routes import api

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.register_blueprint(api)

# Register cleanup function for graceful shutdown
def cleanup():
    """Clean up resources on shutdown."""
    try:
        from services.job_dispatcher import shutdown_dispatcher
        shutdown_dispatcher()
        logging.info("Job dispatcher cleaned up successfully")
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

atexit.register(cleanup)

##############################################################################
#                                    MAIN                                    #
##############################################################################

if __name__ == "__main__":
    try:
        logging.info("Starting yfinance-api Flask server...")
        logging.info("Listening on http://0.0.0.0:5000")
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logging.info("User used (Ctrl+C). Shutting down gracefully.")
        cleanup()
    except Exception as e:
        logging.exception("An error occurred while running the server: %s", e)
        cleanup()
