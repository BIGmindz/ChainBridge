#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE SMART CUSTOMS FUSION MODULE                            ║
║                   PAC-LOG-P75-EXEC                                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: LOGISTICS_IMPLEMENTATION                                              ║
║  GOVERNANCE_TIER: OPERATIONAL                                                ║
║  MODE: BEHAVIORAL_INTERDICTION                                               ║
║  LANE: BORDER_CONTROL_LANE                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

FUSION GATE ARCHITECTURE:
  Layer 1 (LAW):          DocumentValidator (Atlas) - Physical/Paperwork
  Layer 2 (INTELLIGENCE): RouteSentinel (Eve) - Behavioral/Telemetry
  Fusion Layer:           SmartCustomsGate (Benson) - Decision Engine

DECISION MATRIX:
  ┌─────────────┬─────────────┬────────────┐
  │ DOCS (Law)  │ ROUTE (AI)  │ DECISION   │
  ├─────────────┼─────────────┼────────────┤
  │ ❌ FAIL     │ (any)       │ REJECT     │
  │ ✅ PASS     │ ❌ FAIL     │ HOLD       │  ← TROJAN HORSE CATCH
  │ ✅ PASS     │ ✅ PASS     │ RELEASE    │
  └─────────────┴─────────────┴────────────┘

INVARIANT:
  ROUTE_INTEGRITY: A valid shipment implies a valid journey.
  
CONSTRAINT:
  MUST prioritize Physical Law for Rejection.
  MUST NOT auto-reject on AI suspicion alone (HOLD only).

TRAINING SIGNAL:
  "The map is not the territory. The paperwork is not the cargo. Trust the behavior."
"""

import json
import logging
from enum import Enum
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

# Setup Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [SMART_CUSTOMS] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmartCustoms")


class GateDecision(Enum):
    """Smart Customs Gate Decision States"""
    RELEASE = "RELEASE"  # All checks passed - proceed to destination
    HOLD = "HOLD"        # Behavioral anomaly detected - manual inspection required
    REJECT = "REJECT"    # Document/physical failure - deny entry


class DocumentValidator:
    """
    Layer 1: The Law (Physical/Paperwork)
    Managed by: Atlas (GID-11)
    
    Validates the legal and physical aspects of a shipment:
    - Seal integrity
    - Weight variance
    - Document completeness
    """
    
    def __init__(self):
        self.agent_id = "GID-11"
        self.agent_name = "Atlas"
        self.weight_tolerance = 0.05  # 5% variance allowed
        
    def validate(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate shipment documentation and physical state.
        
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        shipment_id = manifest.get("shipment_id", "UNKNOWN")
        logger.info(f"[ATLAS] Validating documents for {shipment_id}")
        
        # 1. Check Seal Integrity
        if not manifest.get("seal_intact", False):
            logger.warning(f"[ATLAS] SEAL BROKEN on {shipment_id}")
            return False, "SEAL_BROKEN"
        
        # 2. Check Weight Variance (Tolerance 5%)
        declared = manifest.get("declared_weight_kg", 0)
        actual = manifest.get("actual_weight_kg", 0)
        
        if declared == 0:
            logger.warning(f"[ATLAS] Invalid weight declaration on {shipment_id}")
            return False, "INVALID_WEIGHT_DECLARED"
        
        variance = abs(declared - actual) / declared
        if variance > self.weight_tolerance:
            logger.warning(f"[ATLAS] Weight variance {variance:.2%} exceeds {self.weight_tolerance:.0%} on {shipment_id}")
            return False, f"WEIGHT_VARIANCE_EXCEEDS_LIMIT ({variance:.2%})"
        
        # 3. Check Required Documents
        required_docs = ["bill_of_lading", "commercial_invoice", "packing_list"]
        missing_docs = [doc for doc in required_docs if not manifest.get(doc, True)]
        if missing_docs:
            logger.warning(f"[ATLAS] Missing documents on {shipment_id}: {missing_docs}")
            return False, f"MISSING_DOCUMENTS: {', '.join(missing_docs)}"
            
        logger.info(f"[ATLAS] Documents VALID for {shipment_id}")
        return True, "DOCS_VALID"


class RouteSentinel:
    """
    Layer 2: The Intelligence (Behavioral)
    Managed by: Eve (GID-01)
    
    Analyzes the behavioral patterns of a shipment:
    - Route deviation
    - Unscheduled stops
    - Time window compliance
    """
    
    def __init__(self):
        self.agent_id = "GID-01"
        self.agent_name = "Eve"
        self.deviation_threshold_km = 5.0
        self.delay_threshold_min = 30
        
    def analyze(self, telemetry: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Analyze route telemetry for behavioral anomalies.
        
        Returns:
            Tuple[bool, str]: (is_normal, reason)
        """
        shipment_id = telemetry.get("shipment_id", "UNKNOWN")
        logger.info(f"[EVE] Analyzing route behavior for {shipment_id}")
        
        # 1. Check Route Deviation
        deviation = telemetry.get("route_deviation_km", 0)
        if deviation > self.deviation_threshold_km:
            logger.warning(f"[EVE] Route deviation {deviation}km exceeds threshold on {shipment_id}")
            return False, f"SIGNIFICANT_ROUTE_DEVIATION ({deviation}km)"
        
        # 2. Check Unscheduled Stops
        unscheduled_stops = telemetry.get("unscheduled_stops", 0)
        if unscheduled_stops > 0:
            stop_locations = telemetry.get("stop_locations", ["UNKNOWN"])
            logger.warning(f"[EVE] {unscheduled_stops} unscheduled stop(s) detected on {shipment_id}")
            return False, f"UNSCHEDULED_STOP_DETECTED ({unscheduled_stops} stops)"
            
        # 3. Check Time Window Compliance
        delay = telemetry.get("arrival_delay_min", 0)
        if delay > self.delay_threshold_min:
            logger.warning(f"[EVE] Arrival delay {delay}min exceeds threshold on {shipment_id}")
            return False, f"ARRIVAL_DELAY_EXCEEDS_THRESHOLD ({delay}min)"
        
        # 4. Check GPS Integrity (if available)
        if telemetry.get("gps_gaps", 0) > 0:
            gap_duration = telemetry.get("gps_gap_duration_min", 0)
            if gap_duration > 10:
                logger.warning(f"[EVE] GPS signal gap of {gap_duration}min detected on {shipment_id}")
                return False, f"GPS_SIGNAL_GAP ({gap_duration}min)"
            
        logger.info(f"[EVE] Route behavior NORMAL for {shipment_id}")
        return True, "ROUTE_NORMAL"


