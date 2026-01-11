"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 SECURITY MODULE - THE DIGITAL IMMUNE SYSTEM                  ║
║                       PAC-SEC-P600-IMMUNE-SYSTEM                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Continuous Adversarial Testing for Sovereign Node Resilience                ║
║                                                                              ║
║  "What does not kill the Node makes it Sovereign."                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

This module provides the security infrastructure for ChainBridge:
  - War Games Engine for adversarial simulation
  - Attack vector definitions and execution
  - Anti-fragility testing
  - Containment verification

Components:
  - WarGamesEngine: Continuous attack simulation
  - AttackVector: Types of simulated attacks
  - AttackResult: Attack outcome tracking
  - SecurityReport: Aggregate security metrics

Usage:
    from modules.security import WarGamesEngine, AttackVector
    
    # Initialize the war games engine
    engine = WarGamesEngine()
    
    # Run specific attack
    result = engine.execute_attack(AttackVector.XML_BOMB)
    
    # Run full simulation
    report = engine.run_simulation(iterations=100)
"""

__version__ = "3.0.0"

from .wargames import (
    # Engine
    WarGamesEngine,
    
    # Models
    AttackResult,
    SecurityReport,
    
    # Enums
    AttackVector,
    AttackOutcome,
    Severity,
    
    # Exceptions
    SecurityError,
    CriticalBreachError,
    ContainmentFailureError,
)

__all__ = [
    # Engine
    "WarGamesEngine",
    
    # Models
    "AttackResult",
    "SecurityReport",
    
    # Enums
    "AttackVector",
    "AttackOutcome",
    "Severity",
    
    # Exceptions
    "SecurityError",
    "CriticalBreachError",
    "ContainmentFailureError",
]
