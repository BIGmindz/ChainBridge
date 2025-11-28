import { X } from "lucide-react";
import { useEffect, useState } from "react";

import { FEATURES } from "../config/env";
import { useDemo } from "../core/demo/DemoContext";
import { useShipmentIoT } from "../hooks/useIoTShipmentSnapshot";
import { usePaymentQueue } from "../hooks/usePaymentQueue";
import { useRiskStories } from "../hooks/useRiskStories";
import { useShipmentAlerts } from "../hooks/useShipmentAlerts";
import { getProofPack, type ProofPackResponse } from "../lib/apiClient";
import {
    calculatePaymentProgress,
    formatRiskScore,
    formatUSD,
} from "../lib/formatters";
import type { Shipment } from "../lib/types";
import { shipmentsClient } from "../services/shipmentsClient";


import type { ShipmentChainStripProps } from "./intel/ShipmentChainStrip";
import ShipmentChainStrip from "./intel/ShipmentChainStrip";
import { ShipmentEventTimeline } from "./oc/ShipmentEventTimeline";

interface ShipmentDetailDrawerProps {
  shipmentId: string;
  onClose: () => void;
}

const CAN_FETCH_PROOFPACK = Boolean(import.meta.env.VITE_API_BASE_URL);

/**
 * Map shipment status to value chain stage
 */
function mapStatusToChainStage(status: Shipment["status"]): ShipmentChainStripProps["currentStage"] {
  // TODO: Enhance this mapping as more granular status values become available
  switch (status) {
    case "pickup":
      return "pickup";
    case "in_transit":
      return "in_transit";
    case "delivery":
      return "warehouse"; // Assuming delivery means at warehouse
    case "completed":
      return "delivered";
    case "delayed":
    case "blocked":
      // For delayed/blocked, infer from other context if possible
      // For now, default to in_transit as a conservative guess
      return "in_transit";
    default:
      return "booking";
  }
}

/**
 * Shipment Detail Drawer Component
 * Shows full shipment details, risk, payment, and proof data
 */
