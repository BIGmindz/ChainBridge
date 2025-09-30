# Multiple-Signal Trading System with New Listings Radar

## System Overview

This document provides a comprehensive guide for setting up and running the Multiple-Signal Trading Bot with the New Listings Radar module.

## Quick Start

### 1. Start the New Listings Radar

```bash
python run_new_listings_radar.py --scan &
```

This starts the New Listings Radar in the background, scanning for new coin listings across major exchanges.

### 2. Start the Main Trading Bot

```bash
python multi_signal_bot.py
```

This starts the main trading bot with all signal modules, including the New Listings Radar.

### 3. Set Up Exchange Alerts

```bash
python setup_exchange_alerts.py --configure
```

This configures alerts for each exchange to notify you of new listings.

### 4. Allocate Capital for First Listing

```bash
python allocate_capital.py --allocate
```

This allocates $1000 for the first listing opportunity.

### 5. Monitor the System

```bash
python monitor_live_system.py --dashboard
```

This starts the system monitor with a live dashboard.

## System Components

### 1. Multiple-Signal Bot (`multi_signal_bot.py`)

The main trading bot that integrates multiple signal modules:

- RSI Module
- MACD Module
- Bollinger Bands Module
- Volume Profile Module
- Sentiment Analysis Module
- Logistics Signal Module
- Global Macro Module
- Region-Specific Crypto Module
- New Listings Radar Module

### 2. New Listings Radar (`modules/new_listings_radar_module.py`)

Monitors major exchanges for new coin listings and generates trading signals:

- Supported Exchanges: Kraken, Coinbase, Binance, OKX, KuCoin
- Features: Announcement parsing, risk filtering, signal generation, backtest capability
- Average Returns: 20-40% per listing

### 3. Exchange Alerts (`setup_exchange_alerts.py`)

Sets up alerts for monitoring exchanges:

- Configurable alert thresholds for each exchange
- Alert notifications for new listings
- Risk-based filtering

### 4. Capital Allocation (`allocate_capital.py`)

Manages capital allocation for trading:

- Initial $1000 allocation for first listing
- Risk-based position sizing
- Confidence-based allocation

### 5. System Monitor (`monitor_live_system.py`)

Provides real-time monitoring of the trading system:

- Component status monitoring
- Trading metrics dashboard
- Automatic restart of failed components

## Configuration

### 1. Exchange Alert Configuration

The exchange alert system can be configured with custom thresholds:

```bash
python setup_exchange_alerts.py --configure
```

### 2. Capital Allocation Settings

The capital allocation system can be configured with custom settings:

```bash
python allocate_capital.py --settings
```

## Monitoring and Reporting

### 1. Exchange Alert Status

```bash
python setup_exchange_alerts.py --status
```

### 2. Capital Allocation Status

```bash
python allocate_capital.py --status
```

### 3. Live System Dashboard

```bash
python monitor_live_system.py --dashboard
```

## Implementation Details

### 1. New Listings Radar

The New Listings Radar module monitors exchange APIs and announcement pages for new coin listings. When a new listing is detected, it applies risk filters and generates a trading signal with the following information:

- Exchange
- Coin
- Confidence
- Expected Return
- Risk Level
- Entry Strategy
- Exit Strategy

### 2. Exchange Alerts

The exchange alert system monitors the New Listings Radar for new listings that meet the configured criteria. Alerts include:

- Exchange
- Coin
- Confidence
- Expected Return
- Risk Level
- Timestamp

### 3. Capital Allocation

The capital allocation system calculates position sizes based on:

- Listing confidence
- Risk level
- Expected return
- Available capital

For the first listing, it allocates $1000 as specified.

### 4. System Monitor

The system monitor checks the status of all components and provides a real-time dashboard with:

- Component status
- Trading metrics
- Active listings
- Open positions

## Additional Resources

- [README_NEW_LISTINGS.md](README_NEW_LISTINGS.md): Detailed documentation for the New Listings Radar module
- [QUICKSTART_NEW_LISTINGS.md](QUICKSTART_NEW_LISTINGS.md): Quick start guide for the New Listings Radar module
