/**
 * Integration Examples: Glass Box UI Components
 *
 * How to wire SmartReconcileCard, LiquidityDashboard, and CollateralBreachModal
 * into the ChainBridge Operator Console v2.0
 */

import { useEffect, useState } from "react";

import { SmartReconcileCard } from "../components/audit/SmartReconcileCard";
import { CollateralBreachModal } from "../components/risk/CollateralBreachModal";
import { LiquidityDashboard } from "../pages/ChainStake/LiquidityDashboard";
import type { AuditVector, CollateralBreach, StakingPosition } from "../types/chainbridge";

// ============================================================================
// EXAMPLE 1: Using SmartReconcileCard in ChainAudit Flow
// ============================================================================

/**
 * Example: Payment reconciliation confirmation page
 * Triggered after ChainAudit analyzes a payment intent
 */
export function PaymentReconciliationPage() {
  // Fetch vectors from ChainAudit backend
  const auditVectors: AuditVector[] = [
    {
      label: "Shipment Delay",
      value: 4.5,
      unit: "hours",
      impact: -1.2,
      severity: "HIGH",
    },
    {
      label: "Temperature Variance",
      value: 2.1,
      unit: "°C",
      impact: -0.3,
      severity: "LOW",
    },
  ];

  const handleAcceptPayment = async (adjusted: boolean) => {
    try {
      // Call backend to confirm payment
      const response = await fetch("/api/payments/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paymentIntentId: "pi_12345",
          adjusted,
          confidence: 87.5,
        }),
      });

      if (response.ok) {
        // Show success notification
        console.log("Payment confirmed");
      }
    } catch (error) {
      console.error("Payment confirmation failed:", error);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Reconciliation Review</h1>

      <SmartReconcileCard
        confidenceScore={87.5}
        deduction={245.5}
        vectors={auditVectors}
        currency="USD"
        onAccept={handleAcceptPayment}
        onCancel={() => window.history.back()}
      />
    </div>
  );
}

// ============================================================================
// EXAMPLE 2: Using LiquidityDashboard in ChainStake Page
// ============================================================================

/**
 * Example: Treasury dashboard for staking positions
 * Shows working capital, yield, and collateral health
 */
export function TreasuryDashboardPage() {
  const [positions, setPositions] = useState<StakingPosition[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Fetch positions from ChainStake smart contracts
    const fetchPositions = async () => {
      try {
        const response = await fetch("/api/staking/positions");
        const data = await response.json();
        setPositions(data);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPositions();
  }, []);

  if (isLoading) {
    return <div>Loading positions...</div>;
  }

  return (
    <LiquidityDashboard
      positions={positions}
      totalYieldAccrued={8251.85}
      yieldPerSecond={0.0095}
      currency="USD"
    />
  );
}

// ============================================================================
// EXAMPLE 3: Using CollateralBreachModal in OC Layout
// ============================================================================

/**
 * Example: Operator Console with breach monitoring
 * Modal triggers automatically when position LTV > 90%
 */
export function OperatorConsoleWithBreach() {
  const [breach, setBreach] = useState<CollateralBreach | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Poll for critical positions
  useEffect(() => {
    const checkForBreaches = async () => {
      const response = await fetch("/api/staking/critical-positions");
      const data: CollateralBreach[] = await response.json();

      if (data.length > 0) {
        // Show first critical breach
        setBreach(data[0]);
        setIsModalOpen(true);
      }
    };

    const interval = setInterval(checkForBreaches, 30000); // Check every 30s
    checkForBreaches(); // Initial check

    return () => clearInterval(interval);
  }, []);

  const handleFlashRepay = async (positionId: string) => {
    // Call flash repay smart contract
    const response = await fetch("/api/staking/flash-repay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ positionId }),
    });

    if (response.ok) {
      console.log("Flash repay initiated");
      setIsModalOpen(false);
      // Refresh positions
    }
  };

  const handleAbandonLiquidate = async (positionId: string) => {
    // Call liquidation smart contract
    const response = await fetch("/api/staking/liquidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ positionId }),
    });

    if (response.ok) {
      console.log("Position liquidated");
      setIsModalOpen(false);
    }
  };

  return (
    <div className="bg-slate-950 min-h-screen">
      {/* Main OC content */}
      <div className="p-6">{/* ... rest of operator console ... */}</div>

      {/* Breach Modal */}
      <CollateralBreachModal
        breach={breach}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onFlashRepay={handleFlashRepay}
        onAbandonLiquidate={handleAbandonLiquidate}
      />
    </div>
  );
}

