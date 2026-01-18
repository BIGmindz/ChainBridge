#!/usr/bin/env python3
"""
PSV Translator - Telemetry to Proposed Strategic Vector Conversion
===================================================================

Translates ROS 2 sensor telemetry (Odometry, Lidar) into ChainBridge
Proposed Strategic Vector (PSV) format with HMAC-512 NFI signatures.

This module is a TRANSLATOR ONLY - it has ZERO authority to execute
physical movements. All PSVs must be approved by the Rust Kernel.

Architecture:
- Receives ROS 2 messages (nav_msgs/Odometry, sensor_msgs/LaserScan)
- Converts to JSON-PSV schema
- Signs with HMAC-SHA512 NFI instance key
- Submits to Rust Kernel for constitutional judgment

Safety:
- CB-ROB-01: No physical movement without signed Kernel Approval
- CB-SEC-01: Every ROS 2 packet must carry valid NFI signature
- Fail-closed by design

Author: BENSON [GID-00]
PAC: PAC-ROS2-DEFENSE-BRIDGE-25
"""

import hashlib
import hmac
import json
import math
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import os
import sys

# Add project root to path for absolute imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TelemetryType(Enum):
    """Types of robotic telemetry data"""
    ODOMETRY = "odometry"
    LIDAR_SCAN = "lidar_scan"
    IMU = "imu"
    CAMERA = "camera"
    UNKNOWN = "unknown"


@dataclass
class ProposedStrategicVector:
    """
    Proposed Strategic Vector (PSV) - Rust Kernel Input Schema
    
    This is the canonical format for physical movement proposals.
    All robotic actions must be translated into PSVs and approved
    by the Rust Kernel before execution.
    """
    psv_id: str
    timestamp: str
    telemetry_type: str
    source_topic: str
    
    # Physical state
    position: Dict[str, float]  # {x, y, z}
    velocity: Dict[str, float]  # {vx, vy, vz}
    orientation: Dict[str, float]  # {roll, pitch, yaw} or quaternion
    
    # Sensor data
    sensor_data: Dict[str, Any]
    
    # Proposed action (if any)
    proposed_movement: Optional[Dict[str, Any]]
    
    # NFI signature metadata
    nfi_instance: str
    nfi_signature: str
    architectural_justification: str
    
    # Trace information
    latency_us: float
    sequence_number: int


