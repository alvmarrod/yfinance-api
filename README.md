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

Systems:

- Rate limiter
- Cache (with LRU eviction and disk offload)
- Job Queue (regular + cron)
- Pre-fetch scheduler

## Requirements

- Python 3.13
- Flask
- yfinance (beware that an outdated version may break all requests)
- pandas
- APScheduler

## Setup

### Local Environment
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd yfinance-api
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python3.13 -m venv test_env
   source test_env/bin/activate
   pip install --upgrade --no-cache-dir -r requirements.txt
   ```
3. Run the application:
   ```bash
   python3 app.py
   ```

### Docker

1. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Or manually with Docker:
   ```bash
   make build-docker
   make run-docker
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_CONFIG_PATH` | `./cache_config.json` | Path to cache configuration file |

### Cache Configuration (`cache_config.json`)

```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT"],
  "blocks": ["info", "financials", "balance_sheet", "dividends"],
  "concurrency": 1,
  "adaptive_cache": false,
  "cache_size": 100,
  "prefetch_schedule": {
    "info": "15 * * * *",
    "dividends": "0 0 */1 * *",
    "financials": "2 0 */1 * *"
  },
  "ttl_seconds": {
    "info": 3600,
    "dividends": 86400,
    "financials": 86400
  }
}
```

**Fields:**
- `tickers`: List of stock symbols to track
- `blocks`: Data blocks to fetch (info, financials, balance_sheet, etc.)
- `concurrency`: Max parallel fetches for pre-fetch jobs
- `adaptive_cache`: If true, no max cache size
- `cache_size`: Max tickers in memory (when adaptive_cache is false)
- `prefetch_schedule`: Cron expression per block for proactive caching
- `ttl_seconds`: Time-to-live per block

## Cache Behavior

### Persistence

- Cache is persisted to disk on shutdown (Ctrl+C)
- Cache is loaded from disk on startup
- Disk structure: `cache/{ticker}/{block}.pkl`

### LRU Eviction

When memory cache is full:
1. Oldest ticker (by max block access time) is evicted to disk
2. On next read, disk is checked and loaded back if not expired
3. Expired blocks are automatically deleted

### SIGHUP Hot Reload

Send `kill -HUP <pid>` to reload configuration without restarting:
- Reloads `cache_config.json`
- Reconfigures scheduler

## API Endpoints

### Base URL

`http://<host>:<port>`

### Endpoints

- **GET `/health`**: Health check for container orchestration
- **GET `/cache/status`**: Cache statistics and scheduler status
- **GET `/symbol/<tag>`**: Fetch all available data for a stock symbol
- **GET `/symbol/<tag>/<field>/`**: Fetch a specific field's value
- **GET `/symbol/<tag>/<field>/raw`**: Fetch raw field value
- **GET `/symbol/historic/candle/<tag>`**: Download historical data as CSV

### Example Usage

```bash
# Health check
curl http://localhost:5001/health

# Cache status
curl http://localhost:5001/cache/status

# Fetch ROE ratio
curl http://localhost:5001/symbol/AAPL/ROE/
```

### Alias and Calculated Fields

- Some fields have aliases for easier access defined in `USUAL_FIELDS`
- Calculated fields are defined in `CALCULATED_FIELDS`

## Development

- **Rate limiting**: Configurable via `cache_config.json`
- **Cache-first strategy**: Popular tickers get instant responses
- **Queue-based processing**: Handles high load gracefully
- **Pre-fetch scheduler**: Proactive caching using APScheduler

## Pre-commit Hooks

1. Install pre-commit:
   ```bash
   brew install pre-commit  # macOS
   pip install pre-commit   # Alternative
   ```

2. Set up hooks:
   ```bash
   pre-commit install
   ```

3. Run manually:
   ```bash
   pre-commit run --all-files
   pre-commit run ruff --all-files
   ```

## Version

Find the version in [version.txt](version.txt).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
