import sys
from pathlib import Path

# This file lives at:
#   ChainBridge/chainiq-service/app/risk/tests/conftest.py
# We want to add:
#   ChainBridge/chainiq-service
# to sys.path so that "import app" works.

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../chainiq-service
project_root_str = str(PROJECT_ROOT)

if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)
