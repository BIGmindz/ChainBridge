import os
import sys
from importlib import util

# Ensure we load the local main.py directly
spec = util.spec_from_file_location("bmain", "/Users/johnbozza/Multiple-signal-decision-bot/main.py")
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Set required env vars
os.environ["CONFIRM_LIVE"] = "YES"
# Ensure live mode
sys.argv = ["main.py", "--mode", "live", "--min-trade-usd", "5"]

# Call main()
if hasattr(mod, "main"):
    sys.exit(mod.main())
else:
    print("no main() in module")
    sys.exit(2)
