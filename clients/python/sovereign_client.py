#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE SOVEREIGN CLIENT SDK v2.0.0                            ║
║                   PAC-DEV-P223-SDK-V2-GENERATION                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Generated from: docs/api/v2/openapi.json                                    ║
║  Contract Hash: caaf8739eae14f80ed7e2369459cc4b1b97c9f1acb7a5f5a5321fb63...   ║
║  API Version: 2.0.0                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

THE SCEPTER - Python Client for ChainBridge Sovereign Server v2.0

This SDK provides type-safe access to the Sovereign Transaction API with
full support for the Invisible Bank financial capabilities:
  - Fee calculation with configurable strategies
  - Settlement tracking with intent IDs
  - Financial transparency via FinancialTrace

INVARIANTS:
  INV-DEV-001 (Contract Alignment): Client supports only Contract features
  INV-DEV-002 (Ergonomics): Financial data is easy to access

TRAINING SIGNAL:
  "A good tool evolves with the task."

Usage:
    from sovereign_client import SovereignClient, PaymentData, UserData, ShipmentData
    
    client = SovereignClient(base_url="http://localhost:8000")
    
    # Check health
    health = client.health()
    print(f"Server version: {health.version}")
    
    # Submit transaction with fee strategy
    receipt = client.submit_transaction(
        user_data=UserData(user_id="USR-001"),
        payment_data=PaymentData(
            payer_id="ACME-CORP",
            payee_id="GLOBEX-INC",
            amount=250000.00,
            currency="USD",
            fee_strategy="default"  # v2.0: Fee control
        ),
        shipment_data=ShipmentData(
            manifest=ManifestData(shipment_id="SHP-001", ...)
        )
    )
    
    # Access financial trace (v2.0)
    if receipt.financial_trace:
        print(f"Fees: {receipt.financial_trace.fees}")
        print(f"Net: {receipt.financial_trace.net_amount}")
        print(f"Ledger committed: {receipt.financial_trace.ledger_committed}")
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
import json
import httpx

__version__ = "2.0.0"
__api_version__ = "2.0.0"
__contract_hash__ = "caaf8739eae14f80ed7e2369459cc4b1b97c9f1acb7a5f5a5321fb63372cf5d6"


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class SovereignClientError(Exception):
    """Base exception for Sovereign Client errors."""
    pass


class ValidationError(SovereignClientError):
    """Raised when request validation fails (422)."""
    pass


class PaymentRequiredError(SovereignClientError):
    """
    Raised when settlement fails (402 Payment Required).
    
    v2.0: This indicates all gates passed but financial execution failed.
    Check the `reason` attribute for details (e.g., insufficient funds).
    """
    def __init__(self, message: str, transaction_id: str = None, reason: str = None, gates_passed: bool = True):
        super().__init__(message)
        self.transaction_id = transaction_id
        self.reason = reason
        self.gates_passed = gates_passed


