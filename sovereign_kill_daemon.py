#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P16-DEPLOY — Sovereign Kill Switch Daemon
# Physical Sovereignty Layer - Hardware Binding
# Governance Tier: CONSTITUTIONAL_LAW
# Invariant: FAIL_CLOSED | NO_BACKDOORS | PHYSICAL_BINDING
# ═══════════════════════════════════════════════════════════════════════════════
"""
Sovereign Kill Switch Daemon

This daemon monitors hardware signals and terminates the process if the
physical link is severed. It implements a "Pull Up" configuration where:

- Safe State = Circuit Closed to Ground (LOW)
- Danger State = Circuit Open / Wire Cut (HIGH)

Vector 1: GPIO (Raspberry Pi / ARM)
- Pin 18 (BCM) with internal pull-up resistor
- 50Hz polling
- HIGH signal = kill

Vector 2: Serial (USB / Desktop)
- DTR/DSR signaling on /dev/ttyUSB0
- DTR energized, DSR monitored
- DSR loss = kill

Constitutional Mandate:
"The circuit is the law. The break in the circuit is the execution of the law."
"""

import logging
import os
import signal
import threading
import time

logger = logging.getLogger("SovereignShield")

# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 1: GPIO (For Pi/ARM)
# ═══════════════════════════════════════════════════════════════════════════════
try:
    import RPi.GPIO as GPIO
    GPIO_ENABLED = True
except ImportError:
    GPIO_ENABLED = False

# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR 2: Serial (For USB/Desktop)
# ═══════════════════════════════════════════════════════════════════════════════
try:
    import serial
    SERIAL_ENABLED = True
except ImportError:
    SERIAL_ENABLED = False


