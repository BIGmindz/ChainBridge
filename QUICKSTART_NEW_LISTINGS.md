# New Listings Radar Quick Start Guide

This guide provides a quick overview of how to use the New Listings Radar module with the Multiple-signal-decision-bot.

## Setup

1. Install dependencies:


   ```bash
   python setup_new_listings.py
   ```

2. Verify installation:


   ```bash
   pip list | grep beautifulsoup4
   ```

## Running the Module

### Standalone Mode

Run the New Listings Radar independently:

```bash
# Scan for new listings
python run_new_listings_radar.py --scan

# Run with backtest
python run_new_listings_radar.py --backtest --days 30
```

### Dashboard Mode

View the visual dashboard of listing opportunities:

```bash
python new_listings_dashboard.py
```

### Integrated Mode

The module is already integrated with the main bot:

1. Make sure `modules/new_listings_radar_module.py` is properly installed
2. Run the main bot which will include this module:


   ```bash
   python multi_signal_bot.py
   ```

## Common Commands

```bash
# Check setup status
python setup_new_listings.py

# Run scan and save results
python run_new_listings_radar.py --scan --save

# Run backtest with custom days
python run_new_listings_radar.py --backtest --days 60

# Run dashboard
python new_listings_dashboard.py
```

## Checking Logs

The module logs information to the main bot's logging system:

```bash
# View the last 50 lines of logs with listings radar info
tail -n 50 logs/dashboard.log | grep "NewListingsRadar"
```

## Troubleshooting

If you encounter issues:

1. Check dependencies:


   ```bash
   python setup_new_listings.py
   ```

2. Verify network connectivity to exchanges

3. Check log files for error messages

4. Ensure proper configuration in `config/trading_config.json`
