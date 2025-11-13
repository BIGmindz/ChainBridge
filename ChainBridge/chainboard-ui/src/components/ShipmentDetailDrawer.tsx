import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { Shipment, ShipmentProofSummary } from "../types";
import { apiClient } from "../services/api";
import {
  formatRiskScore,
  formatUSD,
  calculatePaymentProgress,
} from "../utils/formatting";

interface ShipmentDetailDrawerProps {
  shipmentId: string;
  onClose: () => void;
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
  const [proofData, setProofData] = useState<ShipmentProofSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [proofLoading, setProofLoading] = useState(false);
  const [showProof, setShowProof] = useState(false);

  useEffect(() => {
    const fetch = async (): Promise<void> => {
      try {
        const data = await apiClient.getShipmentDetail(shipmentId);
        setShipment(data);

        // Fetch proof pack data if pack_id exists
        if (data && data.proofpack?.pack_id) {
          setProofLoading(true);
          try {
            const proofResponse = await apiClient.getProofPack(
              data.proofpack.pack_id
            );
            // Transform backend response to UI format
            setProofData({
              packId: proofResponse.pack_id,
              shipmentId: proofResponse.shipment_id,
              manifestHash: proofResponse.manifest_hash,
              generatedAt: proofResponse.generated_at,
              status: proofResponse.status,
              message: proofResponse.message,
              signatureStatus: proofResponse.signature_status,
              events: proofResponse.events,
            });
          } catch (error) {
            console.error("Failed to load proof pack:", error);
            // Fall back to mock data from shipment
          } finally {
            setProofLoading(false);
          }
        }
      } catch (error) {
        console.error("Failed to load shipment:", error);
      } finally {
        setLoading(false);
      }
    };

    fetch();
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
        <p className="text-gray-500">Shipment not found</p>
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

  return (
    <div className="card overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
        <h3 className="font-semibold text-gray-900">{shipment.shipment_id}</h3>
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
              <p className="text-gray-600">Lane</p>
              <p className="font-medium text-gray-900">
                {shipment.origin} → {shipment.destination}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Value</p>
              <p className="font-medium text-gray-900">
                {formatUSD(shipment.total_value_usd)}
              </p>
            </div>
            <div>
              <p className="text-gray-600">Status</p>
              <p className="font-medium text-gray-900 capitalize">
                {shipment.current_status}
              </p>
            </div>
          </div>
        </div>

        {/* Risk */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Risk Assessment</h4>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Risk Score</span>
              <span
                className={`px-3 py-1 rounded-full font-semibold text-sm ${
                  formatRiskScore(shipment.risk.risk_score).bgColor
                } ${formatRiskScore(shipment.risk.risk_score).color}`}
              >
                {shipment.risk.risk_score}
              </span>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Recommended Action</p>
              <p className="font-medium text-gray-900">
                {shipment.risk.recommended_action}
              </p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Confidence</p>
              <p className="font-medium text-gray-900">{shipment.risk.confidence}%</p>
            </div>
          </div>
        </div>

        {/* Payment */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Payment Schedule</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm text-gray-600">Progress</span>
                <span className="text-sm font-semibold text-gray-900">
                  {Math.round(paymentProgress)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-success-600 h-2 rounded-full transition-all"
                  style={{ width: `${paymentProgress}%` }}
                />
              </div>
            </div>

            {shipment.payment_schedule.map((milestone, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between py-2 border-t border-gray-100"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {milestone.milestone}
                  </p>
                  <p className="text-xs text-gray-600">{milestone.percentage}%</p>
                </div>
                <span
                  className={`px-2 py-1 text-xs rounded font-semibold ${
                    milestone.status === "released"
                      ? "bg-success-100 text-success-700"
                      : milestone.status === "blocked"
                        ? "bg-danger-100 text-danger-700"
                        : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {milestone.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Proof */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Governance & Audit</h4>
          <div className="space-y-2 text-sm">
            {proofLoading ? (
              <div className="text-center py-4">
                <div className="inline-block w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
              </div>
            ) : proofData ? (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-600">ProofPack ID</span>
                  <span className="font-mono text-gray-900">{proofData.packId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Status</span>
                  <span
                    className={`font-semibold text-sm px-2 py-1 rounded ${
                      proofData.status === "SUCCESS"
                        ? "bg-success-100 text-success-700"
                        : proofData.status === "ERROR"
                          ? "bg-danger-100 text-danger-700"
                          : "bg-warning-100 text-warning-700"
                    }`}
                  >
                    {proofData.status}
                  </span>
                </div>
                {proofData.message && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Message</span>
                    <span className="text-gray-900">{proofData.message}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-600">Generated</span>
                  <span className="text-gray-900">
                    {new Date(proofData.generatedAt).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Signature</span>
                  <span
                    className={`font-semibold ${
                      proofData.signatureStatus === "VERIFIED"
                        ? "text-success-600"
                        : proofData.signatureStatus === "FAILED"
                          ? "text-danger-600"
                          : "text-gray-600"
                    }`}
                  >
                    {proofData.signatureStatus || "PENDING"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Manifest Hash</span>
                  <span className="font-mono text-xs text-gray-900">
                    {proofData.manifestHash.substring(0, 12)}...
                  </span>
                </div>
                {proofData.events && proofData.events.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Events Recorded</span>
                    <span className="font-medium text-gray-900">
                      {proofData.events.length}
                    </span>
                  </div>
                )}
                <button
                  onClick={() => setShowProof(!showProof)}
                  className="mt-2 text-primary-600 hover:text-primary-700 font-medium text-sm"
                >
                  {showProof ? "Hide" : "View"} Full Proof
                </button>
                {showProof && (
                  <pre className="mt-3 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-48 text-gray-700">
                    {JSON.stringify(proofData, null, 2)}
                  </pre>
                )}
              </>
            ) : (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-600">ProofPack ID</span>
                  <span className="font-mono text-gray-900">
                    {shipment.proofpack.pack_id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Signature</span>
                  <span
                    className={`font-semibold ${
                      shipment.proofpack.signature_status === "VERIFIED"
                        ? "text-success-600"
                        : "text-danger-600"
                    }`}
                  >
                    {shipment.proofpack.signature_status}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  (Mock data - connect to backend for real proof data)
                </p>
                <button
                  onClick={() => setShowProof(!showProof)}
                  className="mt-2 text-primary-600 hover:text-primary-700 font-medium text-sm"
                >
                  {showProof ? "Hide" : "View"} Manifest
                </button>
                {showProof && (
                  <pre className="mt-3 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-48 text-gray-700">
                    {JSON.stringify(
                      {
                        shipment_id: shipment.shipment_id,
                        events: shipment.events,
                        risk: shipment.risk,
                        payment_schedule: shipment.payment_schedule,
                      },
                      null,
                      2
                    )}
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