class SovereignKillSwitch:
    """
    Hardware Kill Switch with GPIO and Serial monitoring.
    
    Configuration: Pull-Up Resistor
    - Safe = Closed circuit to ground (LOW)
    - Danger = Open circuit / wire cut (HIGH)
    
    Usage:
        from sovereign_kill_daemon import kill_switch
        kill_switch.start()  # In your startup code
    """
    
    def __init__(self, gpio_pin: int = 18, serial_port: str = "/dev/ttyUSB0"):
        self.gpio_pin = gpio_pin
        self.serial_port = serial_port
        self.running = True
        self._armed = False
        self._gpio_thread = None
        self._serial_thread = None
    
    def trigger_kill(self, reason: str) -> None:
        """
        Execute immediate process termination.
        
        NO GRACEFUL SHUTDOWN - this is a hardware interrupt.
        """
        print(f"🚨 HARDWARE KILL TRIGGERED: {reason} 🚨")
        logger.critical(f"HARDWARE KILL: {reason}")
        
        # Log to audit file
        try:
            audit_path = "logs/sovereign_kill_audit.log"
            os.makedirs(os.path.dirname(audit_path), exist_ok=True)
            with open(audit_path, "a") as f:
                from datetime import datetime
                f.write(f"{datetime.utcnow().isoformat()} | KILL | PID={os.getpid()} | REASON={reason}\n")
        except Exception:
            pass
        
        # Force kill the process group
        try:
            os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)
        except Exception:
            os.kill(os.getpid(), signal.SIGKILL)
    
    def monitor_gpio(self) -> None:
        """
        Monitor GPIO pin for kill signal.
        
        SETUP: Pull Up Resistor
        - Safe State = Circuit Closed to Ground (LOW)
        - Danger State = Circuit Open / Wire Cut (HIGH)
        """
        if not GPIO_ENABLED:
            logger.warning("GPIO Not Available. Skipping Vector 1.")
            return
        
        try:
            # Configure pin with pull-up resistor
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            logger.info(f"🛡️ GPIO Shield Active on Pin {self.gpio_pin}")
            
            while self.running:
                state = GPIO.input(self.gpio_pin)
                if state == GPIO.HIGH:
                    self.trigger_kill("GPIO SIGNAL LOSS (OPEN CIRCUIT)")
                time.sleep(0.02)  # 50Hz Polling
                
        except Exception as e:
            logger.error(f"GPIO Shield Error: {e}")
            # Only fail-closed if we were actually monitoring
            if self._armed:
                self.trigger_kill(f"GPIO HARDWARE FAILURE: {e}")
    
    def monitor_serial(self) -> None:
        """
        Monitor serial port DTR/DSR for kill signal.
        
        SETUP: DTR energized, DSR monitored
        - Safe State = DTR connected to DSR (True)
        - Danger State = Disconnected (False)
        """
        if not SERIAL_ENABLED:
            logger.warning("PySerial Not Available. Skipping Vector 2.")
            return
        
        try:
            with serial.Serial(self.serial_port) as ser:
                ser.dtr = True  # Energize DTR
                logger.info(f"🛡️ Serial Shield Active on {self.serial_port}")
                
                while self.running:
                    # Safe State = DTR connected to DSR (True)
                    # Danger State = Disconnected (False)
                    if not ser.dsr:
                        self.trigger_kill("SERIAL DSR SIGNAL LOSS")
                    time.sleep(0.02)  # 50Hz Polling
                    
        except serial.SerialException as e:
            # Serial port not available - only log, don't fail
            logger.warning(f"Serial Shield Not Available: {e}")
        except Exception as e:
            logger.error(f"Serial Shield Error: {e}")
            # If hardware fails while armed, fail closed
            if self._armed:
                self.trigger_kill(f"SERIAL HARDWARE FAILURE: {e}")
    
    def start(self) -> None:
        """
        Start the kill switch daemon.
        
        Spawns monitoring threads for GPIO and Serial vectors.
        """
        if self._armed:
            logger.warning("SovereignKillSwitch already armed")
            return
        
        logger.info("=" * 60)
        logger.info("⚡ SOVEREIGN KILL SWITCH ARMING")
        logger.info(f"   GPIO Pin: {self.gpio_pin} (Vector 1)")
        logger.info(f"   Serial Port: {self.serial_port} (Vector 2)")
        logger.info("=" * 60)
        
        self._armed = True
        self.running = True
        
        # Start monitoring threads
        self._gpio_thread = threading.Thread(
            target=self.monitor_gpio,
            name="SovereignKillSwitch-GPIO",
            daemon=True
        )
        self._serial_thread = threading.Thread(
            target=self.monitor_serial,
            name="SovereignKillSwitch-Serial",
            daemon=True
        )
        
        self._gpio_thread.start()
        self._serial_thread.start()
        
        logger.info("🛡️ SOVEREIGN KILL SWITCH ARMED")
        logger.info("   The circuit is the law.")
    
    def stop(self) -> None:
        """Stop the kill switch daemon (for graceful shutdown only)."""
        if not self._armed:
            return
        
        self.running = False
        self._armed = False
        
        if self._gpio_thread and self._gpio_thread.is_alive():
            self._gpio_thread.join(timeout=1.0)
        if self._serial_thread and self._serial_thread.is_alive():
            self._serial_thread.join(timeout=1.0)
        
        # Cleanup GPIO
        if GPIO_ENABLED:
            try:
                GPIO.cleanup(self.gpio_pin)
            except Exception:
                pass
        
        logger.info("🛡️ Sovereign Kill Switch DISARMED")
    
    @property
    def is_armed(self) -> bool:
        """Check if the kill switch is currently armed."""
        return self._armed


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Default configuration from environment
kill_switch = SovereignKillSwitch(
    gpio_pin=int(os.getenv("HW_KILL_GPIO_PIN", "18")),
    serial_port=os.getenv("HW_KILL_PORT", "/dev/ttyUSB0")
)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN (for standalone testing)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("=" * 60)
    print("🛡️ SOVEREIGN KILL SWITCH TEST MODE")
    print("=" * 60)
    print(f"GPIO Available: {GPIO_ENABLED}")
    print(f"Serial Available: {SERIAL_ENABLED}")
    print("=" * 60)
    print("Starting daemon. Disconnect hardware to trigger kill.")
    print("=" * 60)
    
    kill_switch.start()
    
    try:
        while True:
            time.sleep(1)
            print(f"[ALIVE] Armed={kill_switch.is_armed}")
    except KeyboardInterrupt:
        print("\n[MANUAL STOP]")
        kill_switch.stop()
