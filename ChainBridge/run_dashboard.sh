#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
pip install -r requirements-dashboard.txt
streamlit run dashboard.py