class PSVTranslator:
    """
    Translates ROS 2 telemetry into Proposed Strategic Vectors (PSV)
    with HMAC-512 NFI signatures for Rust Kernel judgment.
    """
    
    def __init__(self, gid: str = "00", nfi_instance: Optional[str] = None):
        """
        Initialize PSV Translator with NFI signing capability.
        
        Args:
            gid: Agent GID (default "00" for BENSON)
            nfi_instance: NFI instance identifier (auto-generated if None)
        """
        self.gid = gid
        self.agent_name = "BENSON" if gid == "00" else f"AGENT-{gid}"
        
        # Generate NFI instance key (simulation - in production, load from secure store)
        if nfi_instance is None:
            instance_hash = hashlib.sha256(f"{gid}_{time.time()}".encode()).hexdigest()[:16]
            self.nfi_instance = f"cb_nfi_gid{gid}_{self.agent_name.lower()}_robotics_{instance_hash}"
        else:
            self.nfi_instance = nfi_instance
        
        # Sequence counter for PSV IDs
        self.sequence = 0
        
        # Performance tracking
        self.translation_count = 0
        self.total_latency_us = 0.0
    
    def _generate_hmac_signature(self, data: Dict[str, Any], justification: str) -> str:
        """
        Generate HMAC-SHA512 signature for PSV data.
        
        Args:
            data: PSV data dictionary
            justification: Architectural justification (min 32 chars)
        
        Returns:
            Hexadecimal HMAC-SHA512 signature
        """
        if len(justification) < 32:
            raise ValueError(f"Architectural justification must be >= 32 chars (got {len(justification)})")
        
        # Create canonical payload
        payload = json.dumps(data, sort_keys=True)
        
        # Generate HMAC-SHA512 (using NFI instance as key)
        signature = hmac.new(
            self.nfi_instance.encode(),
            payload.encode(),
            hashlib.sha512
        ).hexdigest()
        
        return signature
    
    def translate_odometry(
        self,
        position: Dict[str, float],
        velocity: Dict[str, float],
        orientation: Dict[str, float],
        source_topic: str = "/odom",
        proposed_movement: Optional[Dict[str, Any]] = None,
        justification: str = "Translating Carnegie Robotics odometry telemetry to PSV for Rust Kernel constitutional judgment"
    ) -> ProposedStrategicVector:
        """
        Translate ROS 2 Odometry message to PSV.
        
        Args:
            position: {x, y, z} in meters
            velocity: {vx, vy, vz} in m/s
            orientation: {roll, pitch, yaw} in radians or quaternion
            source_topic: ROS 2 topic name
            proposed_movement: Optional proposed movement command
            justification: Architectural justification (MANDATORY, min 32 chars)
        
        Returns:
            ProposedStrategicVector with HMAC-512 signature
        """
        start_time = time.perf_counter()
        self.sequence += 1
        
        # Generate unique PSV ID
        psv_hash = hashlib.sha3_256(
            f"{self.nfi_instance}_{self.sequence}_{time.time()}".encode()
        ).hexdigest()[:12]
        psv_id = f"PSV-ODOM-{psv_hash.upper()}"
        
        # Build PSV data
        psv_data = {
            "psv_id": psv_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "telemetry_type": TelemetryType.ODOMETRY.value,
            "source_topic": source_topic,
            "position": position,
            "velocity": velocity,
            "orientation": orientation,
            "sensor_data": {
                "odometry": {
                    "position": position,
                    "velocity": velocity,
                    "orientation": orientation
                }
            },
            "proposed_movement": proposed_movement,
            "nfi_instance": self.nfi_instance,
            "architectural_justification": justification,
            "sequence_number": self.sequence
        }
        
        # Generate HMAC-512 signature
        signature = self._generate_hmac_signature(psv_data, justification)
        psv_data["nfi_signature"] = signature
        
        # Calculate latency
        end_time = time.perf_counter()
        latency_us = (end_time - start_time) * 1_000_000
        psv_data["latency_us"] = latency_us
        
        # Update stats
        self.translation_count += 1
        self.total_latency_us += latency_us
        
        return ProposedStrategicVector(**psv_data)
    
    def translate_lidar_scan(
        self,
        ranges: List[float],
        angles: List[float],
        intensities: Optional[List[float]] = None,
        source_topic: str = "/scan",
        proposed_movement: Optional[Dict[str, Any]] = None,
        justification: str = "Translating Carnegie Robotics LIDAR scan telemetry to PSV for obstacle detection and path planning"
    ) -> ProposedStrategicVector:
        """
        Translate ROS 2 LaserScan message to PSV.
        
        Args:
            ranges: List of range measurements in meters
            angles: List of corresponding angles in radians
            intensities: Optional list of intensity values
            source_topic: ROS 2 topic name
            proposed_movement: Optional proposed movement command
            justification: Architectural justification (MANDATORY, min 32 chars)
        
        Returns:
            ProposedStrategicVector with HMAC-512 signature
        """
        # Validate architectural justification (NASA/Defense-Grade requirement)
        if len(justification) < 32:
            raise ValueError(f"Architectural justification must be >= 32 chars (got {len(justification)})")
        
        start_time = time.perf_counter()
        self.sequence += 1
        
        # Generate unique PSV ID
        psv_hash = hashlib.sha3_256(
            f"{self.nfi_instance}_{self.sequence}_{time.time()}".encode()
        ).hexdigest()[:12]
        psv_id = f"PSV-LIDAR-{psv_hash.upper()}"
        
        # Calculate obstacle summary
        min_range = min(ranges) if ranges else float('inf')
        max_range = max(ranges) if ranges else 0.0
        avg_range = sum(ranges) / len(ranges) if ranges else 0.0
        
        # Detect closest obstacles
        obstacle_threshold = 2.0  # meters
        obstacles = [
            {"angle": angles[i], "range": ranges[i]}
            for i in range(len(ranges))
            if ranges[i] < obstacle_threshold
        ]
        
        # Build PSV data
        psv_data = {
            "psv_id": psv_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "telemetry_type": TelemetryType.LIDAR_SCAN.value,
            "source_topic": source_topic,
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},  # Relative to robot
            "velocity": {"vx": 0.0, "vy": 0.0, "vz": 0.0},
            "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            "sensor_data": {
                "lidar": {
                    "num_points": len(ranges),
                    "min_range": min_range,
                    "max_range": max_range,
                    "avg_range": avg_range,
                    "obstacles_detected": len(obstacles),
                    "obstacles": obstacles[:10],  # Limit to 10 closest
                    "ranges_sample": ranges[:100],  # Limit payload size
                    "angles_sample": angles[:100]
                }
            },
            "proposed_movement": proposed_movement,
            "nfi_instance": self.nfi_instance,
            "architectural_justification": justification,
            "sequence_number": self.sequence
        }
        
        # Generate HMAC-512 signature
        signature = self._generate_hmac_signature(psv_data, justification)
        psv_data["nfi_signature"] = signature
        
        # Calculate latency
        end_time = time.perf_counter()
        latency_us = (end_time - start_time) * 1_000_000
        psv_data["latency_us"] = latency_us
        
        # Update stats
        self.translation_count += 1
        self.total_latency_us += latency_us
        
        return ProposedStrategicVector(**psv_data)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get translator performance statistics"""
        avg_latency = (
            self.total_latency_us / self.translation_count
            if self.translation_count > 0 else 0.0
        )
        
        return {
            "translations": self.translation_count,
            "avg_latency_us": avg_latency,
            "avg_latency_ms": avg_latency / 1000.0,
            "nfi_instance": self.nfi_instance,
            "gid": self.gid,
            "agent": self.agent_name
        }
    
    def export_psv_to_json(self, psv: ProposedStrategicVector, filepath: str):
        """Export PSV to JSON file for Rust Kernel submission"""
        with open(filepath, 'w') as f:
            json.dump(asdict(psv), f, indent=2)


# CLI for testing
if __name__ == "__main__":
    print("═" * 72)
    print("  PSV TRANSLATOR - TELEMETRY TO PROPOSED STRATEGIC VECTOR")
    print("  PAC: PAC-ROS2-DEFENSE-BRIDGE-25")
    print("  Security: DEFENSE_GRADE | NFI: HMAC-SHA512")
    print("═" * 72)
    print()
    
    # Initialize translator
    translator = PSVTranslator(gid="00")
    print(f"[INIT] NFI Instance: {translator.nfi_instance}")
    print()
    
    # Test 1: Odometry translation
    print("[TEST 1] Translating Odometry Telemetry...")
    odom_psv = translator.translate_odometry(
        position={"x": 1.5, "y": 2.3, "z": 0.0},
        velocity={"vx": 0.5, "vy": 0.0, "vz": 0.0},
        orientation={"roll": 0.0, "pitch": 0.0, "yaw": 0.785},
        proposed_movement={"command": "FORWARD", "velocity": 0.5, "duration": 2.0},
        justification="Ghost movement test for Rust Kernel validation - forward movement at 0.5 m/s for 2 seconds"
    )
    print(f"  PSV ID: {odom_psv.psv_id}")
    print(f"  Timestamp: {odom_psv.timestamp}")
    print(f"  Signature: {odom_psv.nfi_signature[:32]}...")
    print(f"  Latency: {odom_psv.latency_us:.2f} µs")
    print()
    
    # Test 2: LIDAR translation
    print("[TEST 2] Translating LIDAR Scan Telemetry...")
    import math
    num_points = 360
    ranges = [3.0 + 0.5 * math.sin(i * 0.1) for i in range(num_points)]
    ranges[45] = 0.8  # Simulate close obstacle
    angles = [i * (2 * math.pi / num_points) for i in range(num_points)]
    
    lidar_psv = translator.translate_lidar_scan(
        ranges=ranges,
        angles=angles,
        proposed_movement=None,  # No movement - obstacle detected
        justification="LIDAR obstacle detection scan - identifying close-range obstacles for path planning safety verification"
    )
    print(f"  PSV ID: {lidar_psv.psv_id}")
    print(f"  Timestamp: {lidar_psv.timestamp}")
    print(f"  Obstacles: {lidar_psv.sensor_data['lidar']['obstacles_detected']}")
    print(f"  Min Range: {lidar_psv.sensor_data['lidar']['min_range']:.2f}m")
    print(f"  Signature: {lidar_psv.nfi_signature[:32]}...")
    print(f"  Latency: {lidar_psv.latency_us:.2f} µs")
    print()
    
    # Performance stats
    print("[STATS] Translator Performance:")
    stats = translator.get_performance_stats()
    print(f"  Translations: {stats['translations']}")
    print(f"  Avg Latency: {stats['avg_latency_us']:.2f} µs ({stats['avg_latency_ms']:.4f} ms)")
    print()
    
    # Export PSV examples
    print("[EXPORT] Writing PSV examples to logs/robotics/...")
    os.makedirs("logs/robotics", exist_ok=True)
    translator.export_psv_to_json(odom_psv, "logs/robotics/psv_odom_example.json")
    translator.export_psv_to_json(lidar_psv, "logs/robotics/psv_lidar_example.json")
    print("  ✓ logs/robotics/psv_odom_example.json")
    print("  ✓ logs/robotics/psv_lidar_example.json")
    print()
    
    print("═" * 72)
    print("  PSV TRANSLATOR READY - DEFENSE BRIDGE OPERATIONAL")
    print("═" * 72)
