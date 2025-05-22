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
  - These metrics are 
- Export historical stock data in CSV format.
- Rate-limited API to prevent excessive requests.

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
- **GET `/symbol/<tag>/<field>/raw`**: Fetch a specific field's raw value for a stock symbol.
- **GET `/symbol/<tag>/<field>/`**: Fetch a specific field's value in JSON format.
- **GET `/symbol/historic/candle/<tag>`**: Download historical stock data as a CSV file, using the `5m` interval resolution and the maximum available period of 60 days.

### Example Usage

Fetch the ROI ratio for a stock:

```bash
curl http://localhost:5001/symbol/AAPL/ROIRatio/
```

### Alias and Calculated Fields

- Some fields have aliases for easier access. They are defined as a constant map: `USUAL_FIELDS`.
- `yfinance` provides a set of parameters, but sometimes we want non-inmediate values that can be calculated from the data. Aiming to provide a more user-friendly experience, we have created a set of calculated fields that can be accessed via the API.
- The calculated fields are defined in the `CALCULATED_FIELDS` constant map.
- The API will return the calculated value for these fields as part of the response.

## Development

- The project doesn't use yfinance `CachedSession`, as it has been tested and did not work as expected.
- To counter this issue, we have implemented some `caching` mechanisms to avoid excessive requests to Yahoo Finance.
- Calculations for financial metrics are implemented in `app.py`.

## Version

Find the version of the API in the [version.py](version.py) file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.