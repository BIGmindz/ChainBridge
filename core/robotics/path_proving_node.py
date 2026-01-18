#!/usr/bin/env python3
"""
Path Proving Node - Reflex Lattice Executor
============================================

Executes autonomous trajectory with 5-meter look-ahead buffer requirement.
The robot only enters spaces it has already proven it can safely navigate.

PAC: PAC-PATH-PROVING-30
Classification: LAW / AUTONOMOUS-TRAJECTORY
Security: DEFENSE_GRADE

Reflex Lattice Concept:
- 1km total path divided into 100,000 segments (10mm each)
- Minimum 5.0m look-ahead buffer (500 segments) required before movement
- Each segment is NFI-signed and constitutionally validated
- Emergency halt if buffer drops below 5.0m

The Paradigm Shift:
- Legacy Robotics: React to obstacles (fail-open)
- ChainBridge: Only enter proven-safe spaces (fail-closed)

Author: BENSON [GID-00]
Lead Agent: QID-08 (Alex-Quantum) for path synthesis
Architect: JEFFREY
"""

import os
import sys
import json
import time
import hashlib
import hmac
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ROS 2 imports (conditional)
try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    print("[WARNING] ROS 2 not available - running in simulation mode")
    
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


class PathProvingNode(Node if ROS2_AVAILABLE else object):
    """
    Path Proving Node with Reflex Lattice
    
    Maintains 5-meter look-ahead buffer of NFI-signed path segments.
    Only moves when sufficient proven-safe path exists ahead.
    """
    
    def __init__(self):
        """Initialize Path Proving Node"""
        if ROS2_AVAILABLE:
            super().__init__('path_proving_node')
            self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
            self.subscription = self.create_subscription(
                String, '/reflex_buffer', self.buffer_callback, 10
            )
        
        # Agent configuration
        self.gid = "00"
        self.lead_agent = "QID-08"
        self.nfi_instance = "BENSON-PROD-01"
        
        # Reflex lattice parameters
        self.segment_size_m = 0.01  # 10mm per segment
        self.look_ahead_required_m = 5.0  # 5-meter buffer required
        self.look_ahead_required_segments = int(self.look_ahead_required_m / self.segment_size_m)
        
        # Path state
        self.signed_segments: List[Dict[str, Any]] = []
        self.buffer_depth_m = 0.0
        self.buffer_depth_segments = 0
        self.total_path_segments = 100000  # 1km at 10mm granularity
        
        # Movement state
        self.nominal_velocity_m_s = 0.5  # 0.5 m/s nominal speed
        self.current_velocity_m_s = 0.0
        self.movement_active = False
        self.emergency_halted = False
        
        # Performance tracking
        self.segments_consumed = 0
        self.distance_traveled_m = 0.0
        self.halt_events = 0
        
        # Logging
        self.log_dir = "logs/robotics"
        os.makedirs(self.log_dir, exist_ok=True)
    
    def generate_segment_signature(self, segment_data: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA512 NFI signature for path segment
        
        Args:
            segment_data: Segment dictionary to sign
            
        Returns:
            Hexadecimal HMAC-SHA512 signature
        """
        payload = json.dumps(segment_data, sort_keys=True)
        signature = hmac.new(
            self.nfi_instance.encode(),
            payload.encode(),
            hashlib.sha512
        ).hexdigest()
        return signature
    
    def verify_segment_signature(self, segment: Dict[str, Any]) -> bool:
        """
        Verify HMAC-SHA512 signature of path segment
        
        Args:
            segment: Segment with nfi_signature field
            
        Returns:
            True if signature valid, False otherwise
        """
        # Extract signature
        stored_signature = segment.get('nfi_signature')
        if not stored_signature:
            return False
        
        # Create copy without signature for verification
        segment_copy = segment.copy()
        del segment_copy['nfi_signature']
        
        # Generate expected signature
        expected_signature = self.generate_segment_signature(segment_copy)
        
        return stored_signature == expected_signature
    
    def buffer_callback(self, msg):
        """
        ROS 2 callback for /reflex_buffer topic
        
        Receives NFI-signed path segments from synthesis swarm.
        """
        try:
            segment = json.loads(msg.data)
            
            # Verify NFI signature
            if not self.verify_segment_signature(segment):
                if ROS2_AVAILABLE:
                    self.get_logger().error(f"Signature verification failed for segment {segment.get('segment_id')}")
                else:
                    print(f"[ERROR] Signature verification failed")
                return
            
            # Add to buffer
            self.signed_segments.append(segment)
            self.buffer_depth_segments += 1
            self.buffer_depth_m = self.buffer_depth_segments * self.segment_size_m
            
            # Verify lattice integrity
            self.verify_lattice()
            
        except Exception as e:
            if ROS2_AVAILABLE:
                self.get_logger().error(f"Buffer callback error: {e}")
            else:
                print(f"[ERROR] Buffer callback: {e}")
    
    def verify_lattice(self):
        """
        Verify Reflex Lattice integrity and execute/halt accordingly
        
        Constitutional Invariant CB-REFLEX-001:
        Movement MUST HALT if look-ahead buffer < 5.0m
        """
        # Check buffer depth
        if self.buffer_depth_m >= self.look_ahead_required_m:
            # Sufficient buffer - allow movement
            if not self.movement_active:
                self.start_movement()
            else:
                self.maintain_velocity(self.nominal_velocity_m_s)
        else:
            # Insufficient buffer - emergency halt
            if self.movement_active or self.current_velocity_m_s > 0:
                self.emergency_halt(
                    reason=f"BUFFER UNDERRUN: {self.buffer_depth_m:.2f}m < {self.look_ahead_required_m}m"
                )
    
    def start_movement(self):
        """Initialize movement with nominal velocity"""
        self.movement_active = True
        self.current_velocity_m_s = self.nominal_velocity_m_s
        self.execute_velocity(self.current_velocity_m_s)
        
        if ROS2_AVAILABLE:
            self.get_logger().info(
                f"✅ MOVEMENT INITIATED: {self.nominal_velocity_m_s}m/s | "
                f"Buffer: {self.buffer_depth_m:.2f}m ({self.buffer_depth_segments} segments)"
            )
        else:
            print(f"[INFO] ✅ MOVEMENT INITIATED: {self.nominal_velocity_m_s}m/s | Buffer: {self.buffer_depth_m:.2f}m")
    
    def maintain_velocity(self, speed: float):
        """Maintain current velocity"""
        self.current_velocity_m_s = speed
        self.execute_velocity(speed)
    
    def execute_velocity(self, speed: float):
        """Publish velocity command to /cmd_vel"""
        if ROS2_AVAILABLE:
            msg = Twist()
            msg.linear.x = speed
            self.publisher_.publish(msg)
        else:
            # Simulation mode - just track state
            pass
    
    def emergency_halt(self, reason: str = "REFLEX LATTICE BREACH"):
        """
        Execute emergency halt due to constitutional violation
        
        Args:
            reason: Reason for halt (for logging)
        """
        self.movement_active = False
        self.current_velocity_m_s = 0.0
        self.emergency_halted = True
        self.halt_events += 1
        
        # Publish halt command
        if ROS2_AVAILABLE:
            msg = Twist()
            msg.linear.x = 0.0
            self.publisher_.publish(msg)
            self.get_logger().error(f"🚨 EMERGENCY HALT: {reason} 🚨")
        else:
            print(f"[ERROR] 🚨 EMERGENCY HALT: {reason} 🚨")
    
    def consume_segment(self):
        """
        Consume one path segment as robot advances
        
        This simulates the robot traveling 10mm and needing
        to consume one segment from the buffer.
        """
        if self.signed_segments:
            segment = self.signed_segments.pop(0)
            self.buffer_depth_segments -= 1
            self.buffer_depth_m = self.buffer_depth_segments * self.segment_size_m
            self.segments_consumed += 1
            self.distance_traveled_m += self.segment_size_m
            
            # Verify lattice after consumption
            self.verify_lattice()
            
            return segment
        else:
            # No segments available - this should trigger emergency halt
            self.emergency_halt(reason="SEGMENT STARVATION")
            return None
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate status report"""
        return {
            "gid": self.gid,
            "lead_agent": self.lead_agent,
            "nfi_instance": self.nfi_instance,
            "buffer_state": {
                "depth_m": self.buffer_depth_m,
                "depth_segments": self.buffer_depth_segments,
                "required_m": self.look_ahead_required_m,
                "required_segments": self.look_ahead_required_segments,
                "buffer_health": "HEALTHY" if self.buffer_depth_m >= self.look_ahead_required_m else "CRITICAL"
            },
            "movement_state": {
                "active": self.movement_active,
                "velocity_m_s": self.current_velocity_m_s,
                "emergency_halted": self.emergency_halted
            },
            "progress": {
                "segments_consumed": self.segments_consumed,
                "total_segments": self.total_path_segments,
                "completion_pct": (self.segments_consumed / self.total_path_segments) * 100 if self.total_path_segments > 0 else 0,
                "distance_traveled_m": self.distance_traveled_m
            },
            "safety": {
                "halt_events": self.halt_events
            }
        }


def main(args=None):
    """Main entry point"""
    print("=" * 72)
    print("  PATH PROVING NODE - REFLEX LATTICE EXECUTOR")
    print("  PAC: PAC-PATH-PROVING-30")
    print("  Security: DEFENSE_GRADE | Fail-Closed: ENABLED")
    print("=" * 72)
    print()
    
    if ROS2_AVAILABLE:
        rclpy.init(args=args)
        node = PathProvingNode()
        
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Path proving interrupted by user")
        finally:
            status = node.get_status_report()
            node.get_logger().info("=" * 72)
            node.get_logger().info("PATH PROVING NODE SHUTDOWN")
            node.get_logger().info(json.dumps(status, indent=2))
            node.get_logger().info("=" * 72)
            
            node.destroy_node()
            rclpy.shutdown()
    else:
        # Simulation mode
        node = PathProvingNode()
        print("[INFO] Path Proving Node initialized in simulation mode")
        print(f"[INFO] NFI Instance: {node.nfi_instance}")
        print(f"[INFO] Look-Ahead Required: {node.look_ahead_required_m}m ({node.look_ahead_required_segments} segments)")
        print()
        print("[INFO] Waiting for path synthesis from QID-08...")
        print("[INFO] Use reflex_lattice_synthesizer.py to generate path segments")
        print()


if __name__ == '__main__':
    main()
