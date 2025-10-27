# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive fitness data pipeline that automatically syncs multi-source health and performance data for analysis. The system collects data from Garmin Connect, Eufy Smart Scale P3, GitHub activity, and optional Telegram bot inputs, storing everything in structured CSV files for analysis.

## Core Architecture

### Data Collection Flow

1. **Entry Point**: `scripts/data_collector.py` - Main orchestration script that coordinates all data collection
2. **Garmin Client**: `scripts/garmin_client.py` - Handles authentication and API calls to Garmin Connect
3. **Data Processor**: `scripts/data_processor.py` - Transforms raw API responses into structured data
4. **CSV Manager**: `scripts/csv_manager.py` - Handles all file I/O, deduplication, and data persistence
5. **Specialized Collectors**: Individual scripts for Eufy (`eufy_collector.py`), Telegram (`telegram_collector.py`), and GitHub (`github_collector.py`)

### Activity-Specific Processing

The system uses type-specific processing for different activities. Activity types are defined in `config/data_schema.py` with the `ACTIVITY_TYPE_MAPPING` dictionary. Each activity type has:
- A dedicated CSV file (e.g., `swimming_activities.csv`, `running_activities.csv`)
- Type-specific column schema
- Specialized extraction methods in `GarminDataClient._extract_*_metrics()`

Supported activity types:
- **Surfing**: Wave tracking, paddle time, surf ratios
- **Swimming**: Strokes, SWOLF, pace, pool vs open water
- **Running**: Cadence, stride length, running dynamics
- **Strength**: Sets, reps, volume, muscle groups
- **Breathwork**: WHM rounds, breath holds, respiration rates
- **Recovery**: Sauna/cold exposure sessions

### Data Schema System

All CSV column definitions are centralized in `config/data_schema.py`. This includes:
- `CORE_ACTIVITY_COLUMNS`: Base fields present in all activities
- Activity-specific column sets (e.g., `SWIMMING_ACTIVITY_COLUMNS`)
- `ACTIVITY_TYPE_MAPPING`: Routes activity types to files and schemas
- Health, physiological, and body composition schemas

### Historical vs Daily Sync

The collector implements smart sync logic in `data_collector.py:is_first_run()`:
- **First run**: Collects 30 days of historical data
- **Subsequent runs**: Collects 14 days (with deduplication)
- Detection: Checks if `data/health/daily_metrics.csv` has data from last 7 days

## Development Commands

### Running Data Collection Locally

```bash
# Set required environment variables
set GARMIN_EMAIL=your-email@example.com
set GARMIN_PASSWORD=your-password
set EUFY_EMAIL=your-eufy-email@example.com
set EUFY_PASSWORD=your-eufy-password

# Optional integrations
set TELEGRAM_BOT_TOKEN=your-bot-token
set _GITHUB_USERNAME=your-username
set _GITHUB_TOKEN=your-token

# Run collection
python scripts/data_collector.py
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Manual Testing Individual Collectors

```bash
# Test Garmin connection
python scripts/garmin_client.py

# Test Eufy collection
python scripts/eufy_collector.py

# Test data processing
python scripts/data_processor.py
```

## GitHub Actions Automation

The workflow runs daily at 1 PM PT (21:00 UTC) via `.github/workflows/sync_data.yml`:
- Automatically commits collected data to the repository
- Requires secrets: `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `EUFY_EMAIL`, `EUFY_PASSWORD`
- Optional: `TELEGRAM_BOT_TOKEN`, `_GITHUB_USERNAME`, `_GITHUB_TOKEN`

Manual trigger: Use "Run workflow" button in GitHub Actions tab.

## Data Storage Structure

```
data/
├── activities/           # Sport-specific CSVs (swimming, running, etc.)
├── health/              # Daily health metrics (sleep, HRV, body battery)
├── physiological/       # VO2 max, training status, fitness age
├── body_composition/    # Eufy scale measurements
├── training_zones/      # Weekly heart rate zone distribution
├── recovery_trends/     # Recovery analysis over time
├── subjective/          # Telegram bot inputs (optional)
├── lifestyle/           # GitHub coding activity (optional)
└── metadata/            # Sync logs
```

## Key Implementation Details

### Duplicate Detection and Updates

The CSV manager (`csv_manager.py:append_to_csv()`) uses intelligent deduplication:
- Activities: Uses `['date', 'activity_id']` as composite key
- Daily metrics: Uses `['date']` as key
- Weekly data: Uses `['week_start_date']` as key
- Updates existing records with new data, adds new records

### Rate Limiting

The `rate_limit_manager.py` handles Garmin API rate limits to prevent authentication blocks during historical data collection.

### Connect IQ Data Extraction

For specialized metrics (WHM breathwork, surfing apps), the system extracts Connect IQ developer fields:
- `GarminDataClient._extract_whm_connectiq_data()`: Parses WHM app data
- `GarminDataClient._extract_surfing_connectiq_data()`: Parses surf tracking data
- Field numbers map to specific metrics (e.g., field 0 = rounds, field 1 = breaths)

### Error Handling

All collectors log errors to `data/metadata/sync_log.csv` with:
- Timestamp, data type, records added, status, error message
- Allows partial failures (e.g., Eufy fails but Garmin succeeds)

## Working with Activity Types

When adding a new activity type:

1. Add column schema to `config/data_schema.py`
2. Add entry to `ACTIVITY_TYPE_MAPPING`
3. Create extraction method in `garmin_client.py` (e.g., `_extract_cycling_metrics()`)
4. Add condition in `get_activity_details_by_type()` to route to new extractor
5. The CSV manager will automatically create the file and handle deduplication

## Testing Changes

There are no formal tests in this repository. Test manually by:
1. Running `data_collector.py` with test credentials
2. Checking CSV output in `data/` directories
3. Verifying sync logs in `data/metadata/sync_log.csv`
4. Checking GitHub Actions logs after pushing changes

## Common Debugging Areas

- **Authentication failures**: Check credentials, 2FA settings on Garmin/Eufy accounts
- **Missing metrics**: Some devices don't provide all fields; processing handles null values gracefully
- **Duplicate data**: CSV manager should handle this; check key column logic in `append_to_csv()`
- **Rate limiting**: Garmin may block aggressive requests; `rate_limit_manager.py` adds delays