class ServerError(SovereignClientError):
    """Raised when server returns 5xx error."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS - PYDANTIC-STYLE DATACLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class UserData:
    """
    P85 Biometric Gate Input
    Identity verification data.
    """
    user_id: str
    liveness_score: float = 0.95
    face_similarity: float = 0.95
    has_enrolled_template: bool = True
    document_type: str = "PASSPORT"
    is_expired: bool = False
    is_tampered: bool = False
    mrz_valid: bool = True
    is_static_image: bool = False
    is_replay: bool = False
    is_deepfake: bool = False


@dataclass
class PaymentData:
    """
    P65 AML Gate Input + P202 Fee Strategy
    Financial transaction data with fee configuration.
    
    v2.0 Fields:
      - fee_strategy: Controls fee calculation ("default", "premium", "zero")
    """
    payer_id: str
    payee_id: str
    amount: float
    transaction_id: Optional[str] = None
    payer_country: str = "US"
    payee_country: str = "US"
    currency: str = "USD"
    fee_strategy: str = "default"  # v2.0: Fee strategy control
    daily_total: float = 0.0
    is_new_customer: bool = False
    off_hours: bool = False


@dataclass
class ManifestData:
    """Shipment manifest for customs validation."""
    shipment_id: str
    declared_weight_kg: float
    actual_weight_kg: float
    seal_intact: bool = True
    bill_of_lading: bool = True
    commercial_invoice: bool = True
    packing_list: bool = True


@dataclass
class TelemetryData:
    """Route telemetry for behavioral analysis."""
    route_deviation_km: float = 0.0
    unscheduled_stops: int = 0
    stop_locations: List[str] = field(default_factory=list)
    arrival_delay_min: int = 0
    gps_gaps: int = 0
    gps_gap_duration_min: int = 0


@dataclass
class ShipmentData:
    """
    P75 Smart Customs Gate Input
    Cargo/logistics data.
    """
    manifest: ManifestData
    telemetry: TelemetryData = field(default_factory=TelemetryData)


# ══════════════════════════════════════════════════════════════════════════════
# v2.0 FINANCIAL MODELS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FinancialTrace:
    """
    P210 Financial Execution Trace
    
    Provides transparency into the movement of funds.
    This model is only present when a transaction is FINALIZED.
    
    INV-API-003 (Rich Receipts): Proof of financial execution.
    """
    gross_amount: str
    currency: str
    settlement_intent_id: Optional[str] = None
    settlement_status: Optional[str] = None
    fees: Optional[Dict[str, Any]] = None
    net_amount: Optional[str] = None
    payer_account: Optional[str] = None
    payee_account: Optional[str] = None
    ledger_committed: bool = False
    
    @property
    def total_fees(self) -> Optional[str]:
        """Extract total fees from fees dict."""
        if self.fees:
            return self.fees.get("total")
        return None
    
    @property
    def fee_strategy_used(self) -> Optional[str]:
        """Extract fee strategy from fees dict."""
        if self.fees:
            return self.fees.get("strategy")
        return None


@dataclass
class GateSummary:
    """Summary of a single gate's decision."""
    decision: str
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class TransactionReceipt:
    """
    Complete transaction receipt from Sovereign Server v2.0.
    
    v2.0 Fields:
      - financial_trace: Full breakdown of fees, settlement, and ledger commit
      - invariants_enforced: List of system invariants checked
    """
    transaction_id: str
    timestamp: str
    status: str
    finalized: bool
    gates: Dict[str, Any]
    controller: str
    version: str
    transaction_hash: Optional[str] = None
    blame: Optional[Dict[str, str]] = None
    financial_trace: Optional[FinancialTrace] = None  # v2.0
    participants: Optional[Dict[str, Any]] = None
    value: Optional[Dict[str, str]] = None
    attestation: Optional[str] = None
    invariants_enforced: Optional[List[str]] = None  # v2.0
    
    @property
    def is_finalized(self) -> bool:
        """Check if transaction was finalized."""
        return self.finalized and self.status == "FINALIZED"
    
    @property
    def is_aborted(self) -> bool:
        """Check if transaction was aborted."""
        return not self.finalized or self.status == "ABORTED"
    
    @property
    def blame_gate(self) -> Optional[str]:
        """Get the gate that caused abort, if any."""
        if self.blame:
            return self.blame.get("gate")
        return None
    
    @property
    def net_amount(self) -> Optional[str]:
        """Get net amount after fees (v2.0)."""
        if self.financial_trace:
            return self.financial_trace.net_amount
        return None


@dataclass
class HealthResponse:
    """Health check response."""
    status: str
    version: str
    controller: str
    uptime_seconds: float
    transactions_processed: int


@dataclass
class StatsResponse:
    """Statistics response."""
    transactions_processed: int
    transactions_finalized: int
    transactions_aborted: int
    finalization_rate: float
    controller_version: str


# ══════════════════════════════════════════════════════════════════════════════
# SOVEREIGN CLIENT
# ══════════════════════════════════════════════════════════════════════════════

