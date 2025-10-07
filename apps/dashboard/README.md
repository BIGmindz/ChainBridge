# BensonBot Strategy Backtest Comparison Dashboard

A Streamlit application that provides a consolidated view of all strategy backtests, enabling data-driven strategy comparison and selection.

## Features

- **Automatic Report Discovery**: Automatically finds and parses all backtest reports

- **Top Performers Overview**: Highlights best strategies for key metrics

- **Interactive Leaderboard**: Sortable table with all strategy performance data

- **Professional UI**: Clean, modern interface with proper formatting

- **Real-time Updates**: Cached data loading with automatic refresh

## Usage

### Basic Usage

```bash

## Launch the dashboard

streamlit run apps/dashboard/comparison_dashboard.py

## Or use the convenience script

./apps/dashboard/run_dashboard.sh

```text

### Prerequisites

1. **Backtest Reports**: Run the backtester first to generate reports

   ```bash

   python apps/backtester/backtester.py

   ```

1. **Report Format**: The dashboard expects `backtest_report.md` files in each strategy directory

## Dashboard Features

### Top Performers Overview

- **Best Return**: Strategy with highest total return percentage

- **Best Sharpe Ratio**: Strategy with highest risk-adjusted returns

- **Lowest Drawdown**: Strategy with smallest maximum drawdown

### Strategy Leaderboard

- **Sortable Columns**: Click any column header to sort

- **Formatted Metrics**: Properly formatted percentages, currency, and ratios

- **Complete Data**: All key performance metrics in one view

## Data Sources

The dashboard reads from:

```text

strategies/
├── strategy_name_1/
│   └── backtest_report.md
├── strategy_name_2/
│   └── backtest_report.md
└── ...

```text

## Report Format

Expected markdown format in backtest reports:

```markdown

## Backtest Report: STRATEGY_NAME

| Metric | Value |
|--------|-------|
| Total Return | `15.23%` |
| Final Portfolio Value | `$11,523.45` |
| Annualized Sharpe Ratio | `1.45` |
| Max Drawdown | `-8.32%` |

```text

## Workflow Integration

1. **Run Backtests**: Execute the backtester on all strategies

1. **Launch Dashboard**: Start the comparison dashboard

1. **Analyze Results**: Compare strategies across multiple dimensions

1. **Select Candidates**: Identify top performers for live deployment

1. **Allocate Capital**: Make informed capital allocation decisions

## Dependencies

- streamlit

- pandas

- plotly (for future chart enhancements)

## Configuration

The dashboard automatically discovers strategies and reports. No configuration required.

## Error Handling

- Gracefully handles missing reports

- Shows clear warnings when no data is available

- Provides helpful guidance for next steps

## Future Enhancements

- Interactive equity curve comparisons

- Risk-return scatter plots

- Strategy correlation analysis

- Performance attribution breakdowns
