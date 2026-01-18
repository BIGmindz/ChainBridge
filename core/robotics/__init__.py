"""
ChainBridge Robotics Integration Module
========================================

Provides ROS 2 bridge for hardware-in-the-loop (HITL) integration with
Carnegie Robotics telemetry systems. Translates physical sensor data into
Proposed Strategic Vectors (PSV) for Rust Kernel judgment.

Architecture:
- ros2_bridge.py: ROS 2 node subscribing to /odom and /scan topics
- psv_translator.py: Telemetry-to-PSV conversion with NFI signing
- Rust Kernel integration for fail-closed movement approval

Security:
- HMAC-SHA512 NFI signatures on all packets
- Zero authority to execute movements (translation only)
- NASA/Defense-grade fail-closed architecture

Author: BENSON [GID-00]
PAC: PAC-ROS2-DEFENSE-BRIDGE-25
Version: 1.0.0 (Defense-Grade)
"""

__version__ = "1.0.0"
__security_clearance__ = "DEFENSE_GRADE"
__fail_closed__ = True

from .psv_translator import PSVTranslator, TelemetryType
from .ros2_bridge import BensonROS2Bridge

__all__ = [
    "PSVTranslator",
    "TelemetryType",
    "BensonROS2Bridge"
]
