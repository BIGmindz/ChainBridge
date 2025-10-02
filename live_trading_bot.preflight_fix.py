# Safe replacement for the preflight_check() snippet in live_trading_bot.py.
# Replace the function preflight_check() that prints key fragments with this version.

import sys
import os

def preflight_check():
    api_key = os.environ.get("API_KEY")
    api_secret = os.environ.get("API_SECRET")
    if not api_key or not api_secret:
        print("❌ Missing API_KEY or API_SECRET in environment.")
        sys.exit(1)
    else:
        # Do NOT print key fragments. Just indicate presence.
        print("✔ API keys loaded (value redacted).")
