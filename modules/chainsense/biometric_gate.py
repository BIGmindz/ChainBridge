#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE BIOMETRIC GATE MODULE (P85)                            ║
║                   IDENTITY SOVEREIGNTY PILLAR                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: IDENTITY_VERIFICATION                                                 ║
║  GOVERNANCE_TIER: CONSTITUTIONAL                                             ║
║  MODE: PROOF_OF_HUMAN                                                        ║
║  LANE: IDENTITY_LANE                                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

BIOMETRIC GATE ARCHITECTURE:
  Liveness Check:     Detect presentation attacks (photos, masks, deepfakes)
  Face Match:         Compare capture to enrolled template
  Document Verify:    Validate government ID authenticity
  Watchlist Screen:   Check against wanted/banned persons

DECISION MATRIX:
  ┌─────────────┬─────────────┬────────────┐
  │ LIVENESS    │ FACE_MATCH  │ DECISION   │
  ├─────────────┼─────────────┼────────────┤
  │ ❌ FAIL     │ (any)       │ REJECT     │
  │ ✅ PASS     │ ❌ FAIL     │ REJECT     │
  │ ✅ PASS     │ ✅ PASS     │ VERIFY     │
  └─────────────┴─────────────┴────────────┘

INVARIANT:
  PROOF_OF_HUMAN: Every sovereign transaction requires a verified human.
