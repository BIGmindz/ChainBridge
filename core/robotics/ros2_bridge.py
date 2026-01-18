#!/usr/bin/env python3
"""
Benson ROS 2 Defense Bridge
===========================

ROS 2 node that subscribes to Carnegie Robotics telemetry topics
(/odom, /scan) and translates them into Proposed Strategic Vectors (PSV)
with HMAC-512 NFI signatures for Rust Kernel judgment.

This bridge is a TRANSLATOR ONLY - it has ZERO authority to execute
physical movements. All motor commands require Rust Kernel approval.

Architecture:
- Subscribes to /odom (nav_msgs/Odometry) and /scan (sensor_msgs/LaserScan)
- Translates to PSV format with NFI signatures
- Submits to Rust Kernel for constitutional judgment
- Enforces fail-closed architecture (default: NO_MOVEMENT)

Safety Invariants:
- CB-ROB-01: No physical movement without signed Kernel Approval
- CB-SEC-01: Every ROS 2 packet must carry valid NFI signature
- CB-ROB-02: ROS 2 Bridge has ZERO authority (translation only)

Author: BENSON [GID-00]
PAC: PAC-ROS2-DEFENSE-BRIDGE-25
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.robotics.psv_translator import PSVTranslator, ProposedStrategicVector

# ROS 2 imports (conditional - graceful degradation if not available)
try:
    import rclpy
    from rclpy.node import Node
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import LaserScan
    from geometry_msgs.msg import Quaternion
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    print("[WARNING] ROS 2 not available - running in simulation mode")
    
    # Mock classes for development without ROS 2
    class Node:
        def __init__(self, node_name):
            self.node_name = node_name
        def get_logger(self):
            return self
        def info(self, msg):
            print(f"[INFO] {msg}")
        def warn(self, msg):
            print(f"[WARN] {msg}")
        def error(self, msg):
            print(f"[ERROR] {msg}")


class BensonROS2Bridge(Node if ROS2_AVAILABLE else object):
    """
    ROS 2 Defense Bridge for Carnegie Robotics Integration
    
    Subscribes to robotic telemetry and translates to PSV format
    for Rust Kernel constitutional judgment.
    """
    
    def __init__(self, gid: str = "00", nfi_signed: bool = True):
        """
        Initialize Benson ROS 2 Bridge.
        
        Args:
            gid: Agent GID (default "00" for BENSON)
            nfi_signed: Require NFI signatures (MANDATORY in production)
        """
        if ROS2_AVAILABLE:
            super().__init__('benson_defense_bridge')
        
        self.gid = gid
        self.nfi_signed = nfi_signed
        self.start_time = time.time()
        
        # Initialize PSV translator
        self.translator = PSVTranslator(gid=gid)
        
        # Performance tracking
        self.odom_count = 0
        self.scan_count = 0
        self.psv_submitted = 0
        self.psv_approved = 0
        self.psv_rejected = 0
        
        # Logging
        self.log_dir = "logs/robotics"
        os.makedirs(self.log_dir, exist_ok=True)
        self.psv_log = open(f"{self.log_dir}/psv_submission_trace.json", 'a')
        self.telemetry_log = open(f"{self.log_dir}/ros2_telemetry.log", 'a')
        
        # ROS 2 subscribers (if available)
        if ROS2_AVAILABLE:
            self.odom_sub = self.create_subscription(
                Odometry,
                '/odom',
                self.odometry_callback,
                10
            )
            self.scan_sub = self.create_subscription(
                LaserScan,
                '/scan',
                self.scan_callback,
                10
            )
            self.get_logger().info("ROS 2 Defense Bridge initialized")
            self.get_logger().info(f"NFI Instance: {self.translator.nfi_instance}")
            self.get_logger().info(f"NFI Signing: {'ENABLED' if nfi_signed else 'DISABLED'}")
        else:
            print("[INIT] ROS 2 Bridge in simulation mode")
            print(f"[INIT] NFI Instance: {self.translator.nfi_instance}")
    
    def quaternion_to_euler(self, q) -> Dict[str, float]:
        """Convert quaternion to Euler angles (roll, pitch, yaw)"""
        # Simplified conversion (assumes Quaternion message type)
        if hasattr(q, 'x'):
            x, y, z, w = q.x, q.y, q.z, q.w
        else:
            x, y, z, w = q
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return {"roll": roll, "pitch": pitch, "yaw": yaw}
    
    def odometry_callback(self, msg):
        """
        Callback for /odom topic (nav_msgs/Odometry)
        
        Translates odometry data to PSV and submits to Rust Kernel.
        """
        self.odom_count += 1
        
        # Extract position
        position = {
            "x": msg.pose.pose.position.x,
            "y": msg.pose.pose.position.y,
            "z": msg.pose.pose.position.z
        }
        
        # Extract velocity
        velocity = {
            "vx": msg.twist.twist.linear.x,
            "vy": msg.twist.twist.linear.y,
            "vz": msg.twist.twist.linear.z
        }
        
        # Extract orientation (quaternion to euler)
        orientation = self.quaternion_to_euler(msg.pose.pose.orientation)
        
        # Log raw telemetry
        self._log_telemetry("ODOMETRY", {
            "position": position,
            "velocity": velocity,
            "orientation": orientation
        })
        
        # Translate to PSV
        try:
            psv = self.translator.translate_odometry(
                position=position,
                velocity=velocity,
                orientation=orientation,
                source_topic="/odom",
                justification="Carnegie Robotics odometry telemetry translation for Rust Kernel constitutional judgment and position tracking"
            )
            
            # Submit PSV to Rust Kernel (simulation)
            self._submit_psv_to_kernel(psv)
            
        except Exception as e:
            if ROS2_AVAILABLE:
                self.get_logger().error(f"Odometry translation failed: {e}")
            else:
                print(f"[ERROR] Odometry translation failed: {e}")
    
    def scan_callback(self, msg):
        """
        Callback for /scan topic (sensor_msgs/LaserScan)
        
        Translates LIDAR scan data to PSV and submits to Rust Kernel.
        """
        self.scan_count += 1
        
        # Extract ranges and angles
        ranges = list(msg.ranges)
        angles = [
            msg.angle_min + i * msg.angle_increment
            for i in range(len(ranges))
        ]
        intensities = list(msg.intensities) if msg.intensities else None
        
        # Log raw telemetry
        self._log_telemetry("LIDAR_SCAN", {
            "num_points": len(ranges),
            "min_range": min(ranges) if ranges else 0,
            "max_range": max(ranges) if ranges else 0
        })
        
        # Translate to PSV
        try:
            psv = self.translator.translate_lidar_scan(
                ranges=ranges,
                angles=angles,
                intensities=intensities,
                source_topic="/scan",
                justification="Carnegie Robotics LIDAR scan telemetry for obstacle detection and path planning safety verification"
            )
            
            # Submit PSV to Rust Kernel (simulation)
            self._submit_psv_to_kernel(psv)
            
        except Exception as e:
            if ROS2_AVAILABLE:
                self.get_logger().error(f"LIDAR scan translation failed: {e}")
            else:
                print(f"[ERROR] LIDAR scan translation failed: {e}")
    
    def _submit_psv_to_kernel(self, psv: ProposedStrategicVector):
        """
        Submit PSV to Rust Kernel for constitutional judgment.
        
        In production, this would make an RPC call to the Rust Kernel.
        For now, we simulate the submission and log the PSV.
        """
        self.psv_submitted += 1
        
        # Log PSV submission
        psv_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "psv_id": psv.psv_id,
            "telemetry_type": psv.telemetry_type,
            "source_topic": psv.source_topic,
            "nfi_instance": psv.nfi_instance,
            "nfi_signature": psv.nfi_signature[:32] + "...",
            "latency_us": psv.latency_us,
            "sequence": psv.sequence_number
        }
        
        self.psv_log.write(json.dumps(psv_record) + "\n")
        self.psv_log.flush()
        
        # Simulate Rust Kernel judgment (in production, this is RPC)
        # For now, approve all PSVs without proposed movements
        if psv.proposed_movement is None:
            judgment = "APPROVED_OBSERVATION"
            self.psv_approved += 1
        else:
            # Proposed movements require actual Kernel judgment
            judgment = "PENDING_KERNEL_JUDGMENT"
        
        if ROS2_AVAILABLE:
            self.get_logger().info(
                f"PSV {psv.psv_id} submitted | "
                f"Type: {psv.telemetry_type} | "
                f"Judgment: {judgment} | "
                f"Latency: {psv.latency_us:.2f}µs"
            )
    
    def _log_telemetry(self, telemetry_type: str, data: Dict[str, Any]):
        """Log raw telemetry data"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": telemetry_type,
            "data": data
        }
        self.telemetry_log.write(json.dumps(log_entry) + "\n")
        self.telemetry_log.flush()
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate bridge status report"""
        uptime = time.time() - self.start_time
        translator_stats = self.translator.get_performance_stats()
        
        return {
            "bridge_status": "OPERATIONAL",
            "uptime_seconds": uptime,
            "gid": self.gid,
            "nfi_instance": self.translator.nfi_instance,
            "nfi_signing": "ENABLED" if self.nfi_signed else "DISABLED",
            "telemetry": {
                "odometry_messages": self.odom_count,
                "lidar_scans": self.scan_count
            },
            "psv_stats": {
                "submitted": self.psv_submitted,
                "approved": self.psv_approved,
                "rejected": self.psv_rejected,
                "pending": self.psv_submitted - self.psv_approved - self.psv_rejected
            },
            "translator_performance": translator_stats
        }
    
    def __del__(self):
        """Cleanup on shutdown"""
        if hasattr(self, 'psv_log'):
            self.psv_log.close()
        if hasattr(self, 'telemetry_log'):
            self.telemetry_log.close()


def main(args=None):
    """Main entry point for ROS 2 node"""
    if not ROS2_AVAILABLE:
        print("[ERROR] ROS 2 not available - cannot run bridge node")
        print("[INFO] Install ROS 2 Humble: https://docs.ros.org/en/humble/Installation.html")
        return
    
    # Initialize ROS 2
    rclpy.init(args=args)
    
    # Create bridge node
    bridge = BensonROS2Bridge(gid="00", nfi_signed=True)
    
    try:
        # Spin node
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        status = bridge.get_status_report()
        bridge.get_logger().info("=" * 72)
        bridge.get_logger().info("ROS 2 DEFENSE BRIDGE SHUTDOWN")
        bridge.get_logger().info(json.dumps(status, indent=2))
        bridge.get_logger().info("=" * 72)
        
        bridge.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    if ROS2_AVAILABLE:
        main()
    else:
        # Simulation mode for development
        print("=" * 72)
        print("  BENSON ROS 2 DEFENSE BRIDGE - SIMULATION MODE")
        print("  PAC: PAC-ROS2-DEFENSE-BRIDGE-25")
        print("=" * 72)
        print()
        
        bridge = BensonROS2Bridge(gid="00", nfi_signed=True)
        print(f"[INIT] Bridge initialized in simulation mode")
        print(f"[INIT] NFI Instance: {bridge.translator.nfi_instance}")
        print()
        print("[INFO] ROS 2 not available - install with:")
        print("  $ sudo apt install ros-humble-desktop")
        print("  $ source /opt/ros/humble/setup.bash")
        print()
        print("=" * 72)
