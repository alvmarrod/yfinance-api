
#PYTHON_EXEC=python3.13
PYTHON_EXEC=python3.11

SERVICE_NAME=yahoo_finance_api
CONTAINER_NAME=yfinance_api_instance

build-docker:
	docker build -t $(SERVICE_NAME) .

run-docker:
	docker run -d -p 5000:5000 --name $(CONTAINER_NAME) $(SERVICE_NAME)

run-local:
	@if [ ! -d "test_env" ]; then $(PYTHON_EXEC) -m venv test_env; fi
	@./test_env/bin/activate; python -m pip install --upgrade --no-cache-dir -r requirements.txt
	@FLASK_APP=app FLASK_ENV=development
	python -m flask run --host=0.0.0.0
	@deactivate