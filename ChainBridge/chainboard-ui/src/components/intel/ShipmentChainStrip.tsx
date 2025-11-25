/**
 * ShipmentChainStrip Component
 *
 * Visual representation of a shipment moving through the value chain.
 * Shows booking → pickup → transit → port → customs → warehouse → delivered
 * with risk overlays and capital blocking indicators.
 *
 * This is a presentational component; it does not fetch data.
 */

import {
  Package,
  Truck,
  Ship,
  Anchor,
  FileCheck,
  Warehouse,
  CheckCircle,
  AlertTriangle,
  Lock,
} from "lucide-react";

type ChainStage =
  | "booking"
  | "pickup"
  | "in_transit"
  | "port"
  | "customs"
  | "warehouse"
  | "delivered";

export interface ShipmentChainStripProps {
  shipmentRef: string;
  currentStage: ChainStage;
  riskScore?: number; // 0-100
  blockedCapital?: number; // USD
}

interface StageConfig {
  id: ChainStage;
  label: string;
  Icon: React.ElementType;
}

const STAGES: StageConfig[] = [
  { id: "booking", label: "Booking", Icon: Package },
  { id: "pickup", label: "Pickup", Icon: Truck },
  { id: "in_transit", label: "In Transit", Icon: Ship },
  { id: "port", label: "Port", Icon: Anchor },
  { id: "customs", label: "Customs", Icon: FileCheck },
  { id: "warehouse", label: "Warehouse", Icon: Warehouse },
  { id: "delivered", label: "Delivered", Icon: CheckCircle },
];

export default function ShipmentChainStrip({
  shipmentRef,
  currentStage,
  riskScore,
  blockedCapital,
}: ShipmentChainStripProps): JSX.Element {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);

  // Derive risk category from score
  const riskCategory = getRiskCategory(riskScore);

  return (
    <div className="rounded-xl border border-slate-800/70 bg-slate-900/50 p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-slate-100">Value Chain Progress</h4>
          <p className="mt-1 text-xs text-slate-400">
            Shipment: <span className="font-mono text-slate-300">{shipmentRef}</span>
          </p>
        </div>

        {/* Risk & Capital Indicators */}
        <div className="flex items-center gap-3">
          {riskScore !== undefined && (
            <div className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${
              riskCategory === "high"
                ? "border-red-500/50 bg-red-500/10"
                : riskCategory === "medium"
                ? "border-amber-500/50 bg-amber-500/10"
                : "border-emerald-500/50 bg-emerald-500/10"
            }`}>
              <AlertTriangle className={`h-3.5 w-3.5 ${
                riskCategory === "high"
                  ? "text-red-400"
                  : riskCategory === "medium"
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`} />
              <span className={`text-[10px] font-semibold uppercase tracking-wider ${
                riskCategory === "high"
                  ? "text-red-300"
                  : riskCategory === "medium"
                  ? "text-amber-300"
                  : "text-emerald-300"
              }`}>
                {riskCategory} Risk
              </span>
            </div>
          )}

          {blockedCapital !== undefined && blockedCapital > 0 && (
            <div className="flex items-center gap-1.5 rounded-full border border-red-500/50 bg-red-500/10 px-2.5 py-1">
              <Lock className="h-3.5 w-3.5 text-red-400" />
              <span className="text-[10px] font-semibold text-red-300">
                {formatCurrency(blockedCapital)} blocked
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Chain Visualization */}
      <div className="relative">
        {/* Connector Line - Progress indicator */}
        <div className="absolute top-6 left-8 right-8 h-0.5 bg-slate-800">
          {/* Progress fill calculated as percentage of stages completed */}
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-blue-500 transition-all duration-500"
            style={{ width: `${(currentIndex / (STAGES.length - 1)) * 100}%` }}
            aria-label={`Progress: ${Math.round((currentIndex / (STAGES.length - 1)) * 100)}%`}
          />
        </div>

        {/* Stage Nodes */}
        <div className="relative flex items-center justify-between">
          {STAGES.map((stage, index) => {
            const isActive = index === currentIndex;
            const isPast = index < currentIndex;

            return (
              <div key={stage.id} className="flex flex-col items-center">
                {/* Node Circle */}
                <div className={`z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 transition-all ${
                  isActive
                    ? "border-blue-500 bg-blue-500/20 shadow-lg shadow-blue-500/50"
                    : isPast
                    ? "border-emerald-500 bg-emerald-500/20"
                    : "border-slate-700 bg-slate-900"
                }`}>
                  <stage.Icon className={`h-5 w-5 ${
                    isActive
                      ? "text-blue-400"
                      : isPast
                      ? "text-emerald-400"
                      : "text-slate-600"
                  }`} />
                </div>

                {/* Label */}
                <span className={`mt-2 text-[10px] font-medium ${
                  isActive
                    ? "text-blue-400"
                    : isPast
                    ? "text-emerald-400"
                    : "text-slate-600"
                }`}>
                  {stage.label}
                </span>

                {/* Active Indicator */}
                {isActive && (
                  <div className="mt-1 flex items-center gap-1">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500"></span>
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Status Footer */}
      <div className="mt-6 flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 px-4 py-2">
        <span className="text-xs text-slate-400">Current Status</span>
        <span className="text-xs font-semibold text-slate-200">
          {STAGES[currentIndex].label}
        </span>
      </div>
    </div>
  );
}

/**
 * Derive risk category from numeric score
 */
function getRiskCategory(score?: number): "low" | "medium" | "high" {
  if (score === undefined) return "low";
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

/**
 * Format currency with proper locale
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}
