# Changelog

## [0.19.0] - 2026-03-19

### Changed

- **README.md**: Comprehensive documentation update
  - Expanded configuration section with all fields documented
  - Detailed rate limiter behavior explanation (cooldown, fake events)
  - Docker Compose deployment instructions (initial, upgrade, hot reload)
  - Volume mount documentation
  - SIGHUP hot reload for Docker

## [0.18.0] - 2026-03-19

### Added

- **External Config for Rate Limiter**: Moved rate limiter constants to `cache_config.json`
  - New `rate_limiter` section with configurable values
  - `request_period_seconds`: Time period for rate tracking (default: 120s)
  - `max_requests_per_period`: Max requests per period (default: 65)
  - `cooldown_seconds`: Cooldown after API rate limit hit (default: 80s)
  - `cooldown_fake_events`: Fake events for slow start after cooldown (default: 10)

### Changed

- Rate limiter now receives values from config instead of module constants
- Rate limiter is recreated when config is reloaded via SIGHUP

## [0.17.0] - 2026-03-19

### Added

- **External Config for PendingTicker**: Moved timing constants to `cache_config.json`
  - `pending_ticker_window_seconds`: Timer window for PendingTicker (default: 1s)
  - `seconds_sleep_when_rate_hit`: Sleep duration when rate limited (default: 5s)

### Changed

- PendingTicker now receives timing values from config instead of module constants
- Default values: window=1s (was 20s), rate_limit_sleep=5s (was 1s)

## [0.16.0] - 2026-03-19

### Added

- **Health Endpoint**: `GET /health` for container orchestration
- **Cache Status Endpoint**: `GET /cache/status` with detailed metrics
  - Memory and disk ticker counts
  - Configuration summary
  - Scheduler status and last prefetch timestamps
  - Queue sizes (regular and cron)
- **Docker Compose**: New `docker-compose.yml` with proper volume mounts
- **Prefetch Timestamps**: Scheduler tracks last prefetch time per block

### Changed

- **Dockerfile**: Updated to copy all source files, create cache directory
- **Makefile**: Added cache/config mounts and docker-compose targets
- **README.md**: Comprehensive update with new documentation
- **.gitignore**: Added `cache/` directory

## [0.15.0] - 2026-03-19

### Added

- **Proactive Pre-fetch Jobs**: APScheduler-based cache warming
  - One cron job per block type using `prefetch_schedule` from config
  - Each job fetches all tickers for its block type
  - Separate cron queue with unlimited capacity (no timeout)
  - Worker processes regular queue first, then cron queue
  - Logging shows queue size before/after each cron batch
- **New files**:
  - `services/cron_queue.py`: Unlimited thread-safe queue for cron jobs
  - `services/scheduler.py`: APScheduler wrapper for prefetch jobs
- **APScheduler dependency** added to requirements.txt

### Changed

- Worker loop now processes regular queue before cron queue
- Scheduler lifecycle tied to `start_worker()`/`stop_worker()`
- Config reload via SIGHUP also reconfigures scheduler

## [0.14.0] - 2026-03-19

### Added

- **Per-Block Retrieval Times**: Each block in `FullTickerData` now has its own retrieval time
- **LRU Eviction with Disk Offload**: When memory cache is full, evict oldest ticker to disk
  - Disk structure: `cache/{ticker}/{block}.pkl` and `cache/{ticker}/metadata.pkl`
  - On memory miss, check disk and load back if not expired
  - Expired block files are automatically deleted
- **New `FullTickerData` methods**:
  - `get_max_block_time()`: Most recent block access time
  - `get_block_sections()`: Set of blocks with data

### Changed

- Cache now uses `FullTickerData` directly (removed `CacheEntry` wrapper)
- Cache now uses configurable `ttl_seconds` per block (from config)
- Single pickle file persistence replaced with directory structure

### Removed

- `services/cache_entry.py`: Cache now uses `FullTickerData` directly

## [0.13.0] - 2026-03-19

### Added

- **Cache Configuration**: Load configuration from JSON file on startup
  - New `services/cache_config.py` with dataclasses: `CacheConfig`, `PrefetchScheduleConfig`, `TtlConfig`
  - Configuration path via `CACHE_CONFIG_PATH` env var (default: `./cache_config.json`)
  - Type validation for all config fields
  - Log config summary on startup (without printing arrays)
- **Config Hot Reload**: SIGHUP signal reloads configuration without restarting Flask
  - Send `kill -HUP <pid>` to reload config
  - Config stored globally and accessible via `get_cache_config()`

## [0.12.0] - 2026-03-19

### Fixed

- **Cache Singleton Bug**: Fixed persistence bug where a new empty cache instance was being pickled instead of the actual cache
  - Made `tsCache` a singleton pattern
  - Now `persist_to_disk()` correctly saves the cache being used by `JobDispatcher`
  - Added `tsCache.get_instance()` class method for singleton access

## [0.11.0] - 2026-03-19

### Added

- **PendingTicker Architecture**: Refactored request batching to per-ticker windowing
  - Each ticker gets its own `PendingTicker` instance with independent timer
  - Timer restarts when new sections are requested (not duplicates)
  - Serial fetch: one ticker at a time to avoid rate limit issues
  - Window duration: 20 seconds per ticker
- **Cache Persistence**: Pickle-based cache persistence across server restarts
  - Cache is persisted to disk on Ctrl+C or normal shutdown
  - Cache is loaded from disk on startup
  - New constants: `MAX_PERSISTED_CACHE_SIZE` (225), `CACHE_PICKLE_FILE`
  - Signal handler for SIGINT ensures clean persistence
- **Cache Warmup**: Expired cache entries are automatically re-fetched on startup
  - Each expired ticker creates a `PendingTicker` to re-fetch its data
  - Warmup runs in parallel with server accepting requests
  - Requests during warmup are deduplicated with pending tickers
  - New `warmup_ticker()` method in `JobDispatcher`
  - New `ExpiredTickerInfo` dataclass and `get_cached_sections()` helper

### Changed

- Renamed from "bucket" to "pending_ticker" terminology throughout
- Removed `MAX_BUCKET_SIZE` constant (no longer needed)
- Increased `PENDING_TICKER_WINDOW_SECONDS` from 3s to 20s
- Removed parallel batch processing in favor of serial per-ticker fetch
- Split `_cache_has_expired()` into separate function (returns bool)
- Improved cache expiration check in `get_ticker()`
- `tsCache.load_from_disk()` now returns list of expired tickers for warmup

### Files Added

- `services/pending_ticker.py`: PendingTicker, TickerWaitingRequest classes

### Files Removed

- `services/request_bucket.py`: Replaced by pending_ticker
- `services/batch_processor.py`: No longer needed

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