// ============================================================================
// EXAMPLE 4: Combined Dashboard (All Three Components)
// ============================================================================

interface ReconciliationData {
  confidence: number;
  deduction: number;
  vectors: AuditVector[];
}

/**
 * Example: Full Bloomberg Terminal view combining all three components
 * Shows reconciliation decisions, staking dashboard, and breach monitoring
 */
export function FullCorporateTreasuryDashboard() {
  const [reconciliationData, setReconciliationData] = useState<ReconciliationData | null>(null);
  const [positions, setPositions] = useState<StakingPosition[]>([]);
  const [breach, setBreach] = useState<CollateralBreach | null>(null);

  useEffect(() => {
    // Fetch all data in parallel
    const fetchData = async () => {
      try {
        const [audit, staking, critical] = await Promise.all([
          fetch("/api/audit/pending").then((r) => r.json()),
          fetch("/api/staking/positions").then((r) => r.json()),
          fetch("/api/staking/critical-positions").then((r) => r.json()),
        ]);

        setReconciliationData(audit);
        setPositions(staking);
        setBreach(critical[0] || null);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="bg-slate-950 min-h-screen space-y-8 p-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold text-slate-100">
          Corporate Treasury Interface
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          ChainBridge v2.0 — Glass Box Reconciliation & Staking Dashboard
        </p>
      </div>

      {/* Grid: Reconciliation + Liquidity */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Pending Reconciliations */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-slate-200">
            Pending Reconciliations
          </h2>
          {reconciliationData && (
            <SmartReconcileCard
              confidenceScore={reconciliationData.confidence}
              deduction={reconciliationData.deduction}
              vectors={reconciliationData.vectors}
              currency="USD"
              onAccept={(adjusted: boolean) =>
                console.log("Reconciliation accepted", { adjusted })
              }
              onCancel={() => console.log("Review reconciliation")}
            />
          )}
        </div>

        {/* Right: Staking Summary */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-slate-200">
            Position Summary
          </h2>
          {positions.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-400 mb-2">
                Total Staked Value
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono">
                {positions
                  .reduce((sum, p) => sum + p.collateralValue, 0)
                  .toLocaleString("en-US", {
                    style: "currency",
                    currency: "USD",
                    maximumFractionDigits: 0,
                  })}
              </div>
              <div className="text-xs text-slate-600 mt-2">
                {positions.length} active positions
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Full Liquidity Dashboard */}
      {positions.length > 0 && (
        <div className="mt-8">
          <LiquidityDashboard
            positions={positions}
            totalYieldAccrued={8251.85}
            yieldPerSecond={0.0095}
            currency="USD"
          />
        </div>
      )}

      {/* Breach Modal (Always Present) */}
      <CollateralBreachModal
        breach={breach}
        isOpen={breach !== null}
        onClose={() => setBreach(null)}
        onFlashRepay={async (id: string) => console.log("Flash repay", id)}
        onAbandonLiquidate={async (id: string) => console.log("Liquidate", id)}
      />
    </div>
  );
}

// ============================================================================
// EXAMPLE 5: API Contract (Backend Requirements)
// ============================================================================

/**
 * Backend API endpoints required for Glass Box components
 *
 * RECONCILIATION ENDPOINTS:
 * GET /api/audit/pending - Get pending reconciliation decisions
 *   Response: { confidence: number, deduction: number, vectors: AuditVector[] }
 *
 * POST /api/payments/confirm - Confirm payment with reconciliation
 *   Body: { paymentIntentId: string, adjusted: boolean, confidence: number }
 *
 * STAKING ENDPOINTS:
 * GET /api/staking/positions - Get all active staking positions
 *   Response: StakingPosition[]
 *
 * GET /api/staking/critical-positions - Get positions with LTV > 90%
 *   Response: CollateralBreach[]
 *
 * POST /api/staking/flash-repay - Initiate flash repay
 *   Body: { positionId: string }
 *
 * POST /api/staking/liquidate - Liquidate position
 *   Body: { positionId: string }
 *
 * POLLING STRATEGY:
 * - Reconciliation: Check on-demand (user navigates to page)
 * - Positions: Poll every 30 seconds (background monitoring)
 * - Breaches: Real-time WebSocket or poll every 5 seconds
 */

export { };
