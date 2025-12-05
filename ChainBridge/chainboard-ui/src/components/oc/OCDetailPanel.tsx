/**
 * OCDetailPanel - Right Side Detail Panel for The OC
 *
 * M04-FRONTEND-FUSION: Now fetches real risk snapshot, events, pricing, and audit pack from backend.
 * Shows detailed information for selected shipment with tabbed views.
 * Tabs: Overview | Events | Risk | Pricing | Audit
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Copy, ExternalLink, Loader2, RefreshCw, Search, Shield, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { approveReconciliation } from "../../api/chainpay";
import { createSnapshotExport } from "../../services/apiClient";
import { fetchAuditPack, fetchEventTimeline, fetchFinancingQuote, fetchInventoryStakesForShipment, fetchPricingBreakdown, fetchReconciliationSummary, fetchRicardianInstrumentForShipment, fetchRiskSnapshot } from "../../services/operatorApi";
import type { AuditVector, OperatorQueueItem, TransportMode } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { SmartReconcileCard } from "../audit/SmartReconcileCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

import { AuditPackView } from "./AuditPackView";
import { ModeBadge } from "./hud/ModeBadge";
import { RiskBadge } from "./hud/RiskBadge";

interface OCDetailPanelProps {
  selectedShipment: OperatorQueueItem | null;
}

type TabType = "overview" | "events" | "risk" | "pricing" | "reconciliation" | "legal" | "audit";

// Action Button Component with Real-time Feedback
function ExportSnapshotButton({
  shipmentId,
  disabled,
  onSuccess,
}: {
  shipmentId: string;
  disabled?: boolean;
  onSuccess?: () => void;
}) {
  const [isExporting, setIsExporting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const queryClient = useQueryClient();

  const handleExport = async () => {
    setIsExporting(true);
    setMessage(null);
    try {
      await createSnapshotExport(shipmentId);
      setMessage({ type: "success", text: "✅ Snapshot export created" });
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["operatorSummary"] });
      queryClient.invalidateQueries({ queryKey: ["operatorQueue"] });
      onSuccess?.();
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({
        type: "error",
        text: `❌ Export failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-2">
      <button
        onClick={handleExport}
        disabled={disabled || isExporting}
        className={classNames(
          "w-full px-4 py-2 rounded-lg font-medium flex items-center justify-center gap-2 transition-all",
          disabled || isExporting
            ? "bg-slate-700 text-slate-400 cursor-not-allowed"
            : "bg-blue-600 text-white hover:bg-blue-700"
        )}
      >
        {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
        {isExporting ? "Exporting..." : "Export Snapshot"}
      </button>
      {message && (
        <div
          className={classNames(
            "text-xs p-2 rounded border",
            message.type === "success"
              ? "bg-emerald-950/50 border-emerald-700/50 text-emerald-300"
              : "bg-rose-950/50 border-rose-700/50 text-rose-300"
          )}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}


export function OCDetailPanel({ selectedShipment }: OCDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const queryClient = useQueryClient();

  // Listen for tab switch events from AuditPackView
  useEffect(() => {
    const handleTabSwitch = () => {
      setActiveTab("reconciliation");
    };
    window.addEventListener("switchToReconciliation", handleTabSwitch);
    return () => {
      window.removeEventListener("switchToReconciliation", handleTabSwitch);
    };
  }, []);

  // M04: Fetch real risk snapshot from backend
  const {
    data: riskSnapshot,
    isLoading: riskLoading,
    error: riskError,
  } = useQuery({
    queryKey: ["riskSnapshot", selectedShipment?.shipmentId],
    queryFn: () => fetchRiskSnapshot(selectedShipment!.shipmentId),
    enabled: !!selectedShipment,
    staleTime: 30_000,
    retry: 2,
  });

  // M04: Fetch real event timeline from backend
  const {
    data: eventTimeline,
    isLoading: eventsLoading,
    error: eventsError,
  } = useQuery({
    queryKey: ["eventTimeline", selectedShipment?.shipmentId],
    queryFn: () => fetchEventTimeline(selectedShipment!.shipmentId),
    enabled: !!selectedShipment,
    staleTime: 15_000,
    retry: 2,
  });

  // M04: Fetch pricing breakdown from backend
  const {
    data: pricing,
    isLoading: pricingLoading,
    error: pricingError,
  } = useQuery({
    queryKey: ["pricingBreakdown", selectedShipment?.shipmentId],
    queryFn: () => fetchPricingBreakdown(selectedShipment!.shipmentId),
    enabled: !!selectedShipment,
    staleTime: 60_000,
    retry: 2,
  });

  // M04: Fetch audit pack from backend (only when Audit tab is active)
  const {
    data: auditPack,
    isLoading: auditLoading,
    error: auditError,
  } = useQuery({
    queryKey: ["auditPack", selectedShipment?.shipmentId],
    queryFn: () => fetchAuditPack(selectedShipment!.shipmentId),
    enabled: !!selectedShipment && activeTab === "audit",
    staleTime: 60_000,
    retry: 2,
  });

  // R01: Fetch reconciliation summary from backend
  const {
    data: recon,
    isLoading: reconLoading,
    error: reconError,
  } = useQuery({
    queryKey: ["reconciliation", selectedShipment?.shipmentId],
    queryFn: () => fetchReconciliationSummary(selectedShipment!.shipmentId),
    enabled: !!selectedShipment,
    staleTime: 60_000,
    retry: 2,
  });

  // LEGAL-R01: Fetch Ricardian legal wrapper
  const {
    data: legalWrapper,
    isLoading: legalLoading,
    error: legalError,
  } = useQuery({
    queryKey: ["ricardianInstrument", selectedShipment?.shipmentId],
    queryFn: () => fetchRicardianInstrumentForShipment(selectedShipment!.shipmentId),
    enabled: !!selectedShipment,
    staleTime: 60_000,
    retry: 2,
  });

  // FINANCE-R01: Derive physical reference and notional value
  const physicalRef = selectedShipment?.shipmentId;
  const notionalValue =
    selectedShipment?.declared_valueUsd ?? selectedShipment?.declaredValueUsd ?? 0; // TODO: Replace with actual backend field

  // FINANCE-R01: Fetch financing quote
  const {
    data: financeQuote,
    isLoading: financeLoading,
    error: financeError,
  } = useQuery({
    queryKey: ["financingQuote", physicalRef, notionalValue],
    queryFn: () => fetchFinancingQuote(physicalRef!, notionalValue),
    enabled: !!physicalRef && notionalValue > 0 && legalWrapper?.status === "ACTIVE",
    staleTime: 60_000,
    retry: 2,
  });

  // FINANCE-R01: Fetch inventory stakes
  const {
    data: stakes,
    isLoading: stakesLoading,
    error: stakesError,
  } = useQuery({
    queryKey: ["inventoryStakes", physicalRef],
    queryFn: () => fetchInventoryStakesForShipment(physicalRef!),
    enabled: !!physicalRef,
    staleTime: 60_000,
    retry: 2,
  });

  if (!selectedShipment) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        <div className="text-center">
          <Search className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="font-medium">Select a settlement in the queue</p>
          <p className="text-sm mt-1">to view details and take action</p>
        </div>
      </div>
    );
  }

  // Tab configuration
  const tabs: { id: TabType; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "events", label: "Events" },
    { id: "risk", label: "Risk" },
    { id: "pricing", label: "Pricing" },
    { id: "reconciliation", label: "Reconciliation" },
    { id: "legal", label: "Legal Wrapper" },
    { id: "audit", label: "Audit" },
  ];

  return (
    <div className="flex flex-col overflow-hidden h-full">
      {/* Detail Header Card */}
      <Card className="bg-slate-800/50 border-slate-700 m-4 mb-2 flex-shrink-0">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="font-mono text-lg">{selectedShipment.shipmentId}</CardTitle>
              <CardDescription className="mt-1 flex gap-2 flex-wrap">
                {selectedShipment.corridorCode && (
                  <span className="text-slate-400">{selectedShipment.corridorCode}</span>
                )}
                {selectedShipment.mode && (
                  <span className="text-slate-400">•</span>
                )}
                {selectedShipment.mode && (
                  <ModeBadge
                    mode={selectedShipment.mode as TransportMode}
                    size="sm"
                    showLabel
                  />
                )}
                {selectedShipment.incoterm && (
                  <>
                    <span className="text-slate-400">•</span>
                    <span className="text-slate-400">{selectedShipment.incoterm}</span>
                  </>
                )}
              </CardDescription>
            </div>
            <RiskBadge
              riskLevel={selectedShipment.riskLevel}
              size="lg"
            />
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Risk Score</span>
            <span className="font-bold text-slate-200">{selectedShipment.riskScore}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Completeness</span>
            <span className="font-bold text-slate-200">{selectedShipment.completeness_pct}%</span>
          </div>
          {(selectedShipment.blocking_gap_count ?? selectedShipment.blockingGapCount ?? 0) > 0 && (
            <div className="flex justify-between">
              <span className="text-rose-400">Blocking Gaps</span>
              <span className="font-bold text-rose-300">{selectedShipment.blocking_gap_count ?? selectedShipment.blockingGapCount ?? 0}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tab Navigation */}
      <div className="flex gap-1 px-4 mb-2 border-b border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={classNames(
              "px-3 py-2 text-xs font-medium transition-colors relative",
              activeTab === tab.id
                ? "text-emerald-400"
                : "text-slate-400 hover:text-slate-300"
            )}
          >
            {tab.label}
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-400" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content - Scrollable */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <Card className="bg-slate-800/30 border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Summary</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Level</span>
                  <span className="text-slate-200 font-medium">{selectedShipment.riskLevel}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Score</span>
                  <span className="text-slate-200 font-medium">{selectedShipment.riskScore}</span>
                </div>
                {selectedShipment.template_name && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Template</span>
                    <span className="text-slate-200">{selectedShipment.template_name}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <Card className="bg-slate-800/30 border-slate-700">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Actions</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <ExportSnapshotButton
                  shipmentId={selectedShipment.shipmentId}
                  disabled={!selectedShipment.needsSnapshot}
                />
                {!selectedShipment.needsSnapshot && (
                  <p className="text-xs text-slate-500 mt-2 italic">
                    Snapshot already exported. Ready for next steps.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Events Tab */}
        {activeTab === "events" && (
          <Card className="bg-slate-800/30 border-slate-700">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Event Timeline</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              {eventsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : eventsError ? (
                <div className="flex items-center gap-2 text-rose-400 text-xs">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Failed to load events</span>
                </div>
              ) : eventTimeline && eventTimeline.events.length > 0 ? (
                <div className="space-y-2">
                  {eventTimeline.events.map((event, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-2 bg-slate-900/50 rounded border border-slate-700"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span
                              className={classNames(
                                "text-xs font-medium px-2 py-0.5 rounded",
                                event.severity === "ERROR"
                                  ? "bg-rose-900/50 text-rose-300"
                                  : event.severity === "WARNING"
                                  ? "bg-amber-900/50 text-amber-300"
                                  : "bg-blue-900/50 text-blue-300"
                              )}
                            >
                              {event.eventType}
                            </span>
                          </div>
                          <p className="text-slate-300 mt-1">{event.description}</p>
                          {event.actor && (
                            <p className="text-xs text-slate-500 mt-1">by {event.actor}</p>
                          )}
                        </div>
                        <time className="text-xs text-slate-500 whitespace-nowrap">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </time>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-xs italic">No events recorded</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Risk Tab */}
        {activeTab === "risk" && (
          <Card className="bg-slate-800/30 border-slate-700">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center justify-between">
                Risk Snapshot
                {riskSnapshot?.snapshot_hash && (
                  <span className="text-xs font-mono text-slate-500">
                    #{riskSnapshot.snapshot_hash.slice(0, 8)}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-3">
              {riskLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              ) : riskError ? (
                <div className="flex items-center gap-2 text-rose-400 text-xs">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Failed to load risk data</span>
                </div>
              ) : riskSnapshot ? (
                <>
                  {/* Risk Level & Score */}
                  <div className="flex justify-between">
                    <span className="text-slate-400">Level</span>
                    <span className="text-slate-200 font-medium">{riskSnapshot.riskLevel}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Score</span>
                    <span className="text-slate-200 font-medium">{riskSnapshot.riskScore}</span>
                  </div>

                  {/* Readiness Reason */}
                  {riskSnapshot.readiness_reason && (
                    <div className="pt-2 border-t border-slate-700">
                      <p className="text-xs text-slate-400 mb-1">Readiness Status:</p>
                      <p className="text-slate-300">{riskSnapshot.readiness_reason}</p>
                    </div>
                  )}

                  {/* Compliance Blocks */}
                  {riskSnapshot.compliance_blocks.length > 0 && (
                    <div className="pt-2 border-t border-slate-700">
                      <p className="text-xs text-slate-400 mb-2">Compliance Blocks:</p>
                      <div className="space-y-1">
                        {riskSnapshot.compliance_blocks.map((block, idx) => (
                          <div
                            key={idx}
                            className={classNames(
                              "px-2 py-1 rounded text-xs",
                              block.severity === "CRITICAL"
                                ? "bg-rose-950/50 text-rose-300 border border-rose-700/50"
                                : block.severity === "HIGH"
                                ? "bg-amber-950/50 text-amber-300 border border-amber-700/50"
                                : "bg-blue-950/50 text-blue-300 border border-blue-700/50"
                            )}
                          >
                            <div className="font-medium">{block.block_type}</div>
                            <div className="text-xs opacity-90">{block.message}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Risk Factors */}
                  {riskSnapshot.risk_factors.length > 0 && (
                    <div className="pt-2 border-t border-slate-700">
                      <p className="text-xs text-slate-400 mb-2">Risk Factors:</p>
                      <div className="space-y-1">
                        {riskSnapshot.risk_factors.map((factor, idx) => (
                          <div key={idx} className="flex justify-between items-start">
                            <span className="text-slate-300">{factor.description}</span>
                            <span
                              className={classNames(
                                "text-xs font-mono ml-2",
                                factor.impact_score > 50 ? "text-rose-400" : "text-amber-400"
                              )}
                            >
                              {factor.impact_score}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </CardContent>
          </Card>
        )}

        {/* Pricing Tab */}
        {activeTab === "pricing" && (
          <Card className="bg-slate-800/30 border-slate-700">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Pricing Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2">
              {pricingLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : pricingError ? (
                <div className="flex items-center gap-2 text-rose-400 text-xs">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Pricing not available</span>
                </div>
              ) : pricing ? (
                <>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Base Rate</span>
                    <span className="font-mono text-slate-200">${pricing.base_rate.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Fuel Surcharge</span>
                    <span className="font-mono text-slate-200">
                      ${pricing.fuel_surcharge.toFixed(2)}
                    </span>
                  </div>
                  {pricing.accessorials > 0 && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Accessorials</span>
                      <span className="font-mono text-slate-200">
                        ${pricing.accessorials.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {pricing.volatility_buffer > 0 && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Volatility Buffer</span>
                      <span className="font-mono text-amber-400">
                        ${pricing.volatility_buffer.toFixed(2)}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between pt-2 border-t border-slate-700 font-bold">
                    <span className="text-slate-200">Total Price</span>
                    <span className="font-mono text-emerald-400">
                      ${pricing.total_price.toFixed(2)}
                    </span>
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        )}

        {/* Reconciliation Tab - R01 Micro-Settlement */}
        {activeTab === "reconciliation" && (
          <div className="space-y-4">
            {reconLoading ? (
              <>
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-64 w-full" />
              </>
            ) : reconError ? (
              <div className="flex items-center gap-2 text-rose-400 text-xs p-4">
                <AlertTriangle className="h-4 w-4" />
                <span>Reconciliation data not available</span>
              </div>
            ) : recon ? (
              <>
                {/* Smart Reconcile Card - Bloomberg Terminal View */}
                <SmartReconcileCard
                  confidenceScore={recon.reconScore}
                  deduction={recon.heldAmount}
                  vectors={
                    recon.flags.map((flag, idx): AuditVector => ({
                      label: flag.replace(/_/g, " "),
                      value: idx + 1,
                      unit: "flag",
                      impact: -1.5,
                      severity: idx % 3 === 0 ? "HIGH" : idx % 3 === 1 ? "MEDIUM" : "LOW",
                    })) || []
                  }
                  currency="USD"
                  onAccept={async (adjusted) => {
                    if (selectedShipment) {
                      await approveReconciliation(recon.policyId, { adjusted });
                      queryClient.invalidateQueries({ queryKey: ["reconciliation", selectedShipment.shipmentId] });
                    }
                  }}
                  onCancel={() => {
                    /* Close/dismiss reconciliation review */
                  }}
                />

                {/* Reconciliation Summary Card */}
                <Card className="bg-slate-800/30 border-slate-700">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Micro-Settlement Summary</CardTitle>
                      <span
                        className={classNames(
                          "px-3 py-1 rounded text-xs font-bold",
                          recon.decision === "AUTO_APPROVE"
                            ? "bg-emerald-900/50 text-emerald-300 border border-emerald-700/50"
                            : recon.decision === "PARTIAL_APPROVE"
                            ? "bg-amber-900/50 text-amber-300 border border-amber-700/50"
                            : "bg-rose-900/50 text-rose-300 border border-rose-700/50"
                        )}
                      >
                        {recon.decision === "AUTO_APPROVE"
                          ? "Auto-approved"
                          : recon.decision === "PARTIAL_APPROVE"
                          ? "Partial approval"
                          : "Blocked"}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="text-sm space-y-3">
                    {/* Cash Flow Summary */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-emerald-950/30 border border-emerald-700/50 rounded">
                        <div className="text-xs text-emerald-400 mb-1">Approved</div>
                        <div className="text-lg font-mono font-bold text-emerald-300">
                          ${recon.approvedAmount.toFixed(2)}
                        </div>
                      </div>
                      <div className="p-3 bg-amber-950/30 border border-amber-700/50 rounded">
                        <div className="text-xs text-amber-400 mb-1">Held</div>
                        <div className="text-lg font-mono font-bold text-amber-300">
                          ${recon.heldAmount.toFixed(2)}
                        </div>
                      </div>
                    </div>

                    {/* Recon Score */}
                    <div className="pt-2 border-t border-slate-700">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-slate-400">Reconciliation Score</span>
                        <span className="text-sm font-mono font-bold text-slate-200">
                          {recon.reconScore}/100
                        </span>
                      </div>
                      <div className="h-2 bg-slate-700 rounded-full overflow-hidden relative">
                        <div
                          className={classNames(
                            "h-full transition-all absolute left-0 top-0",
                            recon.reconScore >= 90
                              ? "bg-emerald-500"
                              : recon.reconScore >= 70
                              ? "bg-amber-500"
                              : "bg-rose-500"
                          )}
                          style={{ width: `${Math.min(100, Math.max(0, recon.reconScore))}%` }}
                        />
                      </div>
                    </div>

                    {/* Policy */}
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Policy ID</span>
                      <span className="font-mono text-slate-300">{recon.policyId}</span>
                    </div>

                    {/* Flags */}
                    {recon.flags.length > 0 && (
                      <div className="pt-2 border-t border-slate-700">
                        <div className="text-xs text-slate-400 mb-2">Applied Adjustments</div>
                        <div className="flex flex-wrap gap-1.5">
                          {recon.flags.map((flag, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-blue-900/30 text-blue-300 border border-blue-700/50 rounded text-xs font-medium"
                            >
                              {flag.replace(/_/g, " ")}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Line-by-Line Reconciliation Table */}
                <Card className="bg-slate-800/30 border-slate-700">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">Line-by-Line Reconciliation</CardTitle>
                    <CardDescription className="text-xs">
                      {recon.lines.length} line item{recon.lines.length !== 1 ? "s" : ""} reconciled
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-slate-700">
                            <th className="text-left py-2 px-2 text-slate-400 font-medium">Line / SKU</th>
                            <th className="text-right py-2 px-2 text-slate-400 font-medium">PO Qty</th>
                            <th className="text-right py-2 px-2 text-slate-400 font-medium">Exec Qty</th>
                            <th className="text-right py-2 px-2 text-slate-400 font-medium">Inv Qty</th>
                            <th className="text-left py-2 px-2 text-slate-400 font-medium">Status</th>
                            <th className="text-right py-2 px-2 text-slate-400 font-medium">Approved</th>
                            <th className="text-right py-2 px-2 text-slate-400 font-medium">Held</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/50">
                          {recon.lines.map((line) => (
                            <tr key={line.lineId} className="hover:bg-slate-700/30">
                              <td className="py-2.5 px-2">
                                <div className="font-medium text-slate-200">
                                  {line.sku || line.lineId}
                                </div>
                                {line.description && (
                                  <div className="text-slate-400 text-xs mt-0.5 truncate max-w-[200px]">
                                    {line.description}
                                  </div>
                                )}
                              </td>
                              <td className="py-2.5 px-2 text-right font-mono text-slate-300">
                                {line.poQty ?? "—"}
                              </td>
                              <td className="py-2.5 px-2 text-right font-mono text-slate-300">
                                {line.execQty ?? "—"}
                              </td>
                              <td className="py-2.5 px-2 text-right font-mono text-slate-300">
                                {line.invoiceQty ?? "—"}
                              </td>
                              <td className="py-2.5 px-2">
                                <span
                                  className={classNames(
                                    "inline-block px-2 py-0.5 rounded text-xs font-medium",
                                    line.status === "MATCHED"
                                      ? "bg-emerald-900/30 text-emerald-300 border border-emerald-700/50"
                                      : line.status === "UNDER_DELIVERED" ||
                                        line.status === "OVER_DELIVERED" ||
                                        line.status === "PRICE_DELTA"
                                      ? "bg-amber-900/30 text-amber-300 border border-amber-700/50"
                                      : "bg-rose-900/30 text-rose-300 border border-rose-700/50"
                                  )}
                                >
                                  {line.status.replace(/_/g, " ")}
                                </span>
                                <div className="text-slate-500 mt-0.5 text-xs">
                                  {line.reasonCode}
                                </div>
                              </td>
                              <td className="py-2.5 px-2 text-right font-mono text-emerald-400 font-medium">
                                ${line.approvedAmount.toFixed(2)}
                              </td>
                              <td className="py-2.5 px-2 text-right font-mono text-amber-400 font-medium">
                                ${line.heldAmount.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot className="border-t-2 border-slate-600">
                          <tr className="font-bold">
                            <td colSpan={5} className="py-2.5 px-2 text-slate-200">
                              Total
                            </td>
                            <td className="py-2.5 px-2 text-right font-mono text-emerald-400">
                              ${recon.approvedAmount.toFixed(2)}
                            </td>
                            <td className="py-2.5 px-2 text-right font-mono text-amber-400">
                              ${recon.heldAmount.toFixed(2)}
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : null}
          </div>
        )}

        {/* Legal Wrapper Tab - LEGAL-R01 */}
        {activeTab === "legal" && (
          <div className="space-y-4">
            {legalLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : legalError ? (
              <div className="flex items-center gap-2 text-rose-400 text-xs p-4">
                <AlertTriangle className="h-4 w-4" />
                <span>Legal wrapper data unavailable</span>
              </div>
            ) : !legalWrapper ? (
              <Card className="bg-slate-800/30 border-slate-700">
                <CardContent className="py-8 text-center">
                  <Shield className="h-12 w-12 mx-auto mb-3 text-slate-600 opacity-50" />
                  <p className="text-slate-400 text-sm font-medium">
                    No Ricardian legal wrapper associated with this shipment yet
                  </p>
                  <p className="text-slate-500 text-xs mt-2">
                    This shipment is data-only and not yet bankable
                  </p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Legal Wrapper Status Card */}
                <Card className="bg-slate-800/30 border-slate-700">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Shield className="h-5 w-5 text-emerald-400" />
                        <CardTitle className="text-sm">Ricardian Legal Wrapper</CardTitle>
                      </div>
                      <span
                        className={classNames(
                          "px-3 py-1 rounded text-xs font-bold",
                          legalWrapper.status === "ACTIVE"
                            ? "bg-emerald-900/50 text-emerald-300 border border-emerald-700/50"
                            : legalWrapper.status === "FROZEN"
                            ? "bg-rose-900/50 text-rose-300 border border-rose-700/50"
                            : "bg-slate-700 text-slate-300 border border-slate-600"
                        )}
                      >
                        {legalWrapper.status === "ACTIVE"
                          ? "Ricardian Wrapped (Active)"
                          : legalWrapper.status === "FROZEN"
                          ? "FROZEN – Legal Hold"
                          : "Terminated"}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    {/* Instrument Details */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Instrument Type</div>
                        <div className="font-medium text-slate-200">
                          {legalWrapper.instrumentType.replace(/_/g, " ")}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Physical Reference</div>
                        <div className="font-mono text-xs text-slate-200">
                          {legalWrapper.physicalReference}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Governing Law</div>
                        <div className="text-slate-200">{legalWrapper.governingLaw}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400 mb-1">Ricardian Version</div>
                        <div className="font-mono text-xs text-slate-200">
                          {legalWrapper.ricardianVersion}
                        </div>
                      </div>
                    </div>

                    {/* PDF Hash & Links */}
                    <div className="pt-3 border-t border-slate-700">
                      <div className="text-xs text-slate-400 mb-2">Document Hash & Links</div>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2 p-2 bg-slate-900/50 rounded">
                          <div>
                            <div className="text-xs text-slate-500">PDF Hash</div>
                            <div className="font-mono text-xs text-slate-300 mt-0.5">
                              {legalWrapper.pdfHash.slice(0, 16)}...{legalWrapper.pdfHash.slice(-8)}
                            </div>
                          </div>
                          <button
                            onClick={() => navigator.clipboard.writeText(legalWrapper.pdfHash)}
                            className="p-1.5 hover:bg-slate-700 rounded transition-colors"
                            title="Copy full hash"
                          >
                            <Copy className="h-3.5 w-3.5 text-slate-400" />
                          </button>
                        </div>

                        <div className="flex gap-2">
                          <a
                            href={legalWrapper.pdfUri}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-300 text-xs font-medium rounded border border-emerald-700/50 transition-colors"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            View Legal PDF
                          </a>
                          {legalWrapper.pdfIpfsUri && (
                            <a
                              href={legalWrapper.pdfIpfsUri}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs font-medium rounded transition-colors"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              IPFS
                            </a>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Smart Contract Info */}
                    {legalWrapper.smartContractChain && legalWrapper.smartContractAddress && (
                      <div className="pt-3 border-t border-slate-700">
                        <div className="text-xs text-slate-400 mb-2">Smart Contract (On-Chain)</div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <div className="text-xs text-slate-500">Chain</div>
                              <div className="text-slate-200 text-sm mt-0.5">
                                {legalWrapper.smartContractChain}
                              </div>
                            </div>
                            <div className="flex-1">
                              <div className="text-xs text-slate-500">Contract Address</div>
                              <div className="font-mono text-xs text-slate-300 mt-0.5 flex items-center gap-1">
                                {legalWrapper.smartContractAddress.slice(0, 10)}...
                                {legalWrapper.smartContractAddress.slice(-8)}
                                <button
                                  onClick={() =>
                                    navigator.clipboard.writeText(legalWrapper.smartContractAddress!)
                                  }
                                  className="p-0.5 hover:bg-slate-700 rounded"
                                  title="Copy address"
                                >
                                  <Copy className="h-3 w-3 text-slate-500" />
                                </button>
                              </div>
                            </div>
                          </div>

                          {legalWrapper.lastSignedTxHash && (
                            <div>
                              <div className="text-xs text-slate-500">Last Signed Transaction</div>
                              <div className="font-mono text-xs text-slate-300 mt-0.5 flex items-center gap-1">
                                {legalWrapper.lastSignedTxHash.slice(0, 16)}...
                                {legalWrapper.lastSignedTxHash.slice(-8)}
                                <button
                                  onClick={() =>
                                    navigator.clipboard.writeText(legalWrapper.lastSignedTxHash!)
                                  }
                                  className="p-0.5 hover:bg-slate-700 rounded"
                                  title="Copy tx hash"
                                >
                                  <Copy className="h-3 w-3 text-slate-500" />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Freeze Warning */}
                    {legalWrapper.status === "FROZEN" && legalWrapper.freezeReason && (
                      <div className="pt-3 border-t border-rose-700/50">
                        <div className="p-3 bg-rose-950/30 border border-rose-700/50 rounded">
                          <div className="flex items-start gap-2">
                            <AlertTriangle className="h-4 w-4 text-rose-400 mt-0.5 flex-shrink-0" />
                            <div>
                              <div className="text-xs font-bold text-rose-300 mb-1">Frozen Reason:</div>
                              <div className="text-xs text-rose-200">{legalWrapper.freezeReason}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Digital Supremacy Section - SONNY PACK */}
                {legalWrapper.materialAdverseOverride ? (
                  // Kill Switch Triggered
                  <Card className="bg-rose-950/30 border-rose-700">
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-2">
                        <Zap className="h-5 w-5 text-rose-400" />
                        <CardTitle className="text-sm text-rose-300">🚨 MATERIAL ADVERSE EXCEPTION</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="p-4 bg-rose-900/30 border border-rose-700/50 rounded">
                        <div className="text-sm font-bold text-rose-200 mb-2">
                          Digital Supremacy has been suspended due to:
                        </div>
                        <div className="text-sm text-rose-300">
                          {legalWrapper.freezeReason || "Material adverse event detected"}
                        </div>
                        <div className="text-xs text-rose-400 mt-3 pt-3 border-t border-rose-700/50">
                          ⚠️ Smart Contract execution is NOT authoritative until cleared.
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ) : !legalWrapper.supremacyEnabled ? (
                  // Supremacy Disabled
                  <Card className="bg-slate-800/30 border-slate-700">
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-amber-400" />
                        <CardTitle className="text-sm">⚠️ Code–Prose Parity (Digital Supremacy Off)</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2 text-sm text-slate-300">
                        <p>
                          This instrument does <span className="font-bold text-amber-300">NOT</span> prioritize
                          executable code over contract text.
                        </p>
                        <p className="text-xs text-amber-400 font-medium">
                          ⚠️ This asset is LESS bankable.
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  // Digital Supremacy Enabled
                  <Card className="bg-slate-800/30 border-purple-700">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Zap className="h-5 w-5 text-purple-400" />
                          <CardTitle className="text-sm text-purple-300">✔ Digital Supremacy Enabled</CardTitle>
                        </div>
                        <span className="px-2 py-1 bg-purple-900/50 text-purple-300 text-xs font-bold rounded border border-purple-700/50">
                          CODE PREVAILS
                        </span>
                      </div>
                      <CardDescription className="text-xs text-slate-400 mt-1">
                        Smart Contract execution overrides PDF contract text
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      {legalWrapper.ricardianMetadata?.digitalSupremacy ? (
                        <>
                          {/* Supremacy Details */}
                          <div className="grid grid-cols-2 gap-3 pb-3 border-b border-slate-700">
                            <div>
                              <div className="text-xs text-slate-400 mb-1">Legal Framework</div>
                              <div className="space-y-1">
                                <div className="flex items-center gap-1.5 text-emerald-300">
                                  <span className="text-lg">✔</span>
                                  <span className="text-xs font-medium">
                                    {legalWrapper.ricardianMetadata.digitalSupremacy.uccReference}
                                  </span>
                                </div>
                                {legalWrapper.ricardianMetadata.digitalSupremacy.ukEtda2023 && (
                                  <div className="flex items-center gap-1.5 text-emerald-300">
                                    <span className="text-lg">✔</span>
                                    <span className="text-xs font-medium">UK ETDA 2023</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-400 mb-1">Precedence</div>
                              <div className="text-purple-300 font-semibold">
                                {legalWrapper.ricardianMetadata.digitalSupremacy.precedence.replace(/_/g, " ").toUpperCase()}
                              </div>
                            </div>
                          </div>

                          {/* Hash Binding */}
                          <div className="pb-3 border-b border-slate-700">
                            <div className="text-xs text-slate-400 mb-2">📎 Hash Binding</div>
                            <div className="flex items-center justify-between gap-2 p-2 bg-slate-900/50 rounded">
                              <div className="font-mono text-xs text-slate-300">
                                {legalWrapper.ricardianMetadata.digitalSupremacy.hashBinding.slice(0, 16)}...
                                {legalWrapper.ricardianMetadata.digitalSupremacy.hashBinding.slice(-8)}
                              </div>
                              <button
                                onClick={() => navigator.clipboard.writeText(legalWrapper.ricardianMetadata!.digitalSupremacy!.hashBinding)}
                                className="p-1.5 hover:bg-slate-700 rounded transition-colors"
                                title="Copy hash binding"
                              >
                                <Copy className="h-3.5 w-3.5 text-slate-400" />
                              </button>
                            </div>
                          </div>

                          {/* Kill Switch */}
                          {legalWrapper.ricardianMetadata.digitalSupremacy.killSwitch.enabled && (
                            <div>
                              <div className="text-xs text-slate-400 mb-2">⚙️ Kill Switch Conditions</div>
                              <div className="space-y-1.5">
                                {legalWrapper.ricardianMetadata.digitalSupremacy.killSwitch.conditions.map((condition, idx) => (
                                  <div
                                    key={idx}
                                    className="flex items-start gap-2 p-2 bg-slate-900/50 border border-slate-700 rounded text-xs text-slate-300"
                                  >
                                    <span className="text-amber-400 font-bold mt-0.5">⚠</span>
                                    <span>{condition}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        // Supremacy enabled but no metadata
                        <div className="text-xs text-slate-400 py-2">
                          Digital Supremacy is enabled. Detailed metadata pending backend sync.
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Financing Capacity Section - FINANCE-R01 */}
                {!legalWrapper || legalWrapper.status !== "ACTIVE" ? (
                  // Non-financeable state (no wrapper or FROZEN/TERMINATED)
                  <Card className="bg-slate-800/30 border-slate-700">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Shield className="h-4 w-4 text-slate-500" />
                        Financing Capacity
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-start gap-2 text-slate-400 text-xs p-3 bg-slate-900/30 border border-slate-700 rounded">
                        <AlertTriangle className="h-4 w-4 text-slate-500 mt-0.5 flex-shrink-0" />
                        <p>
                          This shipment is not financeable. Ricardian legal wrapper must be{" "}
                          <span className="font-semibold text-emerald-400">ACTIVE</span> to enable financing.
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  // Financeable state - show quote + stakes
                  <>
                    {/* Financing Quote Card */}
                    {notionalValue <= 0 ? (
                      // CASE B: ACTIVE wrapper but no notional value
                      <Card className="bg-slate-800/30 border-slate-700">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Shield className="h-4 w-4 text-slate-500" />
                            Financing Capacity
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-start gap-2 text-amber-400 text-xs p-3 bg-amber-950/20 border border-amber-700/50 rounded">
                            <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                            <p>
                              Financing capacity unavailable – no notional value provided.
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    ) : financeLoading ? (
                      <Skeleton className="h-48 w-full" />
                    ) : financeError ? (
                      <Card className="bg-slate-800/30 border-slate-700">
                        <CardContent className="py-6">
                          <div className="flex items-center gap-2 text-amber-400 text-xs p-3 bg-amber-950/20 border border-amber-700/50 rounded">
                            <AlertTriangle className="h-4 w-4" />
                            <span>Financing quote unavailable.</span>
                          </div>
                        </CardContent>
                      </Card>
                    ) : financeQuote ? (
                      <Card className="bg-slate-800/30 border-slate-700">
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Shield className="h-4 w-4 text-emerald-400" />
                              Financing Capacity (Liquid BOL)
                            </CardTitle>
                            <span className="px-2 py-1 bg-emerald-900/50 text-emerald-300 text-xs font-bold rounded border border-emerald-700/50">
                              FINANCEABLE
                            </span>
                          </div>
                          <CardDescription className="text-xs text-slate-400 mt-1">
                            Real-time quote based on Ricardian wrapper and risk profile
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3 text-sm">
                          {/* Notional Value & Max Advance */}
                          <div className="grid grid-cols-2 gap-3 pb-3 border-b border-slate-700">
                            <div>
                              <div className="text-xs text-slate-400 mb-1">Notional Value</div>
                              <div className="font-mono text-lg font-bold text-slate-100">
                                {financeQuote.notional_value} {financeQuote.currency}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-400 mb-1">Max Advance Available</div>
                              <div className="font-mono text-lg font-bold text-emerald-300">
                                ${financeQuote.max_advance_amount}
                              </div>
                              <div className="text-xs text-slate-500 mt-0.5">
                                ({financeQuote.max_advance_rate}% LTV)
                              </div>
                            </div>
                          </div>

                          {/* APR Breakdown */}
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <div className="text-xs text-slate-400 mb-1">Base APR</div>
                              <div className="font-mono text-sm text-slate-200">
                                {financeQuote.base_apr}%
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-slate-400 mb-1">Risk-Adjusted APR</div>
                              <div className="font-mono text-sm font-semibold text-amber-300">
                                {financeQuote.risk_adjusted_apr}%
                              </div>
                            </div>
                          </div>

                          {/* Reason Codes */}
                          {financeQuote.reasonCodes && financeQuote.reasonCodes.length > 0 && (
                            <div className="pt-3 border-t border-slate-700">
                              <div className="text-xs text-slate-400 mb-2">Risk Factors</div>
                              <div className="flex flex-wrap gap-1.5">
                                {financeQuote.reasonCodes.map((code, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-1 bg-amber-900/30 text-amber-200 text-xs rounded border border-amber-700/50"
                                  >
                                    {code}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Request Financing Button (Coming Soon) */}
                          <div className="pt-3">
                            <button
                              onClick={() => {
                                // Toast equivalent - just an alert for now since toast isn't imported
                                alert("Request Financing feature coming soon in FINANCE-R02!");
                              }}
                              disabled
                              className="w-full px-4 py-2.5 bg-slate-700 text-slate-400 text-sm font-medium rounded border border-slate-600 cursor-not-allowed opacity-60"
                            >
                              Request Financing (Coming Soon)
                            </button>
                          </div>
                        </CardContent>
                      </Card>
                    ) : null}

                    {/* Inventory Stakes Section */}
                    <Card className="bg-slate-800/30 border-slate-700">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Existing Inventory Stakes</CardTitle>
                        <CardDescription className="text-xs text-slate-400">
                          Active and historical financing positions
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        {stakesLoading ? (
                          <Skeleton className="h-24 w-full" />
                        ) : stakesError ? (
                          <p className="text-slate-500 text-xs py-4 text-center">
                            Unable to load stakes.
                          </p>
                        ) : stakes && stakes.length > 0 ? (
                          <div className="space-y-2">
                            {stakes.map((stake) => (
                              <div
                                key={stake.id}
                                className="p-3 bg-slate-900/50 border border-slate-700 rounded space-y-2"
                              >
                                {/* Status & Principal */}
                                <div className="flex items-center justify-between">
                                  <span
                                    className={classNames(
                                      "px-2 py-1 rounded text-xs font-bold",
                                      stake.status === "ACTIVE"
                                        ? "bg-emerald-900/50 text-emerald-300 border border-emerald-700/50"
                                        : stake.status === "REPAID"
                                        ? "bg-slate-700 text-slate-300 border border-slate-600"
                                        : stake.status === "LIQUIDATED"
                                        ? "bg-rose-900/50 text-rose-300 border border-rose-700/50"
                                        : "bg-slate-700 text-slate-400 border border-slate-600"
                                    )}
                                  >
                                    {stake.status}
                                  </span>
                                  <div className="font-mono text-sm font-bold text-slate-200">
                                    {stake.principal_amount} {stake.currency}
                                  </div>
                                </div>

                                {/* Details Grid */}
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div>
                                    <div className="text-slate-500">APR</div>
                                    <div className="text-slate-300 font-mono">
                                      {stake.risk_adjusted_apr}%
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-slate-500">Created</div>
                                    <div className="text-slate-300">
                                      {new Date(stake.createdAt).toLocaleDateString()}
                                    </div>
                                  </div>
                                  {stake.repaid_at && (
                                    <div>
                                      <div className="text-slate-500">Repaid</div>
                                      <div className="text-slate-300">
                                        {new Date(stake.repaid_at).toLocaleDateString()}
                                      </div>
                                    </div>
                                  )}
                                  {stake.liquidated_at && (
                                    <div>
                                      <div className="text-slate-500">Liquidated</div>
                                      <div className="text-rose-300">
                                        {new Date(stake.liquidated_at).toLocaleDateString()}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-slate-500 text-xs py-4 text-center">
                            No active or historical stakes.
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {/* Audit Tab */}
        {activeTab === "audit" && (
          <>
            {auditLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <div className="grid grid-cols-2 gap-3">
                  <Skeleton className="h-32 w-full" />
                  <Skeleton className="h-32 w-full" />
                  <Skeleton className="h-32 w-full" />
                  <Skeleton className="h-32 w-full" />
                </div>
                <Skeleton className="h-24 w-full" />
              </div>
            ) : auditError ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <AlertTriangle className="h-12 w-12 mb-3 opacity-50" />
                <p className="font-medium">Unable to load AuditPack</p>
                <p className="text-xs mt-1">for this settlement</p>
              </div>
            ) : auditPack ? (
              <AuditPackView audit={auditPack} reconciliation={recon} />
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
