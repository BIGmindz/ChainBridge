# Multiple-Signal Trading System Quick Start

This guide provides quick steps to set up and run the Multiple-Signal Trading System with New Listings Radar.

## Prerequisites

- Python 3.8+
- Required dependencies installed (`pip install -r requirements.txt`)
- New Listings Radar dependencies installed (`pip install -r requirements-listings.txt`)

## Step 1: Start Full System Live Monitoring

Start the system monitor in a separate terminal window:

```bash
python monitor_live_system.py --dashboard
```

This will display a real-time dashboard of your trading system.

## Step 2: Set Alerts for All Exchanges

Configure and start the exchange alert system:

```bash
# Configure alert settings
python setup_exchange_alerts.py --configure

# Start the alert system in background
python setup_exchange_alerts.py &
```

## Step 3: Allocate $1000 for First Listing

Set up capital allocation for the first listing:

```bash
python allocate_capital.py --allocate
```

## Step 4: Start Trading System

Run the New Listings Radar and Multi-Signal Bot:

```bash
# Start New Listings Radar in background
python run_new_listings_radar.py --scan &

# Start Multi-Signal Bot in foreground
python multi_signal_bot.py
```

## Monitoring Commands

Check the status of various components:

```bash
# Check exchange alerts
python setup_exchange_alerts.py --status

# Check capital allocation
python allocate_capital.py --status

# View New Listings Radar log
tail -f new_listings_radar.log

# View Multi-Signal Bot log
tail -f multi_signal_bot.log
```

## Running Backtest

Test the New Listings Radar strategy on historical data:

```bash
python run_new_listings_radar.py --backtest --days 30
```

## Stopping the System

To stop all components:

```bash
# Find and kill Python processes
pkill -f "python.*run_new_listings_radar.py"
pkill -f "python.*multi_signal_bot.py"
pkill -f "python.*monitor_live_system.py"
pkill -f "python.*setup_exchange_alerts.py"
```

## Documentation Links

- [TRADING_SYSTEM_DOCUMENTATION.md](TRADING_SYSTEM_DOCUMENTATION.md) - Full system documentation
- [README_NEW_LISTINGS.md](README_NEW_LISTINGS.md) - New Listings Radar documentation