class SmartCustomsGate:
    """
    Fusion Layer - The Decision Engine
    Managed by: Benson (GID-00)
    
    Fuses document validation with behavioral intelligence to make
    final customs decisions. Implements the "Trojan Horse" detection
    pattern where valid documents + suspicious behavior = HOLD.
    """
    
    def __init__(self):
        self.agent_id = "GID-00"
        self.agent_name = "Benson"
        self.doc_validator = DocumentValidator()
        self.sentinel = RouteSentinel()
        self.decisions_made = 0
        
    def process(self, manifest: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a shipment through the Smart Customs Fusion Gate.
        
        Args:
            manifest: Document/physical data from DocumentValidator
            telemetry: Behavioral data from RouteSentinel
            
        Returns:
            Dict containing decision and full reasoning
        """
        shipment_id = manifest.get("shipment_id", "UNKNOWN")
        logger.info(f"[BENSON] ═══════════════════════════════════════════════")
        logger.info(f"[BENSON] Processing Shipment: {shipment_id}")
        logger.info(f"[BENSON] ═══════════════════════════════════════════════")
        
        # Layer 1: Law (Physical/Documents)
        docs_ok, docs_reason = self.doc_validator.validate(manifest)
        
        # Layer 2: Intelligence (Behavioral)
        telemetry["shipment_id"] = shipment_id  # Pass through for logging
        route_ok, route_reason = self.sentinel.analyze(telemetry)
        
        # Fusion Decision Logic
        decision = GateDecision.REJECT
        final_reason = ""

        if not docs_ok:
            # Physical/Legal failure = REJECT (hard stop)
            decision = GateDecision.REJECT
            final_reason = f"DOCUMENT_FAILURE: {docs_reason}"
            logger.error(f"[BENSON] ❌ REJECT - {final_reason}")
            
        elif docs_ok and not route_ok:
            # THE FUSION CATCH: Valid Docs + Bad Behavior = HOLD
            # This is the "Trojan Horse" scenario
            decision = GateDecision.HOLD
            final_reason = f"BEHAVIORAL_ANOMALY: {route_reason} (Trojan Horse Scenario)"
            logger.warning(f"[BENSON] ⚠️  HOLD - {final_reason}")
            
        else:
            # All checks passed = RELEASE
            decision = GateDecision.RELEASE
            final_reason = "ALL_CHECKS_PASSED"
            logger.info(f"[BENSON] ✅ RELEASE - {final_reason}")

        self.decisions_made += 1
        
        result = {
            "shipment_id": shipment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision.value,
            "reason": final_reason,
            "requires_inspection": decision == GateDecision.HOLD,
            "layers": {
                "law": {
                    "agent": f"{self.doc_validator.agent_name} ({self.doc_validator.agent_id})",
                    "status": "PASS" if docs_ok else "FAIL",
                    "detail": docs_reason
                },
                "sentinel": {
                    "agent": f"{self.sentinel.agent_name} ({self.sentinel.agent_id})",
                    "status": "PASS" if route_ok else "FAIL",
                    "detail": route_reason
                }
            },
            "fusion_agent": f"{self.agent_name} ({self.agent_id})",
            "decision_number": self.decisions_made
        }
        
        logger.info(f"[BENSON] Decision #{self.decisions_made}: {decision.value} | {final_reason}")
        return result


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATION FOR P75 VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def run_simulation():
    """
    Run the P75 validation simulation demonstrating the Trojan Horse catch.
    """
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║        SMART CUSTOMS FUSION GATE - P75 VALIDATION                    ║")
    print("║              \"Catching the Trojan Horse\"                             ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    gate = SmartCustomsGate()
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 1: CLEAN SHIPMENT (Should RELEASE)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*70)
    print("SCENARIO 1: CLEAN SHIPMENT")
    print("="*70)
    
    manifest_1 = {
        "shipment_id": "SHP-001-CLEAN",
        "seal_intact": True,
        "declared_weight_kg": 1000,
        "actual_weight_kg": 1010,  # 1% variance (OK)
        "bill_of_lading": True,
        "commercial_invoice": True,
        "packing_list": True
    }
    
    telemetry_1 = {
        "route_deviation_km": 0.5,
        "unscheduled_stops": 0,
        "arrival_delay_min": 10,
        "gps_gaps": 0
    }
    
    result_1 = gate.process(manifest_1, telemetry_1)
    print(f"\n📋 Result: {json.dumps(result_1, indent=2)}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 2: TROJAN HORSE (Valid Docs, Bad Route) - Should HOLD
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*70)
    print("SCENARIO 2: TROJAN HORSE (Perfect Papers, Suspicious Behavior)")
    print("="*70)
    
    manifest_2 = {
        "shipment_id": "SHP-999-TROJAN",
        "seal_intact": True,
        "declared_weight_kg": 1000,
        "actual_weight_kg": 1020,  # 2% variance (OK)
        "bill_of_lading": True,
        "commercial_invoice": True,
        "packing_list": True
    }
    
    telemetry_2 = {
        "route_deviation_km": 0.5,
        "unscheduled_stops": 1,  # ⚠️ STOP DETECTED
        "stop_locations": ["Unknown Warehouse - Industrial District"],
        "arrival_delay_min": 45,  # ⚠️ LATE
        "gps_gaps": 0
    }
    
    result_2 = gate.process(manifest_2, telemetry_2)
    print(f"\n📋 Result: {json.dumps(result_2, indent=2)}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 3: DOCUMENT FAILURE (Should REJECT)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*70)
    print("SCENARIO 3: DOCUMENT FAILURE (Broken Seal)")
    print("="*70)
    
    manifest_3 = {
        "shipment_id": "SHP-666-BROKEN",
        "seal_intact": False,  # ❌ SEAL BROKEN
        "declared_weight_kg": 1000,
        "actual_weight_kg": 1000,
        "bill_of_lading": True,
        "commercial_invoice": True,
        "packing_list": True
    }
    
    telemetry_3 = {
        "route_deviation_km": 0.0,
        "unscheduled_stops": 0,
        "arrival_delay_min": 0,
        "gps_gaps": 0
    }
    
    result_3 = gate.process(manifest_3, telemetry_3)
    print(f"\n📋 Result: {json.dumps(result_3, indent=2)}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*70)
    print("SIMULATION SUMMARY")
    print("="*70)
    
    print(f"""
    ┌────────────────────┬─────────────┬─────────────┬────────────┐
    │ Shipment           │ Docs (Law)  │ Route (AI)  │ Decision   │
    ├────────────────────┼─────────────┼─────────────┼────────────┤
    │ SHP-001-CLEAN      │ ✅ PASS     │ ✅ PASS     │ ✅ RELEASE │
    │ SHP-999-TROJAN     │ ✅ PASS     │ ❌ FAIL     │ ⚠️  HOLD   │
    │ SHP-666-BROKEN     │ ❌ FAIL     │ ✅ PASS     │ ❌ REJECT  │
    └────────────────────┴─────────────┴─────────────┴────────────┘
    """)
    
    # Validate expected outcomes
    assert result_1["decision"] == "RELEASE", "Scenario 1 should RELEASE"
    assert result_2["decision"] == "HOLD", "Scenario 2 should HOLD (Trojan Horse)"
    assert result_3["decision"] == "REJECT", "Scenario 3 should REJECT"
    
    print("✅ ALL SCENARIOS VALIDATED - FUSION GATE OPERATIONAL")
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║  BENSON [GID-00]: \"The Gate is fused. The Trojan Horse is caught.\"   ║")
    print("║  ATTESTATION: P75_FUSION_GATE_ACTIVE                                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    return {
        "scenarios_run": 3,
        "scenarios_passed": 3,
        "trojan_horse_caught": result_2["decision"] == "HOLD",
        "attestation": "P75_FUSION_GATE_ACTIVE"
    }


if __name__ == "__main__":
    run_simulation()
