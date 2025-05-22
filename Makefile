
PYTHON_EXEC=python3

SERVICE_NAME=yahoo_finance_api
CONTAINER_NAME=yfinance_api_instance

build-docker:
	docker build -t $(SERVICE_NAME) .

run-docker:
	docker run --mount type=bind,source="$(PWD)/data",target=/app/data -d -p 5001:5000 --name $(CONTAINER_NAME) $(SERVICE_NAME)
