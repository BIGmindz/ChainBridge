#!/usr/bin/env python3
"""
Lean-friendly smoke test for AdaptiveWeightIntegrator.

Runs the integrator with tiny sample inputs and prints the result as JSON.
Designed to work in the lean runtime (no TensorFlow), returning default weights.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime


def main() -> int:
    # Protective env flags to avoid native extension noise in lean envs
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    os.environ.setdefault("PYTHONMALLOC", "malloc")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_MAX_THREADS", "1")
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

    # Ensure project root on path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    # Import integrator lazily so env vars are set first
    try:
        from modules.adaptive_weight_module.integrate_adaptive_weights import (  # type: ignore
            AdaptiveWeightIntegrator,
        )
    except Exception as e:  # pragma: no cover - smoke output
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"Failed to import AdaptiveWeightIntegrator: {e}",
                },
                indent=2,
            )
        )
        return 1

    config = {"data_dir": "data", "logs_dir": "logs", "model_dir": "models"}
    integrator = AdaptiveWeightIntegrator(config)

    # Minimal sample inputs
    signal_data = {
        "LAYER_1_TECHNICAL": {"RSI": 55.0, "MACD": 0.1},
        "LAYER_2_LOGISTICS": {"EXCHANGE_HEALTH": 0.8},
        "LAYER_3_GLOBAL_MACRO": {"RISK_ON": 0.6},
        "LAYER_4_ADOPTION": {"USER_GROWTH": 0.7},
    }
    market_data = {
        "price_history": [100.0, 101.0, 102.5, 101.8, 103.2],
        "volume_history": [1000, 1100, 1050, 1200, 1300],
        "timestamp": datetime.now().isoformat(),
    }

    result = integrator.optimize_signal_weights(signal_data, market_data)
    print(json.dumps({"ok": True, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
