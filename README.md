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

- Rate limiter (configurable)
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

### Docker Compose (Recommended)

#### Initial Deployment

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd yfinance-api
   ```

2. Ensure `cache_config.json` exists in the project root.

3. Build and start:
   ```bash
   docker compose up -d
   ```

4. Verify the service:
   ```bash
   curl http://localhost:5001/health
   ```

The `cache/` directory is created automatically on first run.

#### Upgrading the Service

To upgrade to a new version:

```bash
# 1. Pull latest changes
git pull

# 2. Rebuild and restart (preserves cache)
docker compose down
docker compose up -d --build
```

The `cache/` directory is mounted as a volume, so cache data persists across restarts.

#### Hot Reload Configuration

To reload configuration without restarting:

```bash
docker kill --signal=HUP yfinance_api_instance
```

This reloads `cache_config.json` and reconfigures the scheduler.

#### Manual Docker Setup

```bash
# Build
make build-docker

# Run (with cache and config mounts)
make run-docker
```

#### Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./cache` | `/app/cache` | Cache persistence |
| `./cache_config.json` | `/app/cache_config.json` | Configuration |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_CONFIG_PATH` | `./cache_config.json` | Path to cache configuration file |

### cache_config.json

The main configuration file. The `cache/` directory is created automatically on first run.

```json
{
  "tickers": ["AAPL", "GOOGL"],
  "blocks": ["info", "financials", "balance_sheet", "dividends"],
  "concurrency": 1,
  "adaptive_cache": false,
  "cache_size": 100,
  "prefetch_schedule": {
    "info": "15 * * * *",
    "dividends": "0 0 */1 * *"
  },
  "ttl_seconds": {
    "info": 3600,
    "dividends": 86400
  },
  "pending_ticker_window_seconds": 1,
  "seconds_sleep_when_rate_hit": 5,
  "rate_limiter": {
    "request_period_seconds": 120,
    "max_requests_per_period": 65,
    "cooldown_seconds": 80,
    "cooldown_fake_events": 10
  }
}
```

#### Core Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tickers` | list[str] | [] | Stock symbols to track |
| `blocks` | list[str] | [] | Data blocks to fetch (info, financials, etc.) |
| `concurrency` | int | 1 | Max parallel fetches for pre-fetch jobs |

#### Cache Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `adaptive_cache` | bool | false | If true, no max cache size |
| `cache_size` | int | 100 | Max tickers in memory |
| `ttl_seconds` | dict | {} | Time-to-live per block (seconds) |

#### Scheduler Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prefetch_schedule` | dict | {} | Cron expression per block |

#### Rate Limiter Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `request_period_seconds` | int | 120 | Time window for rate tracking |
| `max_requests_per_period` | int | 65 | Max requests per window |
| `cooldown_seconds` | int | 80 | Cooldown after API rate limit hit |
| `cooldown_fake_events` | int | 10 | Fake events for slow ramp-up |

##### Rate Limiter Behavior

When Yahoo Finance returns HTTP 408 (rate limit), the system:

1. **Blocks all requests** for `cooldown_seconds` (80s default)
2. **After cooldown**, adds `cooldown_fake_events` (10) fake events to the register
3. **Resumes at reduced rate** - only (65 - 10) = 55 real slots available

This prevents immediately hitting the rate limit again after recovery.

#### Pending Ticker Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pending_ticker_window_seconds` | float | 1 | Window to batch requests per ticker |
| `seconds_sleep_when_rate_hit` | float | 5 | Sleep duration when rate limited |

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
- Reconfigures rate limiter

In Docker:
```bash
docker kill --signal=HUP yfinance_api_instance
```

## API Endpoints

### Base URL

`http://<host>:<port>`

### Health & Monitoring

- **GET `/health`**: Health check for container orchestration
- **GET `/cache/status`**: Cache statistics and scheduler status

### Symbol Endpoints

- **GET `/symbol/<tag>`**: Fetch all available data for a stock symbol
  - Optional query parameters:
    - `start` (YYYY-MM-DD): Start date for the history block
    - `end` (YYYY-MM-DD): End date for the history block
  - When `start` or `end` is provided, the `history` block is replaced with data for the requested range.
  - Maximum allowed range is 365 days. If only one bound is provided, the other is computed to form a 1-year window.
  - Date-range requests bypass the cache and are serialized with a 5-second cooldown.
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

# Fetch FX data for a specific date range
curl "http://localhost:5001/symbol/JPYEUR=X?start=2024-01-01&end=2024-06-01"
```

### Alias and Calculated Fields

- Some fields have aliases for easier access defined in `USUAL_FIELDS`
- Calculated fields are defined in `CALCULATED_FIELDS`

## Development

- **Rate limiting**: Configurable via `cache_config.json`
- **Cache-first strategy**: Popular tickers get instant responses
- **Queue-based processing**: Handles high load gracefully
- **Pre-fetch scheduler**: Proactive caching using APScheduler

### Pre-commit Hooks

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
