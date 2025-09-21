#!/usr/bin/env python3
"""
BensonBot Strategy Backtest Comparison Dashboard

A Streamlit application that provides a consolidated view of all strategy backtests.
Automatically discovers and parses backtest reports to enable data-driven strategy comparison.

Features:
- Automatic discovery of backtest reports
- Top performers overview with key metrics
- Detailed strategy leaderboard
- Professional formatting and styling
- Real-time data loading with caching

Usage:
    streamlit run apps/dashboard/comparison_dashboard.py

Author: BensonBot Trading System
Date: September 2025
"""

import streamlit as st
import os
import pandas as pd
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="BensonBot Strategy Backtest Comparison",
    layout="wide"
)

# --- App Styling ---
st.markdown("""
<style>
    .stDataFrame {
        font-size: 1.1rem;
    }
    .stMetric {
        border-left: 5px solid #007bff;
        padding-left: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- Core Functions ---

@st.cache_data(ttl=120)
def load_backtest_reports(base_path='strategies'):
    """
    Scans all strategy directories, finds 'backtest_report.md' files,
    and parses them into a structured DataFrame.
    """
    if not os.path.exists(base_path):
        return pd.DataFrame()

    report_data = []
    for strategy_name in os.listdir(base_path):
        strategy_path = os.path.join(base_path, strategy_name)
        report_file = os.path.join(strategy_path, 'backtest_report.md')

        if os.path.isdir(strategy_path) and os.path.exists(report_file):
            try:
                with open(report_file, 'r') as f:
                    content = f.read()

                # Use regex to parse the markdown table for metrics
                metrics = {
                    'Total Return': r"Total Return\s*\|\s*`([\d\.\-]+\%)`",
                    'Final Portfolio Value': r"Final Portfolio Value\s*\|\s*`\$([\d,\.]+)`",
                    'Annualized Sharpe Ratio': r"Annualized Sharpe Ratio\s*\|\s*`([\d\.\-]+)`",
                    'Max Drawdown': r"Max Drawdown\s*\|\s*`([\d\.\-]+\%)`"
                }

                parsed_metrics = {'Strategy': strategy_name.replace('_', ' ').title()}
                for key, pattern in metrics.items():
                    match = re.search(pattern, content)
                    if match:
                        # Clean up the extracted value
                        value = match.group(1).replace(',', '').replace('%', '').replace('$', '')
                        parsed_metrics[key] = float(value)
                    else:
                        parsed_metrics[key] = None

                report_data.append(parsed_metrics)

            except Exception as e:
                st.error(f"Failed to parse report for '{strategy_name}': {e}")

    if not report_data:
        return pd.DataFrame()

    df = pd.DataFrame(report_data)
    # Ensure numeric types for sorting
    for col in ['Total Return', 'Annualized Sharpe Ratio', 'Max Drawdown']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


# --- UI Rendering ---

st.title("📈 BensonBot | Backtest Performance Hub")
st.markdown("A consolidated view of all strategy backtests. Use this hub to compare performance and identify top candidates for live deployment.")
st.markdown("---")

# --- Load Data ---
reports_df = load_backtest_reports()

if reports_df.empty:
    st.warning("No backtest reports found. Please run the backtester on one or more strategies first.")
    st.info("The backtester expects to find `backtest_report.md` files in each `strategies/{strategy_name}/` directory.")
else:
    # --- Key Metrics Overview ---
    st.subheader("Top Performers at a Glance")

    if not reports_df.empty:
        # Find the best strategy for each key metric
        best_return = reports_df.loc[reports_df['Total Return'].idxmax()]
        best_sharpe = reports_df.loc[reports_df['Annualized Sharpe Ratio'].idxmax()]
        best_drawdown = reports_df.loc[reports_df['Max Drawdown'].idxmax()] # Note: Higher value (closer to 0) is better

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Best Return", f"{best_return['Total Return']:.2f}%", delta=best_return['Strategy'])
        with col2:
            st.metric("Best Sharpe Ratio", f"{best_sharpe['Annualized Sharpe Ratio']:.2f}", delta=best_sharpe['Strategy'])
        with col3:
            st.metric("Lowest Drawdown", f"{best_drawdown['Max Drawdown']:.2f}%", delta=best_drawdown['Strategy'], delta_color="inverse")
    else:
        st.info("Run the backtester to generate performance data for comparison.")

    st.markdown("---")

    # --- Detailed Comparison Table ---
    st.subheader("Strategy Leaderboard")

    if not reports_df.empty:
        # Formatting for better readability
        formatted_df = reports_df.copy()
        formatted_df['Total Return'] = formatted_df['Total Return'].map('{:.2f}%'.format)
        formatted_df['Final Portfolio Value'] = formatted_df['Final Portfolio Value'].map('${:,.2f}'.format)
        formatted_df['Annualized Sharpe Ratio'] = formatted_df['Annualized Sharpe Ratio'].map('{:.2f}'.format)
        formatted_df['Max Drawdown'] = formatted_df['Max Drawdown'].map('{:.2f}%'.format)

        st.dataframe(formatted_df.set_index('Strategy'), use_container_width=True)

        st.info("Click on column headers to sort by a specific metric.")
    else:
        st.info("No strategy data available. Run the backtester first to generate reports.")