import logging

from flask import Flask

from api.routes import api

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.register_blueprint(api)

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
    except Exception as e:
        logging.exception("An error occurred while running the server: %s", e)
