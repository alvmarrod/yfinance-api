# Changelog

## [0.10.0] - 2026-03-18

### Added

- **Request Bucketing**: Time-windowed request batching to reduce yfinance API calls
  - 3-second window collects incoming requests before processing
  - Deduplication: duplicate requests for the same ticker within the window are merged
  - Union of sections: merged requests fetch all needed sections in one API call
  - Parallel fetching: up to 10 concurrent threads process batched requests
  - Configurable bucket size (default: 100 unique tickers)

### Changed

- Increased `MAX_BUCKET_SIZE` from 50 to 100
- Reduced log verbosity: many cache, queue, and rate-limiter status messages changed from INFO to DEBUG
- Bucket creation and processing now logged at INFO level for observability

### Files Added

- `services/request_bucket.py`: Request bucket with deduplication logic
- `services/batch_processor.py`: Parallel batch processing and result distribution

## [0.9.0] - 2026-01-15

### Changed

- Improved concern separation between `calculations` and `job_dispatcher` modules.
- Enforced a clearer workflow based on first-cache check instead of depending on the cache in a less transparent way.
- Improved exception manage control for HTTP Error 408 from `yfinance`.
- Worker loop reworked:
  - First try to answer any pending job for which we have chached results
  - If none, then proceed to the next `API call` job
- Switch from `queue` to `deque` for less expensive left re-append jobs.

## [0.8.0] - 2026-01-12

### Added

- Lazy loading to avoid hitting `yfinance` limits.

### Changed

- Calculated fields now raise exceptions instead of returning `-1` values for lazy loading logic.

### Removed

- `Cache report` printing on cache checking, remains on cache writing.
- Deprecated `rate_limiter` endpoints from the old limiter API.

## [0.7.0] - 2026-01-11

### Added

- Added `progressbar` painting to `utils` package.
- Added `cache`, `rate_limiter` and `queue` services and classess.
  - All items are thread-safe.
- Encapsulated the usage of those modules via `JobDispatcher` and rely on it to retrieve the ticker data.

### Removed

- Deprecated the previous rate-limit and cache logic, AI generated.

## [0.6.0] - 2026-01-09

### Added

- **Advanced Rate Limiting System**: Complete queue-based rate limiting to prevent yfinance API abuse
  - Configurable rate limits (default: 20 requests per 2 minutes)
  - Thread-safe atomic operations to prevent race conditions
  - Intelligent queue management with FIFO processing
  - Background thread for rate-limited request processing
- **Cache-First Optimization**: Cache hits bypass rate limiting entirely for instant responses
  - Configurable cache expiry (default: 1 hour)
  - Complete `FullTickerData` caching for maximum efficiency
  - Thread-safe cache operations with automatic cleanup
- **HTTP 500 Retry Logic**: Automatic retry system for yfinance server errors
  - Exponential backoff retry strategy (5s, 10s, 20s delays)
  - Configurable retry attempts (default: 3 retries)
  - Request position maintained during retries (no queue jumping)
- **Enhanced Error Handling**: Proper HTTP status codes and timeout management
  - HTTP 408 for request timeouts (180s default)
  - HTTP 500 for server errors after retries exhausted
  - Detailed error logging with request tracking
- **Monitoring & Configuration**: Real-time rate limiting status and configuration
  - `GET /status/rate-limit` endpoint for monitoring
  - `POST /config/rate-limit` endpoint for dynamic configuration
  - Comprehensive logging with cache hits, queue status, and rate limit details
- **Thread-Safe Singleton**: Single rate limiter instance across all requests
  - Double-checked locking pattern for thread safety
  - Graceful shutdown handling with proper cleanup

### Changed

- Removed unused functions at `services/yf_info.py` to retrieve yfinance ticker sub-objects.
- Consolidate yfinance ticker data into a single `FullTickerData` dataclass for easier access to all relevant data.
- Updated functions to return and use such `FullTickerData` instead of separate yfinance objects.
- **Replaced simple `@cache` decorator** with sophisticated rate-limited caching system
- **Updated timeout handling** from 30s to 180s to accommodate queue delays
- **Enhanced API routes** with proper timeout and error handling
- **Integrated rate limiting documentation** into main README.md for better discoverability

### Removed

- Separate `RATE_LIMITING.md` documentation file (integrated into README.md)

## [0.5.0] - 2026-01-08

### Changed

- Updated `yfinance` dependency to version `1.0`

## [0.4.0] - 2025-08-30

### Added

- Calculated `dividendFrequency` which returns an string: `[-|A|S|Q]`
- Calculated `pegRatio` which returns an string: `[-|A|S|Q]`
  - Included alias `peToGrowth`

### Changed

- Updated usage example `sp100_analysis` to avoid showing calculation error and show `-` instead on some columns.

## [0.3.0] - 2025-07-24

### Added

- Added `balance_sheet` and `financials` data into ticker full retrieval.

### Changed

- Split single script file `app.py` into API structure: api, services, utils.
- Added fallback string default value `-` for `get_symbol_value_raw` and `exdividend_to_datetime` in case it doesn't exist.
- Rework of `ROI` calculation to `ROE`, as `ROI` had the same calculation as `Anual Growth`.

## [0.2.0] - 2025-05-22

### Added

- Support for exporting historical stock data as CSV files.
- Endpoints to fetch candlestick historical data.
  - Note this generates a CSV file with the last 60 days of data in the `./data` directory.

### Changed

- Added missing docstrings.
- Enhanced README with detailed setup instructions, API endpoints, and usage examples.

### Removed

- Deleted residual code about `yfinance CachedSession`.

## [0.1.0] - 2025-03-19

### Added

- Basic Flask application exposing partially Yahoo Finance data via API.
- Introduced new financial calculations: ROI ratio, intrinsic value, and growth ratios.
- Added Docker support for easier deployment.
- Cached API responses to reduce load on Yahoo Finance.
