# Changelog

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