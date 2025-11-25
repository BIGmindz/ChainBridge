"""
Lightweight proxy package that points to the real ChainPay service modules.
"""

from pathlib import Path

# Compute the actual ChainPay "app" directory path (hyphenated folder outside packages)
_CHAINPAY_APP_PATH = Path(__file__).resolve().parents[2] / "chainpay-service" / "app"

# Ensure Python loads modules from the real ChainPay app directory
__path__ = [str(_CHAINPAY_APP_PATH)]
