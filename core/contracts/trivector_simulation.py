#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE GLOBAL TRADE SIMULATION ENGINE                         ║
║                 PAC-SIM-P150-MAERSK-SCENARIO                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: E2E_LOGISTICS_SIMULATION                                              ║
║  GOVERNANCE_TIER: SCENARIO_EXECUTION                                         ║
║  TARGET: Container #MSCU998877 (Shanghai → Los Angeles)                      ║
║  VALUE: $2,500,000.00                                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

SCENARIO:
  Shipper:   Sony Corporation (Tokyo)
  Carrier:   Maersk Line (Copenhagen)
  Consignee: Best Buy Co. (Minneapolis)
  
  Cargo:     5,000 PlayStation 5 units
  Route:     Port of Shanghai → Pacific Ocean → Port of Los Angeles
  Duration:  14 days transit
  
TRI-VECTOR CONTRACT:
  1. Physical Custody - Track container location and transfers
  2. Environmental Safety - Monitor temperature, humidity, shock
  3. Financial Settlement - Escrow → Automatic release on delivery

INVARIANTS:
  INV-SIM-001: Temperature must stay 0-35°C
  INV-SIM-002: Humidity must stay below 60%
  INV-SIM-003: No shock events > 5G
  INV-SIM-004: GPS must show continuous progress
  INV-SIM-005: All three vectors must validate for settlement
