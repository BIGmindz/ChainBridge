"""
Document Retry Remediation Strategy
====================================

PAC-SYS-P163-DOCUMENT-RETRY-STRATEGY: The User Coach.

This strategy handles document and biometric quality failures - cases where
the user's submission failed not because of fraud, but because of technical
issues that can be fixed with guidance.

Instead of a hard rejection ("Transaction Failed"), the system provides
specific, actionable instructions ("Your photo was blurry, please hold
the camera steady and ensure good lighting").

Governance Model:
    - IF Error is User-Fixable (Blur, Glare, Wrong File) → REQUEST_RETRY with SPECIFIC_INSTRUCTION
    - IF Error is Fatal (Forged, Stolen, Deepfake) → REJECT (no coaching)

Invariants:
    - INV-IMMUNE-003: Constructive Feedback - error messages must be actionable
    - Max 3 retries per document type
    - Never reveal fraud detection vectors

Author: Benson (GID-00)
Classification: IMMUNE_STRATEGY_IMPLEMENTATION
Attestation: MASTER-BER-P163-STRATEGY
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import time

from ..remediator import (
    RemediationStrategy,
    RemediationResult,
    EscalationLevel,
)


class RetryCategory(Enum):
    """Categories of retry-able issues."""
    QUALITY = "quality"           # Image quality issues (blur, glare, dark)
    FORMAT = "format"             # Wrong file type, size, resolution
    CONTENT = "content"           # Missing info, wrong document type
    BIOMETRIC = "biometric"       # Liveness, face match issues
    EXPIRED = "expired"           # Document expiration
    FATAL = "fatal"               # Fraud indicators (no retry)


@dataclass
class RetryInstruction:
    """User-facing retry instruction."""
    category: RetryCategory
    technical_code: str
    user_message: str
    action_required: str
    tips: List[str] = field(default_factory=list)
    max_retries: int = 3
    is_fatal: bool = False


class DocumentRetryStrategy(RemediationStrategy):
    """
    Strategy for coaching users through document/biometric failures.
    
    This strategy transforms technical error codes into human-readable,
    actionable guidance. It maintains retry context to prevent infinite
    loops and distinguishes between fixable issues and fraud indicators.
    
    Error Categories:
        - QUALITY: Blur, glare, darkness, reflection
        - FORMAT: Wrong file type, too small, wrong dimensions
        - CONTENT: Wrong document, missing fields, obscured text
        - BIOMETRIC: Liveness failure, face mismatch (user-fixable)
        - FATAL: Forgery, tampering, stolen identity (no retry)
    """
    
    # Technical code to user instruction mapping
    ERROR_MAP: Dict[str, RetryInstruction] = {
        # === QUALITY ISSUES ===
        "DOC_BLURRY": RetryInstruction(
            category=RetryCategory.QUALITY,
            technical_code="DOC_BLURRY",
            user_message="Your document photo appears blurry.",
            action_required="Please retake the photo",
            tips=[
                "Hold your device steady",
                "Ensure good lighting",
                "Clean your camera lens",
                "Place document on a flat surface"
            ]
        ),
        "DOC_GLARE": RetryInstruction(
            category=RetryCategory.QUALITY,
            technical_code="DOC_GLARE",
            user_message="There is glare or reflection on your document.",
            action_required="Please retake without direct light on the document",
            tips=[
                "Avoid overhead lights directly above",
                "Turn off the camera flash",
                "Tilt the document slightly to reduce reflection"
            ]
        ),
        "DOC_DARK": RetryInstruction(
            category=RetryCategory.QUALITY,
            technical_code="DOC_DARK",
            user_message="Your document photo is too dark.",
            action_required="Please retake in a well-lit area",
            tips=[
                "Move to natural light or brighter area",
                "Ensure the document is fully visible"
            ]
        ),
        "DOC_CROPPED": RetryInstruction(
            category=RetryCategory.QUALITY,
            technical_code="DOC_CROPPED",
            user_message="Parts of your document are cut off.",
            action_required="Please ensure the entire document is visible",
            tips=[
                "Include all four corners",
                "Leave a small margin around the edges",
                "Don't crop the image"
            ]
        ),
        
        # === FORMAT ISSUES ===
        "WRONG_FILE_TYPE": RetryInstruction(
            category=RetryCategory.FORMAT,
            technical_code="WRONG_FILE_TYPE",
            user_message="The file format is not supported.",
            action_required="Please upload a JPG, PNG, or PDF file",
            tips=[
                "Convert your file to a supported format",
                "Take a new photo directly from your camera"
            ]
        ),
        "FILE_TOO_SMALL": RetryInstruction(
            category=RetryCategory.FORMAT,
            technical_code="FILE_TOO_SMALL",
            user_message="The image resolution is too low.",
            action_required="Please upload a higher quality image",
            tips=[
                "Use your device's highest camera resolution",
                "Avoid screenshots of documents"
            ]
        ),
        "FILE_TOO_LARGE": RetryInstruction(
            category=RetryCategory.FORMAT,
            technical_code="FILE_TOO_LARGE",
            user_message="The file is too large.",
            action_required="Please upload a smaller file (max 10MB)",
            tips=[
                "Compress the image",
                "Take a new photo at lower resolution"
            ]
        ),
        
        # === CONTENT ISSUES ===
        "WRONG_DOCUMENT": RetryInstruction(
            category=RetryCategory.CONTENT,
            technical_code="WRONG_DOCUMENT",
            user_message="This is not the requested document type.",
            action_required="Please upload the correct document",
            tips=[
                "Check which document is being requested",
                "Ensure you're uploading a passport, ID card, or driver's license as required"
            ]
        ),
        "TEXT_OBSCURED": RetryInstruction(
            category=RetryCategory.CONTENT,
            technical_code="TEXT_OBSCURED",
            user_message="Some text on your document is not readable.",
            action_required="Please ensure all text is clearly visible",
            tips=[
                "Remove any objects covering the document",
                "Don't hold the document with fingers over text"
            ]
        ),
        "MRZ_UNREADABLE": RetryInstruction(
            category=RetryCategory.CONTENT,
            technical_code="MRZ_UNREADABLE",
            user_message="The machine-readable zone could not be scanned.",
            action_required="Please retake focusing on the bottom of the document",
            tips=[
                "Ensure the two lines of code at the bottom are clear",
                "Avoid shadows on the MRZ zone"
            ]
        ),
        
        # === BIOMETRIC ISSUES ===
        "LIVENESS_FAILED": RetryInstruction(
            category=RetryCategory.BIOMETRIC,
            technical_code="LIVENESS_FAILED",
            user_message="We couldn't verify your live presence.",
            action_required="Please try the face verification again",
            tips=[
                "Ensure your face is well-lit and centered",
                "Follow the on-screen instructions carefully",
                "Remove sunglasses and hats",
                "Look directly at the camera"
            ]
        ),
        "FACE_NOT_DETECTED": RetryInstruction(
            category=RetryCategory.BIOMETRIC,
            technical_code="FACE_NOT_DETECTED",
            user_message="We couldn't detect a face in the image.",
            action_required="Please ensure your face is clearly visible",
            tips=[
                "Position yourself in the center of the frame",
                "Ensure adequate lighting on your face",
                "Remove any face coverings"
            ]
        ),
        "FACE_MISMATCH": RetryInstruction(
            category=RetryCategory.BIOMETRIC,
            technical_code="FACE_MISMATCH",
            user_message="The face doesn't match the document photo.",
            action_required="Please try again with clearer images",
            tips=[
                "Ensure you're using your own valid document",
                "Retake both the selfie and document photo",
                "Use similar lighting for both photos"
            ],
            max_retries=2  # Fewer retries for potential fraud
        ),
        
        # === EXPIRATION ISSUES ===
        "DOC_EXPIRED": RetryInstruction(
            category=RetryCategory.EXPIRED,
            technical_code="DOC_EXPIRED",
            user_message="Your document has expired.",
            action_required="Please provide a valid, non-expired document",
            tips=[
                "Check the expiration date on your document",
                "Use an alternative unexpired ID if available"
            ],
            max_retries=1  # User needs different document
        ),
        
        # === FATAL ISSUES (No Retry) ===
        "DOC_TAMPERED": RetryInstruction(
            category=RetryCategory.FATAL,
            technical_code="DOC_TAMPERED",
            user_message="Document verification failed.",
            action_required="Please contact support",
            tips=[],
            is_fatal=True
        ),
        "DOC_FORGED": RetryInstruction(
            category=RetryCategory.FATAL,
            technical_code="DOC_FORGED",
            user_message="Document verification failed.",
            action_required="Please contact support",
            tips=[],
            is_fatal=True
        ),
        "IDENTITY_STOLEN": RetryInstruction(
            category=RetryCategory.FATAL,
            technical_code="IDENTITY_STOLEN",
            user_message="Verification could not be completed.",
            action_required="Please contact support",
            tips=[],
            is_fatal=True
        ),
        "DEEPFAKE_DETECTED": RetryInstruction(
            category=RetryCategory.FATAL,
            technical_code="DEEPFAKE_DETECTED",
            user_message="Liveness check failed.",  # Never reveal deepfake detection
            action_required="Please contact support",
            tips=[],
            is_fatal=True
        ),
    }
    
    # Default instruction for unknown codes
    DEFAULT_INSTRUCTION = RetryInstruction(
        category=RetryCategory.QUALITY,
        technical_code="UNKNOWN",
        user_message="Document verification encountered an issue.",
        action_required="Please try uploading your document again",
        tips=[
            "Use a well-lit area",
            "Ensure the document is clear and complete"
        ]
    )
    
    def __init__(self):
        """Initialize with retry tracking."""
        self._retry_counts: Dict[str, Dict[str, int]] = {}  # tx_id -> {doc_type: count}
    
    @property
    def strategy_id(self) -> str:
        return "document_retry_strategy"
    
    @property
    def handles_gates(self) -> List[str]:
        return ["biometric", "validation"]
    
    @property
    def handles_errors(self) -> List[str]:
        return [
            "DOC_QUALITY_ERROR",
            "DOCUMENT_ERROR",
            "BIOMETRIC_ERROR",
            "LIVENESS_FAILURE",
        ] + list(self.ERROR_MAP.keys())
    
    def can_handle(self, gate: str, error_code: str, context: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the error."""
        # Direct code match
        if error_code in self.ERROR_MAP:
            return True
        
        # Pattern matching
        error_upper = error_code.upper()
        doc_indicators = ["DOC_", "DOCUMENT", "BIOMETRIC", "LIVENESS", "FACE_", "MRZ", "FILE_"]
        return any(ind in error_upper for ind in doc_indicators)
    
    def estimate_success(self, gate: str, error_code: str, context: Dict[str, Any]) -> float:
        """Estimate success probability."""
        instruction = self._get_instruction(error_code)
        
        if instruction.is_fatal:
            return 0.0  # Cannot remediate fraud
        
        # Check retry count
        tx_id = context.get("transaction_id", "unknown")
        doc_type = context.get("document_type", "default")
        current_retries = self._get_retry_count(tx_id, doc_type)
        
        if current_retries >= instruction.max_retries:
            return 0.1  # Too many retries
        
        # Success likelihood by category
        category_success = {
            RetryCategory.QUALITY: 0.85,    # Usually fixable
            RetryCategory.FORMAT: 0.90,     # Very fixable
            RetryCategory.CONTENT: 0.70,    # Might need different doc
            RetryCategory.BIOMETRIC: 0.60,  # Harder to fix
            RetryCategory.EXPIRED: 0.40,    # Needs different document
        }
        
        return category_success.get(instruction.category, 0.5)
    
    def execute(self, original_data: Dict[str, Any], context: Dict[str, Any]) -> RemediationResult:
        """
        Generate user-friendly retry instructions.
        
        This doesn't "fix" the data - it generates a structured request
        for the user to provide corrected input.
        """
        start_time = time.time()
        
        # Get error code from context
        error_code = context.get("error_code", "")
        if not error_code:
            blame = context.get("blame", {})
            error_code = blame.get("code", "UNKNOWN")
        
        # Get instruction
        instruction = self._get_instruction(error_code)
        
        # Check for fatal errors
        if instruction.is_fatal:
            return RemediationResult(
                success=False,
                strategy_used=self.strategy_id,
                original_error=error_code,
                explanation=f"{instruction.user_message} {instruction.action_required}",
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Check retry limits
        tx_id = context.get("transaction_id", original_data.get("transaction_id", "unknown"))
        doc_type = context.get("document_type", "default")
        current_retries = self._get_retry_count(tx_id, doc_type)
        
        if current_retries >= instruction.max_retries:
            return RemediationResult(
                success=False,
                strategy_used=self.strategy_id,
                original_error=error_code,
                explanation=f"Maximum retry attempts ({instruction.max_retries}) reached for this document. Please contact support.",
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Increment retry count
        self._increment_retry(tx_id, doc_type)
        
        # Build retry guidance
        retry_guidance = {
            "retry_allowed": True,
            "retry_number": current_retries + 1,
            "max_retries": instruction.max_retries,
            "category": instruction.category.value,
            "user_message": instruction.user_message,
            "action_required": instruction.action_required,
            "tips": instruction.tips,
            "original_transaction_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Build human-readable explanation
        explanation = f"{instruction.user_message}\n\n"
        explanation += f"**Action Required:** {instruction.action_required}\n\n"
        if instruction.tips:
            explanation += "**Tips:**\n"
            for tip in instruction.tips:
                explanation += f"  • {tip}\n"
        explanation += f"\n(Attempt {current_retries + 1} of {instruction.max_retries})"
        
        return RemediationResult(
            success=True,  # Successfully generated guidance
            strategy_used=self.strategy_id,
            original_error=error_code,
            corrected_data={"retry_guidance": retry_guidance},
            explanation=explanation,
            confidence=0.8,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _get_instruction(self, error_code: str) -> RetryInstruction:
        """Get retry instruction for error code."""
        return self.ERROR_MAP.get(error_code.upper(), self.DEFAULT_INSTRUCTION)
    
    def _get_retry_count(self, tx_id: str, doc_type: str) -> int:
        """Get current retry count for transaction/document."""
        if tx_id not in self._retry_counts:
            return 0
        return self._retry_counts[tx_id].get(doc_type, 0)
    
    def _increment_retry(self, tx_id: str, doc_type: str) -> None:
        """Increment retry count."""
        if tx_id not in self._retry_counts:
            self._retry_counts[tx_id] = {}
        current = self._retry_counts[tx_id].get(doc_type, 0)
        self._retry_counts[tx_id][doc_type] = current + 1
    
    def reset_retries(self, tx_id: str) -> None:
        """Reset retry counts for a transaction (e.g., after success)."""
        if tx_id in self._retry_counts:
            del self._retry_counts[tx_id]
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        total_active = sum(
            sum(counts.values()) 
            for counts in self._retry_counts.values()
        )
        return {
            "active_transactions": len(self._retry_counts),
            "total_retries": total_active,
            "error_codes_mapped": len(self.ERROR_MAP)
        }


# =============================================================================
# STRATEGY DEPLOYMENT COMPLETE
# =============================================================================
#
# DocumentRetryStrategy is now available:
#
#     from modules.immune.strategies import DocumentRetryStrategy
#     engine.register_strategy(DocumentRetryStrategy())
#
# Error Mappings:
#   - DOC_BLURRY → "Please retake in better light"
#   - DOC_GLARE → "Avoid direct light on document"
#   - LIVENESS_FAILED → "Try face verification again"
#   - DOC_FORGED → REJECT (no coaching for fraud)
#
# Attestation: MASTER-BER-P163-STRATEGY
# Ledger: ATTEST: DOCUMENT_RETRY_ACTIVE
# =============================================================================