export default function ShipmentDetailDrawer({
  shipmentId,
  onClose,
}: ShipmentDetailDrawerProps): JSX.Element {
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [proofData, setProofData] = useState<ProofPackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [proofLoading, setProofLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [proofError, setProofError] = useState<string | null>(null);
  const [showProof, setShowProof] = useState(false);

  // Demo mode highlight key
  const { state: demoState } = useDemo();
  const highlightKey = demoState.currentStep?.highlightKey;

  // Unified intelligence hooks
  const { data: riskStories } = useRiskStories(50);
  const { data: payQueue } = usePaymentQueue(50);
  const { snapshot: iotSnapshot, loading: iotLoading } = useShipmentIoT(shipment?.id ?? null);

  const { alertsForShipment, loading: shipmentAlertsLoading } = useShipmentAlerts(
    shipment?.reference
  );

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);
    setProofError(null);

    shipmentsClient
      .getShipmentById(shipmentId)
      .then((data) => {
        if (!isMounted) return;
        setShipment(data);

        if (!CAN_FETCH_PROOFPACK) {
          setProofError("ProofPack API base URL not configured.");
          return;
        }

        setProofLoading(true);
        getProofPack(data.id)
          .then((proof) => {
            if (!isMounted) return;
            setProofData(proof);
          })
          .catch((err) => {
            console.error("Failed to load proof pack:", err);
            if (!isMounted) return;
            setProofError("Unable to load ProofPack snapshot.");
          })
          .finally(() => {
            if (!isMounted) return;
            setProofLoading(false);
          });
      })
      .catch((err) => {
        console.error("Failed to load shipment:", err);
        if (!isMounted) return;
        setError("Shipment not found");
      })
      .finally(() => {
        if (!isMounted) return;
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [shipmentId]);

  if (loading) {
    return (
      <div className="card p-8 text-center">
        <div className="inline-block w-6 h-6 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!shipment) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500">{error ?? "Shipment not found"}</p>
        <button
          onClick={onClose}
          className="mt-4 px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          Close
        </button>
      </div>
    );
  }

  const paymentProgress = calculatePaymentProgress(shipment);
  const clampedPaymentProgress = Math.min(100, Math.max(0, paymentProgress));
  const recommendedRiskAction = getRiskRecommendation(shipment.risk.category);
  const proofFallback = buildProofFallback(shipment);

  // Find intelligence for this shipment
  const story = riskStories?.stories.find(
    (s) => s.shipmentId === shipment.id || s.reference === shipment.reference,
  );
  const payItem = payQueue?.items.find(
    (item) => item.shipmentId === shipment.id || item.reference === shipment.reference,
  );

  return (
    <div className="card overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
        <h3 className="font-semibold text-gray-900">{shipment.id}</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
          aria-label="Close"
        >
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {/* Value Chain Progress */}
        <ShipmentChainStrip
          shipmentRef={shipment.reference}
          currentStage={mapStatusToChainStage(shipment.status)}
          riskScore={shipment.risk.score}
          blockedCapital={shipment.payment.holds_usd}
        />

        {/* Basic Info */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Shipment Details</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-600">Carrier</p>
              <p className="font-medium text-gray-900">{shipment.carrier}</p>
            </div>
            <div>
              <p className="text-gray-600">Customer</p>
              <p className="font-medium text-gray-900">{shipment.customer}</p>
            </div>
            <div className="col-span-2">
              <p className="text-gray-600">Corridor</p>
              <p className="font-medium text-gray-900">
                {shipment.corridor}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Value</p>
              <p className="font-medium text-gray-900">
                {formatUSD(shipment.payment.total_valueUsd)}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Status</p>
              <p className="font-medium text-gray-900 capitalize">
                {shipment.status}
              </p>
            </div>
          </div>
        </div>

        {/* Unified Intelligence - Risk + Payment + IoT */}
        {FEATURES.shipmentIntelligence && (
          <div
            className={`space-y-4 ${
              highlightKey === "intel_panel" ? "ring-2 ring-emerald-400 rounded-lg p-2" : ""
            }`}
          >
            <h4 className="font-semibold text-gray-900">Control Tower Intelligence</h4>

            {/* Risk Story */}
            {story && (
              <div className="border border-orange-200 rounded-lg p-4 bg-orange-50/50">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-orange-700 uppercase">ChainIQ Risk</span>
                  <span className="text-xs bg-orange-200 text-orange-800 px-2 py-0.5 rounded">
                    Score: {story.score}
                  </span>
                </div>
                <p className="text-sm text-gray-700 mb-2">{story.summary}</p>
                <p className="text-xs text-blue-600 font-medium">→ {story.recommended_action}</p>
              </div>
            )}

            {/* Payment Intelligence */}
            {payItem && (
              <div className="border border-red-200 rounded-lg p-4 bg-red-50/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-red-700 uppercase">ChainPay Holds</span>
                  <span className="text-sm font-bold text-red-700">{formatUSD(parseFloat(payItem.holds_usd.toString()))}</span>
                </div>
                <div className="text-xs text-gray-600 space-y-1">
                  <p>Released: {formatUSD(parseFloat(payItem.released_usd.toString()))}</p>
                  <p>Aging: {payItem.aging_days} days</p>
                </div>
              </div>
            )}

            {/* IoT Intelligence */}
            {iotLoading ? (
              <div className="border border-blue-200 rounded-lg p-4 bg-blue-50/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-blue-700 uppercase">ChainSense IoT</span>
                  <span className="text-sm text-blue-600">Loading...</span>
                </div>
              </div>
            ) : iotSnapshot ? (
              <div className="border border-blue-200 rounded-lg p-4 bg-blue-50/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-blue-700 uppercase">ChainSense IoT</span>
                  <span className={`text-sm font-medium ${iotSnapshot.critical_alerts_24h > 0 ? 'text-rose-600' : iotSnapshot.alert_count_24h > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {iotSnapshot.latest_readings.length} Sensors Active
                  </span>
                </div>
                <div className="text-xs text-gray-600 space-y-1">
                  {iotSnapshot.latest_readings.length > 0 && (
                    <div className="mb-2">
                      <p className="font-semibold text-gray-700 mb-1">Latest Readings:</p>
                      {iotSnapshot.latest_readings.slice(0, 3).map((reading, idx) => (
                        <p key={idx} className="text-[11px]">
                          <span className="font-medium capitalize">{reading.sensor_type}</span>: {reading.value}
                          {reading.unit && ` ${reading.unit}`}
                          {reading.status === 'critical' && <span className="ml-1 text-rose-600 font-semibold">⚠ Critical</span>}
                          {reading.status === 'warn' && <span className="ml-1 text-amber-600">⚠ Warning</span>}
                        </p>
                      ))}
                    </div>
                  )}
                  <p>Alerts (24h): <span className="font-medium">{iotSnapshot.alert_count_24h}</span></p>
                  {iotSnapshot.critical_alerts_24h > 0 && (
                    <p className="text-rose-600 font-semibold">
                      Critical Alerts: {iotSnapshot.critical_alerts_24h}
                    </p>
                  )}
                  <p className="text-[10px] text-gray-500 mt-2">
                    Last update: {new Date(iotSnapshot.latest_readings[0]?.timestamp || new Date()).toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase">ChainSense IoT</span>
                  <span className="text-sm text-slate-400">No IoT Data</span>
                </div>
                <p className="text-xs text-gray-500">No IoT sensors registered for this shipment.</p>
              </div>
            )}

            {/* Shipment Alerts */}
            <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-700 uppercase">
                  Alerts for this shipment
                </span>
                {shipmentAlertsLoading && (
                  <span className="text-[10px] text-slate-400">Loading…</span>
                )}
              </div>

              {(!alertsForShipment || alertsForShipment.length === 0) &&
                !shipmentAlertsLoading && (
                  <p className="text-xs text-slate-500">
                    No active alerts for this shipment.
                  </p>
                )}

              {alertsForShipment && alertsForShipment.length > 0 && (
                <ul className="space-y-2">
                  {alertsForShipment.slice(0, 3).map((alert) => (
                    <li key={alert.id} className="text-xs text-gray-700">
                      <span className="font-semibold text-gray-900">
                        {alert.source.toUpperCase()}
                      </span>
                      {": "}
                      {alert.title}
                      {alert.severity === "critical" && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-semibold text-rose-700">
                          CRITICAL
                        </span>
                      )}
                    </li>
                  ))}
                  {alertsForShipment.length > 3 && (
                    <li className="text-xs text-slate-500 italic">
                      +{alertsForShipment.length - 3} more alerts
                    </li>
                  )}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* Lifecycle Timeline */}
        <div
          className={highlightKey === "timeline" ? "ring-2 ring-emerald-400 rounded-lg p-2" : ""}
        >
          <h4 className="font-semibold text-gray-900 mb-3">Shipment Timeline</h4>
          <ShipmentEventTimeline shipmentId={shipment?.reference ?? ""} />
        </div>

        {/* Risk */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Risk Assessment</h4>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Risk Score</span>
              <span
                className={`px-3 py-1 rounded-full font-semibold text-sm ${
                  formatRiskScore(shipment.risk.score).bgColor
                } ${formatRiskScore(shipment.risk.score).color}`}
              >
                {shipment.risk.score}
              </span>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Recommended Action</p>
              <p className="font-medium text-gray-900">{recommendedRiskAction}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Last Assessed</p>
              <p className="font-medium text-gray-900">
                {new Date(shipment.risk.assessed_at).toLocaleString()}
              </p>
            </div>
            {shipment.risk.drivers.length > 0 && (
              <div>
                <p className="text-gray-600 text-sm">Drivers</p>
                <p className="font-medium text-gray-900">
                  {shipment.risk.drivers.join(", ")}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Payment */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">
            Smart Settlements
            <span className="ml-2 text-xs font-normal text-gray-500">
              Real-time milestone tracking
            </span>
          </h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-gray-600">Progress</span>
                <span className="text-sm font-semibold text-gray-900">
                  {Math.round(paymentProgress)}%
                </span>
              </div>
              <svg
                className="h-2 w-full"
                viewBox="0 0 100 4"
                preserveAspectRatio="none"
                role="img"
                aria-label={`Payment progress ${Math.round(paymentProgress)} percent`}
              >
                <rect x="0" y="0" width="100" height="4" rx="2" fill="rgb(229,231,235)" />
                <rect
                  x="0"
                  y="0"
                  width={clampedPaymentProgress}
                  height="4"
                  rx="2"
                  fill="rgb(34,197,94)"
                />
              </svg>
            </div>

            {/* Enhanced milestone states with Smart Settlements support */}
            {shipment.payment.milestones.map((milestone) => {
              // Map milestone states to visual styles
              const getStateStyle = (state: string) => {
                const normalizedState = state.toLowerCase();
                if (normalizedState === "released" || normalizedState === "approved" || normalizedState === "settled") {
                  return "bg-success-100 text-success-700";
                } else if (normalizedState === "blocked" || normalizedState === "rejected") {
                  return "bg-danger-100 text-danger-700";
                } else if (normalizedState === "eligible" || normalizedState === "delayed") {
                  return "bg-warning-100 text-warning-700";
                } else {
                  return "bg-gray-100 text-gray-700";
                }
              };

              return (
                <div
                  key={milestone.label}
                  className="flex items-center justify-between py-2 border-t border-gray-100"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {milestone.label}
                    </p>
                    <p className="text-xs text-gray-600">{milestone.percentage}%</p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs rounded font-semibold ${getStateStyle(milestone.state)}`}
                  >
                    {milestone.state}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Proof */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Governance & Audit</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Proofpack Status</span>
                  <span className="font-semibold">
                    {shipment.governance.proofpack_status}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Last Audit</span>
                  <span className="text-gray-900">
                    {new Date(shipment.governance.last_audit).toLocaleString()}
              </span>
            </div>
            {shipment.governance.exceptions.length > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-600">Exceptions</span>
                <span className="font-medium text-gray-900">
                  {shipment.governance.exceptions.join(", ")}
                </span>
              </div>
            )}

            {proofLoading ? (
              <div className="text-center py-4">
                <div className="inline-block w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
              </div>
            ) : proofData ? (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-600">Version</span>
                  <span className="font-mono text-gray-900">
                    {proofData.version}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Generated</span>
                  <span className="text-gray-900">
                    {new Date(proofData.generatedAt).toLocaleString()}
                  </span>
                </div>
                {proofData.risk_snapshot && (
                  <div className="flex flex-col gap-1 rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
                    <div className="flex justify-between">
                      <span>Risk Score</span>
                      <span>{proofData.risk_snapshot.riskScore}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Severity</span>
                      <span>{proofData.risk_snapshot.severity}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Action</span>
                      <span>{proofData.risk_snapshot.recommended_action}</span>
                    </div>
                  </div>
                )}
                <button
                  onClick={() => setShowProof(!showProof)}
                  className="mt-2 text-primary-600 hover:text-primary-700 font-medium text-sm"
                >
                  {showProof ? "Hide" : "View"} Proof Snapshot
                </button>
                {showProof && (
                  <pre className="mt-3 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-48 text-gray-700">
                    {JSON.stringify(proofData, null, 2)}
                  </pre>
                )}
              </>
            ) : (
              <>
                <p className="text-xs text-gray-500">
                  {proofError ?? "ProofPack snapshot unavailable. Showing governance metadata."}
                </p>
                <button
                  onClick={() => setShowProof(!showProof)}
                  className="mt-2 text-primary-600 hover:text-primary-700 font-medium text-sm"
                >
                  {showProof ? "Hide" : "View"} Governance Snapshot
                </button>
                {showProof && (
                  <pre className="mt-3 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-48 text-gray-700">
                    {JSON.stringify(proofFallback, null, 2)}
                  </pre>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function getRiskRecommendation(category: Shipment["risk"]["category"]): string {
  switch (category) {
    case "high":
      return "Hold for manual review";
    case "medium":
      return "Monitor closely";
    default:
      return "Proceed normally";
  }
}

function buildProofFallback(shipment: Shipment): Record<string, unknown> {
  return {
    shipmentId: shipment.id,
    governance: shipment.governance,
    payment: shipment.payment,
    freight_events: shipment.freight.events,
  };
}