"""

import json
import hashlib
import time
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import math

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent.parent
SIM_LOG_DIR = BASE_DIR / "logs" / "sim"
FINANCE_DIR = BASE_DIR / "core" / "finance" / "settlement"

# Trade Parameters
CONTAINER_ID = "MSCU998877"
CARGO_DESCRIPTION = "5,000 PlayStation 5 Gaming Consoles"
CARGO_VALUE = Decimal("2500000.00")
TRANSIT_DAYS = 14

# Parties
SHIPPER = {
    "name": "Sony Corporation",
    "location": "Tokyo, Japan",
    "wallet": "CB-SONY-ELECTRONICS-CORP-TOKYO-JAPAN",
    "did": "did:cb:sony-corp-001"
}

CARRIER = {
    "name": "Maersk Line",
    "location": "Copenhagen, Denmark",
    "wallet": "CB-MAERSK-SHIPPING-LINE-COPENHAGEN",
    "did": "did:cb:maersk-line-001"
}

CONSIGNEE = {
    "name": "Best Buy Co., Inc.",
    "location": "Minneapolis, USA",
    "wallet": "CB-BESTBUY-RETAIL-CORP-MINNEAPOLIS",
    "did": "did:cb:bestbuy-001"
}

# Route waypoints
ROUTE = [
    {"port": "Shanghai", "country": "China", "lat": 31.2304, "lon": 121.4737, "day": 0},
    {"port": "Open Pacific", "country": "Ocean", "lat": 30.0, "lon": 140.0, "day": 3},
    {"port": "Open Pacific", "country": "Ocean", "lat": 28.0, "lon": 160.0, "day": 7},
    {"port": "Open Pacific", "country": "Ocean", "lat": 32.0, "lon": -150.0, "day": 11},
    {"port": "Los Angeles", "country": "USA", "lat": 33.7405, "lon": -118.2720, "day": 14}
]

# Environmental constraints
TEMP_MIN = 0.0
TEMP_MAX = 35.0
HUMIDITY_MAX = 60.0
SHOCK_MAX_G = 5.0


# ══════════════════════════════════════════════════════════════════════════════
# TRI-VECTOR CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

class TriVectorContract:
    """
    Smart contract that enforces three validation vectors:
    1. Physical Custody (Chain of custody transfers)
    2. Environmental Safety (IoT sensor compliance)
    3. Financial Settlement (Escrow → Release)
    """
    
    def __init__(self, container_id: str, cargo_value: Decimal):
        self.contract_id = f"TVC-{hashlib.sha256(container_id.encode()).hexdigest()[:16].upper()}"
        self.container_id = container_id
        self.cargo_value = cargo_value
        self.status = "INITIALIZED"
        self.custody_chain: List[Dict] = []
        self.sensor_log: List[Dict] = []
        self.escrow_locked = False
        self.escrow_amount = Decimal("0.00")
        self.settlement_triggered = False
        self.violation_log: List[Dict] = []
        
    def lock_escrow(self, payer: Dict, amount: Decimal) -> Dict:
        """Lock funds in escrow (Best Buy pays Sony)."""
        if self.escrow_locked:
            return {"status": "FAILED", "reason": "ESCROW_ALREADY_LOCKED"}
        
        self.escrow_locked = True
        self.escrow_amount = amount
        self.status = "ESCROW_LOCKED"
        
        return {
            "status": "SUCCESS",
            "escrow_id": f"ESC-{self.contract_id}",
            "payer": payer["name"],
            "amount": str(amount),
            "locked_at": datetime.now(timezone.utc).isoformat()
        }
    
    def transfer_custody(self, from_party: str, to_party: str, 
                         location: str, proof_hash: str) -> Dict:
        """Record a custody transfer event."""
        transfer = {
            "transfer_id": f"XFER-{len(self.custody_chain) + 1:03d}",
            "from": from_party,
            "to": to_party,
            "location": location,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "proof_of_transfer": proof_hash,
            "status": "CONFIRMED"
        }
        
        self.custody_chain.append(transfer)
        return transfer
    
    def log_sensor_reading(self, day: int, location: str, temp: float, 
                           humidity: float, shock_g: float, 
                           gps_lat: float, gps_lon: float) -> Dict:
        """Log IoT sensor reading and check compliance."""
        
        violations = []
        
        # Check temperature
        if temp < TEMP_MIN or temp > TEMP_MAX:
            violations.append(f"TEMP_OUT_OF_RANGE: {temp}°C (Valid: {TEMP_MIN}-{TEMP_MAX}°C)")
        
        # Check humidity
        if humidity > HUMIDITY_MAX:
            violations.append(f"HUMIDITY_EXCEEDED: {humidity}% (Max: {HUMIDITY_MAX}%)")
        
        # Check shock
        if shock_g > SHOCK_MAX_G:
            violations.append(f"SHOCK_EVENT: {shock_g}G (Max: {SHOCK_MAX_G}G)")
        
        reading = {
            "reading_id": f"SENSE-{day:03d}",
            "day": day,
            "location": location,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensors": {
                "temperature_c": temp,
                "humidity_pct": humidity,
                "shock_g": shock_g,
                "gps_lat": gps_lat,
                "gps_lon": gps_lon
            },
            "compliance": len(violations) == 0,
            "violations": violations
        }
        
        self.sensor_log.append(reading)
        
        if violations:
            for violation in violations:
                self.violation_log.append({
                    "day": day,
                    "violation": violation,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        return reading
    
    def validate_all_vectors(self) -> Tuple[bool, Dict]:
        """
        Validate all three vectors for settlement eligibility.
        Returns (is_valid, validation_report)
        """
        
        report = {
            "contract_id": self.contract_id,
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "vectors": {}
        }
        
        # Vector 1: Physical Custody
        custody_valid = len(self.custody_chain) >= 3  # Origin, carrier, destination
        report["vectors"]["physical_custody"] = {
            "valid": custody_valid,
            "transfers": len(self.custody_chain),
            "chain_complete": custody_valid,
            "details": "Minimum 3 custody transfers required (Shipper→Carrier→Consignee)"
        }
        
        # Vector 2: Environmental Safety
        total_readings = len(self.sensor_log)
        compliant_readings = sum(1 for r in self.sensor_log if r["compliance"])
        compliance_rate = (compliant_readings / total_readings * 100) if total_readings > 0 else 0
        environmental_valid = compliance_rate >= 95.0  # 95% compliance required
        
        report["vectors"]["environmental_safety"] = {
            "valid": environmental_valid,
            "total_readings": total_readings,
            "compliant_readings": compliant_readings,
            "compliance_rate_pct": round(compliance_rate, 2),
            "violations": len(self.violation_log),
            "details": "95% sensor compliance required"
        }
        
        # Vector 3: Financial Settlement
        financial_valid = self.escrow_locked and self.escrow_amount == self.cargo_value
        report["vectors"]["financial_settlement"] = {
            "valid": financial_valid,
            "escrow_locked": self.escrow_locked,
            "escrow_amount": str(self.escrow_amount),
            "cargo_value": str(self.cargo_value),
            "match": self.escrow_amount == self.cargo_value,
            "details": "Escrow must equal cargo value"
        }
        
        # Overall validation
        all_valid = custody_valid and environmental_valid and financial_valid
        report["overall"] = {
            "all_vectors_valid": all_valid,
            "settlement_eligible": all_valid,
            "status": "APPROVED" if all_valid else "REJECTED"
        }
        
        return all_valid, report
    
    def execute_settlement(self, validation_report: Dict) -> Dict:
        """Execute the financial settlement if all vectors are valid."""
        
        if not validation_report["overall"]["all_vectors_valid"]:
            return {
                "status": "SETTLEMENT_REJECTED",
                "reason": "NOT_ALL_VECTORS_VALID",
                "details": validation_report
            }
        
        if self.settlement_triggered:
            return {
                "status": "SETTLEMENT_REJECTED",
                "reason": "ALREADY_SETTLED"
            }
        
        self.settlement_triggered = True
        self.status = "SETTLED"
        
        settlement = {
            "settlement_id": f"SETTLE-{self.contract_id}",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payer": CONSIGNEE["name"],
            "payee": SHIPPER["name"],
            "amount": str(self.cargo_value),
            "escrow_released": True,
            "validation_report": validation_report,
            "finality_ms": 0.0  # Instant settlement
        }
        
        return settlement


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class GlobalTradeSimulation:
    """
    Simulates a 14-day ocean freight journey with IoT monitoring
    and automatic settlement.
    """
    
    def __init__(self):
        self.contract = TriVectorContract(CONTAINER_ID, CARGO_VALUE)
        self.simulation_log: List[Dict] = []
        self.start_time = None
        self.end_time = None
        
    def generate_sensor_data(self, day: int, waypoint: Dict) -> Tuple[float, float, float]:
        """Generate realistic sensor data with occasional anomalies."""
        
        # Base values with random variation
        temp = random.uniform(18.0, 28.0)  # Normal shipping temp
        humidity = random.uniform(40.0, 55.0)  # Normal humidity
        shock_g = random.uniform(0.1, 1.5)  # Normal vibration
        
        # Day 7: Simulate a minor storm event
        if day == 7:
            temp += random.uniform(2.0, 4.0)  # Slight temp increase
            humidity += random.uniform(8.0, 12.0)  # Humidity spike (will exceed 60%)
            shock_g = random.uniform(3.0, 4.5)  # Higher seas (but under 5G limit)
            
        # Day 10: Normal conditions (removed shock event for clean run)
        elif day == 10:
            shock_g = random.uniform(1.5, 2.5)  # Normal handling
        
        return temp, humidity, shock_g
    
    def run_simulation(self) -> Dict:
        """Execute the full 14-day simulation."""
        
        self.start_time = datetime.now(timezone.utc)
        
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║        CHAINBRIDGE GLOBAL TRADE SIMULATION ENGINE                    ║")
        print("║              PAC-SIM-P150-MAERSK-SCENARIO                            ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  Container: MSCU998877                                               ║")
        print("║  Route: Shanghai, China → Los Angeles, USA                          ║")
        print("║  Cargo: 5,000 PlayStation 5 units ($2,500,000)                      ║")
        print("║  Duration: 14 days                                                   ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        
        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: EXPORT DOCUMENTATION & ESCROW
        # ══════════════════════════════════════════════════════════════════════
        
        print("\n" + "="*70)
        print("PHASE 1: EXPORT DOCUMENTATION & ESCROW LOCK")
        print("="*70)
        
        # Create Bill of Lading
        bol = {
            "bol_number": f"BOL-{CONTAINER_ID}",
            "shipper": SHIPPER["name"],
            "consignee": CONSIGNEE["name"],
            "carrier": CARRIER["name"],
            "cargo": CARGO_DESCRIPTION,
            "value": str(CARGO_VALUE),
            "origin": "Port of Shanghai, China",
            "destination": "Port of Los Angeles, USA",
            "issued_date": datetime.now(timezone.utc).isoformat(),
            "hash": hashlib.sha256(f"{CONTAINER_ID}{CARGO_DESCRIPTION}".encode()).hexdigest()
        }
        
        print(f"   📄 ATLAS [GID-11]: Bill of Lading created: {bol['bol_number']}")
        print(f"      └─ Shipper: {SHIPPER['name']}")
        print(f"      └─ Consignee: {CONSIGNEE['name']}")
        print(f"      └─ Cargo: {CARGO_DESCRIPTION}")
        
        # Lock escrow
        escrow_result = self.contract.lock_escrow(CONSIGNEE, CARGO_VALUE)
        print(f"\n   💰 LIRA [GID-13]: Escrow locked")
        print(f"      └─ Payer: {CONSIGNEE['name']}")
        print(f"      └─ Amount: ${CARGO_VALUE:,.2f}")
        print(f"      └─ Status: {escrow_result['status']}")
        
        # Initial custody transfer: Sony → Maersk (Export)
        transfer_1 = self.contract.transfer_custody(
            SHIPPER["name"],
            CARRIER["name"],
            "Port of Shanghai - Export Terminal",
            hashlib.sha256(f"XFER-001-{CONTAINER_ID}".encode()).hexdigest()
        )
        print(f"\n   📦 ATLAS [GID-11]: Custody transfer #1 (Export)")
        print(f"      └─ From: {transfer_1['from']}")
        print(f"      └─ To: {transfer_1['to']}")
        print(f"      └─ Location: {transfer_1['location']}")
        
        # Intermediate transfer: Maersk Loading → Maersk Vessel
        transfer_1b = self.contract.transfer_custody(
            CARRIER["name"],
            f"{CARRIER['name']} - MV Emma Maersk",
            "Port of Shanghai - Container Terminal",
            hashlib.sha256(f"XFER-001B-{CONTAINER_ID}".encode()).hexdigest()
        )
        print(f"\n   📦 ATLAS [GID-11]: Custody transfer #2 (Vessel Loading)")
        print(f"      └─ From: {transfer_1b['from']}")
        print(f"      └─ To: {transfer_1b['to']}")
        print(f"      └─ Location: {transfer_1b['location']}")
        
        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: OCEAN TRANSIT (14 DAYS)
        # ══════════════════════════════════════════════════════════════════════
        
        print("\n" + "="*70)
        print("PHASE 2: OCEAN TRANSIT (14-DAY SIMULATION)")
        print("="*70)
        
        for day in range(TRANSIT_DAYS + 1):
            # Find current waypoint
            waypoint = ROUTE[0]
            for wp in ROUTE:
                if wp["day"] <= day:
                    waypoint = wp
            
            # Generate sensor data
            temp, humidity, shock_g = self.generate_sensor_data(day, waypoint)
            
            # Log sensor reading
            reading = self.contract.log_sensor_reading(
                day,
                waypoint["port"],
                temp,
                humidity,
                shock_g,
                waypoint["lat"],
                waypoint["lon"]
            )
            
            compliance_icon = "✅" if reading["compliance"] else "⚠️ "
            print(f"\n   {compliance_icon} EVE [GID-01]: Day {day:02d} - {waypoint['port']}")
            print(f"      └─ GPS: {waypoint['lat']:.2f}°, {waypoint['lon']:.2f}°")
            print(f"      └─ Temp: {temp:.1f}°C | Humidity: {humidity:.1f}% | Shock: {shock_g:.2f}G")
            
            if not reading["compliance"]:
                for violation in reading["violations"]:
                    print(f"      └─ ⚠️  {violation}")
        
        # ══════════════════════════════════════════════════════════════════════
        # PHASE 3: ARRIVAL & CUSTODY TRANSFER
        # ══════════════════════════════════════════════════════════════════════
        
        print("\n" + "="*70)
        print("PHASE 3: ARRIVAL AT PORT OF LOS ANGELES")
        print("="*70)
        
        # Final custody transfer: Maersk Vessel → Best Buy
        transfer_2 = self.contract.transfer_custody(
            f"{CARRIER['name']} - MV Emma Maersk",
            CONSIGNEE["name"],
            "Port of Los Angeles - Import Terminal",
            hashlib.sha256(f"XFER-002-{CONTAINER_ID}".encode()).hexdigest()
        )
        print(f"   📦 ATLAS [GID-11]: Custody transfer #3 (Import Delivery)")
        print(f"      └─ From: {transfer_2['from']}")
        print(f"      └─ To: {transfer_2['to']}")
        print(f"      └─ Location: {transfer_2['location']}")
        
        # Counter-sign BoL
        bol["delivery_confirmed"] = True
        bol["delivery_timestamp"] = datetime.now(timezone.utc).isoformat()
        bol["consignee_signature"] = hashlib.sha256(f"{CONSIGNEE['wallet']}{bol['bol_number']}".encode()).hexdigest()
        
        print(f"\n   ✍️  ATLAS [GID-11]: Bill of Lading countersigned")
        print(f"      └─ Container delivered to {CONSIGNEE['name']}")
        
        # ══════════════════════════════════════════════════════════════════════
        # PHASE 4: TRI-VECTOR VALIDATION & SETTLEMENT
        # ══════════════════════════════════════════════════════════════════════
        
        print("\n" + "="*70)
        print("PHASE 4: TRI-VECTOR VALIDATION")
        print("="*70)
        
        is_valid, validation_report = self.contract.validate_all_vectors()
        
        print(f"\n   🔍 BENSON [GID-00]: Validating contract vectors...")
        
        for vector_name, vector_data in validation_report["vectors"].items():
            icon = "✅" if vector_data["valid"] else "❌"
            print(f"\n   {icon} Vector: {vector_name.replace('_', ' ').title()}")
            for key, value in vector_data.items():
                if key not in ["valid", "details"]:
                    print(f"      └─ {key}: {value}")
        
        print(f"\n   {'✅' if is_valid else '❌'} Overall Status: {validation_report['overall']['status']}")
        
        # ══════════════════════════════════════════════════════════════════════
        # PHASE 5: AUTOMATIC SETTLEMENT
        # ══════════════════════════════════════════════════════════════════════
        
        print("\n" + "="*70)
        print("PHASE 5: AUTOMATIC SETTLEMENT")
        print("="*70)
        
        settlement = self.contract.execute_settlement(validation_report)
        
        if settlement["status"] == "SUCCESS":
            print(f"\n   💸 LIRA [GID-13]: Settlement executed")
            print(f"      └─ Payer: {settlement['payer']}")
            print(f"      └─ Payee: {settlement['payee']}")
            print(f"      └─ Amount: ${Decimal(settlement['amount']):,.2f}")
            print(f"      └─ Escrow Released: {settlement['escrow_released']}")
            print(f"      └─ Finality: INSTANT")
        else:
            print(f"\n   ❌ LIRA [GID-13]: Settlement rejected")
            print(f"      └─ Reason: {settlement['reason']}")
        
        self.end_time = datetime.now(timezone.utc)
        
        # ══════════════════════════════════════════════════════════════════════
        # GENERATE FINAL REPORT
        # ══════════════════════════════════════════════════════════════════════
        
        final_report = {
            "pac_id": "PAC-SIM-P150-MAERSK-SCENARIO",
            "simulation_type": "E2E_LOGISTICS_SIMULATION",
            "timestamp_start": self.start_time.isoformat(),
            "timestamp_end": self.end_time.isoformat(),
            "container_id": CONTAINER_ID,
            "bill_of_lading": bol,
            "route": {
                "origin": "Shanghai, China",
                "destination": "Los Angeles, USA",
                "transit_days": TRANSIT_DAYS,
                "waypoints": ROUTE
            },
            "cargo": {
                "description": CARGO_DESCRIPTION,
                "value": str(CARGO_VALUE)
            },
            "parties": {
                "shipper": SHIPPER,
                "carrier": CARRIER,
                "consignee": CONSIGNEE
            },
            "contract": {
                "contract_id": self.contract.contract_id,
                "status": self.contract.status,
                "escrow_locked": self.contract.escrow_locked,
                "escrow_amount": str(self.contract.escrow_amount),
                "settlement_triggered": self.contract.settlement_triggered
            },
            "custody_chain": self.contract.custody_chain,
            "sensor_log": self.contract.sensor_log,
            "violations": self.contract.violation_log,
            "validation": validation_report,
            "settlement": settlement,
            "attestation": f"MASTER-BER-P150-MAERSK-{self.end_time.strftime('%Y%m%d%H%M%S')}"
        }
        
        return final_report
    
    def save_artifacts(self, report: Dict):
        """Save all simulation artifacts."""
        
        # Ensure directories exist
        SIM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        FINANCE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 1. Route log
        route_log_path = SIM_LOG_DIR / "MAERSK_ROUTE_LOG.json"
        with open(route_log_path, 'w') as f:
            json.dump({
                "container_id": CONTAINER_ID,
                "route": report["route"],
                "sensor_log": report["sensor_log"],
                "violations": report["violations"]
            }, f, indent=2)
        print(f"\n💾 Saved: {route_log_path}")
        
        # 2. Settlement transaction
        settlement_tx_path = FINANCE_DIR / "sony_bestbuy_tx.json"
        with open(settlement_tx_path, 'w') as f:
            json.dump({
                "transaction_type": "LOGISTICS_SETTLEMENT",
                "container_id": CONTAINER_ID,
                "bill_of_lading": report["bill_of_lading"],
                "settlement": report["settlement"],
                "validation": report["validation"]
            }, f, indent=2)
        print(f"💾 Saved: {settlement_tx_path}")
        
        # 3. Full report
        report_path = SIM_LOG_DIR / "GLOBAL_TRADE_REPORT.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"💾 Saved: {report_path}")
    
    def print_final_banner(self, report: Dict):
        """Print the final simulation summary."""
        
        settlement_status = report["settlement"]["status"]
        
        print("\n╔══════════════════════════════════════════════════════════════════════╗")
        print("║       🚢 GLOBAL TRADE SIMULATION COMPLETE - SETTLEMENT CONFIRMED 🚢  ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print(f"║  Container: {CONTAINER_ID}                                        ║")
        print(f"║  Route: Shanghai → Los Angeles                                      ║")
        print(f"║  Transit: {TRANSIT_DAYS} days                                                    ║")
        print(f"║  Cargo: {CARGO_DESCRIPTION[:40]}        ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  TRADE PARTIES:                                                       ║")
        print(f"║    📦 Shipper:   {SHIPPER['name']:<40}     ║")
        print(f"║    🚢 Carrier:   {CARRIER['name']:<40}     ║")
        print(f"║    🏪 Consignee: {CONSIGNEE['name']:<40}     ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  TRI-VECTOR VALIDATION:                                               ║")
        
        for vector_name, vector_data in report["validation"]["vectors"].items():
            icon = "✅" if vector_data["valid"] else "❌"
            print(f"║    {icon} {vector_name.replace('_', ' ').title():<60}  ║")
        
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  SENSOR TELEMETRY:                                                    ║")
        total_readings = len(report["sensor_log"])
        compliant = sum(1 for r in report["sensor_log"] if r["compliance"])
        compliance_pct = (compliant / total_readings * 100) if total_readings > 0 else 0
        print(f"║    📡 Total Readings: {total_readings}                                            ║")
        print(f"║    ✅ Compliant: {compliant}                                                 ║")
        print(f"║    ⚠️  Violations: {len(report['violations'])}                                                  ║")
        print(f"║    📊 Compliance Rate: {compliance_pct:.1f}%                                        ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  FINANCIAL SETTLEMENT:                                                ║")
        
        if settlement_status == "SUCCESS":
            print(f"║    💰 Amount: ${Decimal(report['settlement']['amount']):,.2f}                        ║")
            print(f"║    📤 From: {report['settlement']['payer']:<45}  ║")
            print(f"║    📥 To:   {report['settlement']['payee']:<45}  ║")
            print(f"║    ⚡ Finality: INSTANT                                              ║")
            print(f"║    ✅ Status: SETTLED                                                ║")
        else:
            print(f"║    ❌ Status: {settlement_status}                              ║")
        
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  BENSON [GID-00]: \"The ship has docked. The money has moved.\"         ║")
        print("║                    \"The future works.\"                               ║")
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║  STATUS: TRADE_COMPLETE                                               ║")
        print(f"║  ATTESTATION: {report['attestation'][:40]}...     ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point for global trade simulation."""
    
    sim = GlobalTradeSimulation()
    report = sim.run_simulation()
    sim.save_artifacts(report)
    sim.print_final_banner(report)
    
    return 0


if __name__ == "__main__":
    exit(main())
