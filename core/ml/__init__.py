"""
BLCR (Binary Logic Compiled Reasoning) Module
PAC-MLAU-HARDEN-LOGIC-16 + PAC-AUTO-SYNTH-18

Machine-native logic gates for ML-AU fast-path reasoning.
Auto-Synth engine for 10,000+ law-gate generation.
"""

from .blcr_core import (
    BLCRCore,
    LogicGate,
    GateType,
    GuardStatus,
    SentinelGuardBinding,
    BLCRCircuit,
    run_blcr_benchmark,
    export_blcr_circuit
)

from .auto_synth import (
    AutoSynthEngine,
    SynthesizedGate,
    LegalDomain,
    JurisdictionCode,
    run_auto_synth,
    run_stress_test,
    export_gate_library
)

__all__ = [
    # BLCR Core
    "BLCRCore",
    "LogicGate",
    "GateType",
    "GuardStatus",
    "SentinelGuardBinding",
    "BLCRCircuit",
    "run_blcr_benchmark",
    "export_blcr_circuit",
    # Auto-Synth
    "AutoSynthEngine",
    "SynthesizedGate",
    "LegalDomain",
    "JurisdictionCode",
    "run_auto_synth",
    "run_stress_test",
    "export_gate_library"
]