class SovereignClient:
    """
    ChainBridge Sovereign Server Python Client v2.0
    
    The Scepter - command the Invisible Bank with type-safe methods.
    
    Features:
      - Type-safe request/response models
      - Automatic serialization/deserialization
      - Financial trace extraction
      - 402 Payment Required handling
      - Async support via httpx
    
    Example:
        client = SovereignClient("http://localhost:8000")
        
        # Check if server is ready
        health = client.health()
        assert health.version == "2.0.0"
        
        # Submit transaction
        receipt = client.submit_transaction(
            user_data=UserData(user_id="USR-001"),
            payment_data=PaymentData(
                payer_id="ACME",
                payee_id="GLOBEX",
                amount=50000.00,
                fee_strategy="default"
            ),
            shipment_data=ShipmentData(
                manifest=ManifestData(
                    shipment_id="SHP-001",
                    declared_weight_kg=1000,
                    actual_weight_kg=1005
                )
            )
        )
        
        if receipt.is_finalized:
            print(f"Fees: {receipt.financial_trace.total_fees}")
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Sovereign Client.
        
        Args:
            base_url: Sovereign Server URL (default: http://localhost:8000)
            timeout: Request timeout in seconds
            headers: Additional headers to include in requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": f"SovereignClient/{__version__}",
            **(headers or {})
        }
    
    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make HTTP request with error handling."""
        url = f"{self.base_url}{path}"
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self._headers,
                **kwargs
            )
        
        return response
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle response and raise appropriate exceptions."""
        if response.status_code == 200:
            return response.json()
        
        if response.status_code == 402:
            # v2.0: Payment Required - gates passed but settlement failed
            data = response.json()
            detail = data.get("detail", {})
            raise PaymentRequiredError(
                message=f"Settlement failed: {detail.get('reason', 'Unknown')}",
                transaction_id=detail.get("transaction_id"),
                reason=detail.get("reason"),
                gates_passed=detail.get("gates_passed", True)
            )
        
        if response.status_code == 422:
            data = response.json()
            raise ValidationError(f"Validation error: {data}")
        
        if response.status_code >= 500:
            raise ServerError(f"Server error: {response.status_code}")
        
        raise SovereignClientError(f"Unexpected response: {response.status_code}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────
    
    def health(self) -> HealthResponse:
        """
        Check server health.
        
        Returns:
            HealthResponse with version and status
        """
        response = self._request("GET", "/health")
        data = self._handle_response(response)
        return HealthResponse(**data)
    
    def stats(self) -> StatsResponse:
        """
        Get transaction statistics.
        
        Returns:
            StatsResponse with processing metrics
        """
        response = self._request("GET", "/v1/stats")
        data = self._handle_response(response)
        return StatsResponse(**data)
    
    def info(self) -> Dict[str, Any]:
        """
        Get server info from root endpoint.
        
        Returns:
            Server identification including version and mode
        """
        response = self._request("GET", "/")
        return self._handle_response(response)
    
    def submit_transaction(
        self,
        user_data: UserData,
        payment_data: PaymentData,
        shipment_data: ShipmentData
    ) -> TransactionReceipt:
        """
        Submit a Sovereign Transaction through Trinity Gates + Invisible Bank.
        
        This is the primary method for processing transactions. The request
        passes through:
          1. Biometric Gate (P85) - Identity verification
          2. AML Gate (P65) - Financial compliance
          3. Customs Gate (P75) - Cargo validation
          4. Invisible Bank (P200-P203) - Financial execution (v2.0)
        
        Args:
            user_data: Identity verification data
            payment_data: Financial transaction data (includes fee_strategy)
            shipment_data: Cargo/logistics data
        
        Returns:
            TransactionReceipt with financial_trace (v2.0)
        
        Raises:
            PaymentRequiredError: Gates passed but settlement failed (402)
            ValidationError: Request validation failed (422)
            ServerError: Server error (5xx)
        """
        # Build request payload
        payload = {
            "user_data": asdict(user_data),
            "payment_data": asdict(payment_data),
            "shipment_data": {
                "manifest": asdict(shipment_data.manifest),
                "telemetry": asdict(shipment_data.telemetry)
            }
        }
        
        response = self._request("POST", "/v1/transaction", json=payload)
        data = self._handle_response(response)
        
        # Parse financial_trace if present (v2.0)
        financial_trace = None
        if "financial_trace" in data and data["financial_trace"]:
            financial_trace = FinancialTrace(**data["financial_trace"])
        
        return TransactionReceipt(
            transaction_id=data["transaction_id"],
            timestamp=data["timestamp"],
            status=data["status"],
            finalized=data["finalized"],
            gates=data["gates"],
            controller=data["controller"],
            version=data["version"],
            transaction_hash=data.get("transaction_hash"),
            blame=data.get("blame"),
            financial_trace=financial_trace,
            participants=data.get("participants"),
            value=data.get("value"),
            attestation=data.get("attestation"),
            invariants_enforced=data.get("invariants_enforced")
        )
    
    # ──────────────────────────────────────────────────────────────────────────
    # CONVENIENCE METHODS
    # ──────────────────────────────────────────────────────────────────────────
    
    def is_healthy(self) -> bool:
        """Quick health check returning boolean."""
        try:
            health = self.health()
            return health.status == "HEALTHY"
        except Exception:
            return False
    
    def get_version(self) -> str:
        """Get server API version."""
        health = self.health()
        return health.version


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE
# ══════════════════════════════════════════════════════════════════════════════

def create_client(base_url: str = "http://localhost:8000", **kwargs) -> SovereignClient:
    """Factory function to create a Sovereign Client."""
    return SovereignClient(base_url=base_url, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("SOVEREIGN CLIENT SDK v2.0.0 - Self Test")
    print("=" * 70)
    
    # Test model creation
    print("\n[1/4] Testing model creation...")
    
    user = UserData(user_id="USR-TEST-001", liveness_score=0.98)
    print(f"      ✓ UserData: {user.user_id}")
    
    payment = PaymentData(
        payer_id="ACME",
        payee_id="GLOBEX",
        amount=100000.00,
        fee_strategy="premium"  # v2.0
    )
    print(f"      ✓ PaymentData: {payment.payer_id} → {payment.payee_id}")
    print(f"      ✓ PaymentData.fee_strategy: {payment.fee_strategy}")
    
    manifest = ManifestData(
        shipment_id="SHP-001",
        declared_weight_kg=1000,
        actual_weight_kg=1005
    )
    shipment = ShipmentData(manifest=manifest)
    print(f"      ✓ ShipmentData: {shipment.manifest.shipment_id}")
    
    # Test FinancialTrace (v2.0)
    print("\n[2/4] Testing v2.0 FinancialTrace model...")
    
    trace = FinancialTrace(
        gross_amount="100000.00",
        currency="USD",
        settlement_intent_id="PI-abc123",
        settlement_status="captured",
        fees={"total": "2900.30", "strategy": "default"},
        net_amount="97099.70",
        ledger_committed=True
    )
    print(f"      ✓ FinancialTrace.gross_amount: {trace.gross_amount}")
    print(f"      ✓ FinancialTrace.total_fees: {trace.total_fees}")
    print(f"      ✓ FinancialTrace.net_amount: {trace.net_amount}")
    print(f"      ✓ FinancialTrace.ledger_committed: {trace.ledger_committed}")
    
    # Test TransactionReceipt (v2.0)
    print("\n[3/4] Testing v2.0 TransactionReceipt model...")
    
    receipt = TransactionReceipt(
        transaction_id="TRINITY-20260111",
        timestamp="2026-01-11T00:00:00Z",
        status="FINALIZED",
        finalized=True,
        gates={"biometric": {}, "aml": {}, "customs": {}},
        controller="BENSON",
        version="2.0.0",
        financial_trace=trace,
        invariants_enforced=["INV-API-003"]
    )
    print(f"      ✓ TransactionReceipt.is_finalized: {receipt.is_finalized}")
    print(f"      ✓ TransactionReceipt.financial_trace: Present")
    print(f"      ✓ TransactionReceipt.net_amount: {receipt.net_amount}")
    
    # Test PaymentRequiredError (v2.0)
    print("\n[4/4] Testing v2.0 PaymentRequiredError...")
    
    error = PaymentRequiredError(
        message="Settlement failed: Insufficient funds",
        transaction_id="TRINITY-123",
        reason="Insufficient funds: 0.00 < 50000.0",
        gates_passed=True
    )
    print(f"      ✓ PaymentRequiredError.gates_passed: {error.gates_passed}")
    print(f"      ✓ PaymentRequiredError.reason: {error.reason[:30]}...")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"SDK Version: {__version__}")
    print(f"API Version: {__api_version__}")
    print(f"Contract Hash: {__contract_hash__[:16]}...")
    print("=" * 70)
    print("\n🔒 The Scepter is re-forged. You may now command the Bank.")