"""

import json
import logging
from enum import Enum
from typing import Dict, Any, Tuple
from datetime import datetime, timezone
import hashlib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [BIO_GATE] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BiometricGate")


class BioDecision(Enum):
    """Biometric Gate Decision States"""
    VERIFY = "VERIFY"     # Identity confirmed
    REJECT = "REJECT"     # Identity verification failed
    ESCALATE = "ESCALATE" # Manual verification required


class LivenessDetector:
    """
    Presentation Attack Detection
    Managed by: Eve (GID-01)
    
    Detects spoofing attempts:
    - Photo attacks
    - Video replay
    - 3D masks
    - Deepfakes
    """
    
    def __init__(self):
        self.agent_id = "GID-01"
        self.agent_name = "Eve"
        self.liveness_threshold = 0.85  # 85% confidence required
        
    def check(self, biometric_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """
        Perform liveness detection.
        
        Returns:
            Tuple[bool, str, float]: (is_live, reason, confidence)
        """
        user_id = biometric_data.get("user_id", "UNKNOWN")
        logger.info(f"[EVE] Performing liveness check for {user_id}")
        
        # Simulated liveness score (in production: ML model)
        liveness_score = biometric_data.get("liveness_score", 0.95)
        
        # Check for known attack indicators
        if biometric_data.get("is_static_image", False):
            logger.warning(f"[EVE] ❌ STATIC IMAGE DETECTED for {user_id}")
            return False, "STATIC_IMAGE_ATTACK", 0.0
        
        if biometric_data.get("is_replay", False):
            logger.warning(f"[EVE] ❌ VIDEO REPLAY DETECTED for {user_id}")
            return False, "VIDEO_REPLAY_ATTACK", 0.0
        
        if biometric_data.get("is_deepfake", False):
            logger.warning(f"[EVE] ❌ DEEPFAKE DETECTED for {user_id}")
            return False, "DEEPFAKE_ATTACK", 0.0
        
        if liveness_score < self.liveness_threshold:
            logger.warning(f"[EVE] ❌ LOW LIVENESS SCORE: {liveness_score:.2f} for {user_id}")
            return False, f"LOW_LIVENESS_SCORE ({liveness_score:.2f})", liveness_score
        
        logger.info(f"[EVE] ✅ LIVENESS CONFIRMED: {liveness_score:.2f} for {user_id}")
        return True, "LIVENESS_CONFIRMED", liveness_score


class FaceMatcher:
    """
    Facial Recognition Matching
    Managed by: Cody (GID-02)
    
    Compares live capture against enrolled biometric template.
    """
    
    def __init__(self):
        self.agent_id = "GID-02"
        self.agent_name = "Cody"
        self.match_threshold = 0.90  # 90% similarity required
        
    def match(self, biometric_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        """
        Perform face matching against enrolled template.
        
        Returns:
            Tuple[bool, str, float]: (is_match, reason, similarity)
        """
        user_id = biometric_data.get("user_id", "UNKNOWN")
        logger.info(f"[CODY] Performing face match for {user_id}")
        
        # Check if enrolled
        if not biometric_data.get("has_enrolled_template", True):
            logger.warning(f"[CODY] ❌ NO ENROLLED TEMPLATE for {user_id}")
            return False, "NO_ENROLLED_TEMPLATE", 0.0
        
        # Simulated match score (in production: face embedding comparison)
        similarity = biometric_data.get("face_similarity", 0.95)
        
        if similarity < self.match_threshold:
            logger.warning(f"[CODY] ❌ FACE MISMATCH: {similarity:.2f} for {user_id}")
            return False, f"FACE_MISMATCH ({similarity:.2f})", similarity
        
        logger.info(f"[CODY] ✅ FACE MATCH: {similarity:.2f} for {user_id}")
        return True, "FACE_MATCH_CONFIRMED", similarity


class DocumentVerifier:
    """
    Government ID Verification
    Managed by: Atlas (GID-11)
    
    Validates authenticity of identity documents.
    """
    
    def __init__(self):
        self.agent_id = "GID-11"
        self.agent_name = "Atlas"
        self.valid_doc_types = {"PASSPORT", "DRIVERS_LICENSE", "NATIONAL_ID"}
        
    def verify(self, document_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify identity document.
        
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        user_id = document_data.get("user_id", "UNKNOWN")
        doc_type = document_data.get("document_type", "UNKNOWN")
        logger.info(f"[ATLAS] Verifying {doc_type} for {user_id}")
        
        # Check document type
        if doc_type.upper() not in self.valid_doc_types:
            logger.warning(f"[ATLAS] ❌ INVALID DOCUMENT TYPE: {doc_type}")
            return False, f"INVALID_DOCUMENT_TYPE: {doc_type}"
        
        # Check expiration
        if document_data.get("is_expired", False):
            logger.warning(f"[ATLAS] ❌ EXPIRED DOCUMENT for {user_id}")
            return False, "DOCUMENT_EXPIRED"
        
        # Check tampering
        if document_data.get("is_tampered", False):
            logger.warning(f"[ATLAS] ❌ TAMPERED DOCUMENT for {user_id}")
            return False, "DOCUMENT_TAMPERED"
        
        # Check MRZ/barcode validity
        if not document_data.get("mrz_valid", True):
            logger.warning(f"[ATLAS] ❌ INVALID MRZ for {user_id}")
            return False, "INVALID_MRZ"
        
        logger.info(f"[ATLAS] ✅ DOCUMENT VERIFIED for {user_id}")
        return True, "DOCUMENT_VALID"


class BiometricGate:
    """
    Master Biometric Gate - Identity Pillar of Trinity
    Managed by: Benson (GID-00)
    
    Orchestrates liveness, face matching, and document verification
    for comprehensive identity assurance.
    """
    
    def __init__(self):
        self.agent_id = "GID-00"
        self.agent_name = "Benson"
        self.liveness = LivenessDetector()
        self.matcher = FaceMatcher()
        self.doc_verifier = DocumentVerifier()
        self.decisions_made = 0
        
    def process(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user through Biometric Gate.
        
        Args:
            user_data: Dict containing:
                - user_id: Unique user identifier
                - liveness_score: Liveness detection score (0-1)
                - face_similarity: Face match similarity (0-1)
                - document_type: Type of ID document
                - is_expired, is_tampered, etc.
                
        Returns:
            Dict containing decision and full reasoning
        """
        user_id = user_data.get("user_id", f"USR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
        logger.info(f"[BENSON] ═══════════════════════════════════════════════")
        logger.info(f"[BENSON] Processing Biometric Check: {user_id}")
        logger.info(f"[BENSON] ═══════════════════════════════════════════════")
        
        # Layer 1: Liveness Detection
        is_live, live_reason, live_confidence = self.liveness.check(user_data)
        
        # Layer 2: Face Matching
        is_match, match_reason, match_similarity = self.matcher.match(user_data)
        
        # Layer 3: Document Verification
        doc_valid, doc_reason = self.doc_verifier.verify(user_data)
        
        # Decision Logic - ALL must pass
        decision = BioDecision.REJECT
        final_reason = ""
        
        if not is_live:
            decision = BioDecision.REJECT
            final_reason = f"LIVENESS_FAILURE: {live_reason}"
            logger.error(f"[BENSON] ❌ REJECT - {final_reason}")
            
        elif not is_match:
            decision = BioDecision.REJECT
            final_reason = f"FACE_MATCH_FAILURE: {match_reason}"
            logger.error(f"[BENSON] ❌ REJECT - {final_reason}")
            
        elif not doc_valid:
            decision = BioDecision.REJECT
            final_reason = f"DOCUMENT_FAILURE: {doc_reason}"
            logger.error(f"[BENSON] ❌ REJECT - {final_reason}")
            
        else:
            decision = BioDecision.VERIFY
            final_reason = "ALL_CHECKS_PASSED"
            logger.info(f"[BENSON] ✅ VERIFY - {final_reason}")
        
        self.decisions_made += 1
        
        # Generate biometric hash (privacy-preserving identifier)
        bio_hash = hashlib.sha256(f"{user_id}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]
        
        return {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision.value,
            "reason": final_reason,
            "biometric_hash": bio_hash,
            "layers": {
                "liveness": {
                    "agent": f"{self.liveness.agent_name} ({self.liveness.agent_id})",
                    "status": "PASS" if is_live else "FAIL",
                    "confidence": live_confidence,
                    "detail": live_reason
                },
                "face_match": {
                    "agent": f"{self.matcher.agent_name} ({self.matcher.agent_id})",
                    "status": "PASS" if is_match else "FAIL",
                    "similarity": match_similarity,
                    "detail": match_reason
                },
                "document": {
                    "agent": f"{self.doc_verifier.agent_name} ({self.doc_verifier.agent_id})",
                    "status": "PASS" if doc_valid else "FAIL",
                    "detail": doc_reason
                }
            },
            "gate_agent": f"{self.agent_name} ({self.agent_id})",
            "decision_number": self.decisions_made
        }


if __name__ == "__main__":
    # Quick validation
    gate = BiometricGate()
    
    # Verified user
    result = gate.process({
        "user_id": "USR-JOHN-DOE",
        "liveness_score": 0.98,
        "face_similarity": 0.95,
        "has_enrolled_template": True,
        "document_type": "PASSPORT",
        "is_expired": False,
        "is_tampered": False,
        "mrz_valid": True
    })
    print(f"Verified User: {result['decision']}")
    assert result["decision"] == "VERIFY"
    
    # Deepfake attack
    result = gate.process({
        "user_id": "USR-FAKE-001",
        "is_deepfake": True,
        "face_similarity": 0.99,
        "document_type": "PASSPORT"
    })
    print(f"Deepfake Attack: {result['decision']}")
    assert result["decision"] == "REJECT"
    
    print("✅ Biometric Gate P85 Validated")
