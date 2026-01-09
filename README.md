# yfinance-api

<p align="center">
  <img alt="Docker Python Version" src="https://img.shields.io/badge/python-3.13-blue">
  <img alt="GitHub Tag" src="https://img.shields.io/github/v/tag/alvmarrod/yfinance-api">
  <img alt="GitHub License" src="https://img.shields.io/github/license/alvmarrod/yfinance-api">
</p>

## Overview

This project provides a RESTful API to interact with Yahoo Finance data. It allows users to fetch stock information, historical data, and perform calculations such as ROI, intrinsic value, and more.

Notice that this API is not a complete replacement for Yahoo Finance, but rather a simplified interface to access some of its features for personal use.

## Features

- Fetch real-time stock data.
- Calculate financial metrics like ROI, intrinsic value, and growth ratios.
- Export historical stock data in CSV format.
- **Rate limiting with intelligent caching** to prevent API abuse and improve performance.

## Requirements

- Flask
- yfinance
  - Beware that an outdated `yfinance` version may break all your requests to the API.
- pandas

## Setup

### Local Environment
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd yfinance-api
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python3.12 -m venv test_env
   source test_env/bin/activate
   pip install --upgrade --no-cache-dir -r requirements.txt
   ```
3. Run the application:
   ```bash
   FLASK_APP=app FLASK_ENV=development flask run --host=0.0.0.0
   ```

### Docker
1. Build the Docker image:
   ```bash
   docker build -t yahoo_finance_api .
   ```
2. Run the Docker container:
   ```bash
   docker run -d -p 5001:5000 --name yfinance_api_instance yahoo_finance_api
   ```

## API Endpoints

### Base URL

`http://<host>:<port>`

### Endpoints

- **GET `/symbol/<tag>`**: Fetch all available data for a stock symbol.
- **GET `/symbol/<tag>/<field>/`**: Fetch a specific field's value in JSON format.
- **GET `/symbol/<tag>/<field>/raw`**: Fetch a specific field's raw value for a stock symbol.
- **GET `/symbol/historic/candle/<tag>`**: Download historical stock data as a CSV file, using the `5m` interval resolution and the maximum available period of 60 days.

### Example Usage

Fetch the ROI ratio for a stock:

```bash
curl http://localhost:5001/symbol/AAPL/ROE/
```

### Alias and Calculated Fields

- Some fields have aliases for easier access. They are defined as a constant map: `USUAL_FIELDS`.
- `yfinance` provides a set of parameters, but sometimes we want non-inmediate values that can be calculated from the data. Aiming to provide a more user-friendly experience, we have created a set of calculated fields that can be accessed via the API.
- The calculated fields are defined in the `CALCULATED_FIELDS` constant map.
- The API will return the calculated value for these fields as part of the response.

## Rate Limiting

The API includes intelligent rate limiting to prevent hitting yfinance API limits while maintaining performance.

### Default Configuration
- **20 requests per 2 minutes** to yfinance
- **1-hour cache** for all ticker data  
- **180-second timeout** for requests
- **Automatic retries** for HTTP 500 errors

### Key Features
- **Cache-first optimization**: Cached data bypasses rate limiting entirely
- **Queue management**: Requests are queued when rate limits are hit
- **Intelligent retries**: HTTP 500 errors auto-retry with exponential backoff
- **Thread-safe**: Single rate limiter instance handles all requests

### Monitoring
```bash
# Check rate limit status
curl http://localhost:5000/status/rate-limit

# Configure rate limits (optional)
curl -X POST http://localhost:5000/config/rate-limit \
  -H "Content-Type: application/json" \
  -d '{"max_requests_per_2min": 15, "cache_expiry_hours": 2}'
```

### HTTP Status Codes
- **200**: Success (cache hit or fresh data)
- **408**: Request timeout (queue backed up)  
- **500**: Server error (after retries failed)

## Development

- The project implements intelligent **rate limiting and caching** instead of `yfinance`'s `CachedSession` (which didn't work as expected)
- **Cache-first strategy**: Popular tickers get instant responses, reducing API calls
- **Queue-based processing**: Handles high load gracefully without hitting rate limits
- Calculations for financial metrics are implemented at [calculations.py](services/calculations.py)

## FAQ / Troubleshooting

- Q: The service was working fine, and suddenly it has stopped retrieving the data! What can I do?
  - A: Most probably, if nothing else changed, `Yahoo Finance` updates broke the current `yfinance` version that you are using. Go to the [requirements.txt](requirements.txt) file and update the version of `yfinance`, which is fixed to the latest one available. Do not forget to install the new dependency version or re-build your docker image, before running your service again.

## Version

Find the version of the API in the [version.txt](version.txt) file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
