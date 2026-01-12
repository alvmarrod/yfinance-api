import logging
import atexit

from flask import Flask

app_logger = logging.getLogger('yfinance-api')

app_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app_logger.addHandler(handler)

from api.routes import api

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
        app_logger.info("Starting yfinance-api Flask server...")
        app_logger.info("Listening on http://0.0.0.0:5000")
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        app_logger.info("User used (Ctrl+C). Shutting down gracefully.")
        cleanup()
    except Exception as e:
        app_logger.exception("An error occurred while running the server: %s", e)
        cleanup()
