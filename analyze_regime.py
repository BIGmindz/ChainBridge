#!/usr/bin/env python3
"""
Run the market regime analysis tool to evaluate detection performance
and get improvement recommendations.
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # type: ignore

# Import and run the analysis tool
from tools.analyze_regime_detection import main

if __name__ == "__main__":
    print(
        """
    ╔════════════════════════════════════════════════════════╗
    ║   MARKET REGIME ANALYSIS                              ║
    ║   Evaluating Regime Detection Performance             ║
    ╚════════════════════════════════════════════════════════╝
    """
    )

    main()
