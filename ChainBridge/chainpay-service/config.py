"""
ChainPay XRPL configuration
All secrets must use environment variables. XRPL disabled by default.
"""
import os

def env(key: str, default=None):
    return os.environ.get(key, default)

XRPL_MODE = env("XRPL_MODE", "disabled")  # "disabled" | "testnet" | "devnet"
XRPL_SEED = env("XRPL_SEED")
XRPL_ADDRESS = env("XRPL_ADDRESS")
