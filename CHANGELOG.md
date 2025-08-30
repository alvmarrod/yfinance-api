# Changelog

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