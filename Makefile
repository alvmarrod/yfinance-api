
PYTHON_EXEC=python3

SERVICE_NAME=yahoo_finance_api
CONTAINER_NAME=yfinance_api_instance

build-docker:
	docker build -t $(SERVICE_NAME) .

run-docker:
	docker run \
		--mount type=bind,source="$(PWD)/cache",target=/app/cache \
		--mount type=bind,source="$(PWD)/cache_config.json",target=/app/cache_config.json \
		-e CACHE_CONFIG_PATH=/app/cache_config.json \
		-d -p 5001:5000 --name $(CONTAINER_NAME) $(SERVICE_NAME)

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down
