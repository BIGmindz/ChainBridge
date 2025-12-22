import { useState } from 'react';

import { scoreShipment, type ShipmentRiskRequest, type ShipmentRiskResponse } from '../lib/apiClient';

/**
 * ShipmentRiskCard.tsx
 *
 * Business Decision: "Should we release payment for this shipment?"
 *
 * ChainIQ V1 - First real intelligence module for ChainBridge ecosystem.
 * Deterministic risk scoring based on:
 * - Route compliance (sanctions, high-risk jurisdictions)
 * - Carrier reliability score
 * - Shipment value relative to historical patterns
 * - Transit timing anomalies (early arrivals = fraud risk)
 * - Document completeness (customs, bills of lading)
 * - Shipper payment history
 *
 * Returns: Risk score (0-100), severity level, reason codes, recommended action.
 */

export function ShipmentRiskCard() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ShipmentRiskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [shipmentId, setShipmentId] = useState('');
  const [route, setRoute] = useState('');
  const [carrierId, setCarrierId] = useState('');
  const [shipmentValue, setShipmentValue] = useState('');
  const [daysInTransit, setDaysInTransit] = useState('');
  const [expectedDays, setExpectedDays] = useState('');
  const [docsComplete, setDocsComplete] = useState(false);
  const [paymentScore, setPaymentScore] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request: ShipmentRiskRequest = {
        shipmentId: shipmentId,
        route: route,
        carrierId: carrierId,
        shipment_valueUsd: parseFloat(shipmentValue),
        days_in_transit: parseInt(daysInTransit, 10),
        expected_days: parseInt(expectedDays, 10),
        documents_complete: docsComplete,
        shipper_payment_score: parseInt(paymentScore, 10),
      };

      const response = await scoreShipment(request);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'LOW':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'MEDIUM':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'HIGH':
        return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
      case 'CRITICAL':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      default:
        return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'RELEASE_PAYMENT':
        return 'text-green-400';
      case 'MANUAL_REVIEW':
        return 'text-yellow-400';
      case 'HOLD_PAYMENT':
        return 'text-orange-400';
      case 'ESCALATE_COMPLIANCE':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 shadow-xl">
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-white mb-1">ChainIQ Shipment Risk Scoring</h3>
        <p className="text-sm text-gray-400">
          Deterministic risk assessment for payment release decisions
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Shipment ID</label>
            <input
              type="text"
              value={shipmentId}
              onChange={(e) => setShipmentId(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., SH-2025-001"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Route</label>
            <input
              type="text"
              value={route}
              onChange={(e) => setRoute(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., CN-US, US-EU"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Carrier ID</label>
            <input
              type="text"
              value={carrierId}
              onChange={(e) => setCarrierId(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., FEDX, UPS"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Shipment Value (USD)</label>
            <input
              type="number"
              step="0.01"
              value={shipmentValue}
              onChange={(e) => setShipmentValue(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., 25000"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Days in Transit</label>
            <input
              type="number"
              value={daysInTransit}
              onChange={(e) => setDaysInTransit(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., 14"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Expected Days</label>
            <input
              type="number"
              value={expectedDays}
              onChange={(e) => setExpectedDays(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., 15"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Shipper Payment Score (0-100)</label>
            <input
              type="number"
              min="0"
              max="100"
              value={paymentScore}
              onChange={(e) => setPaymentScore(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g., 85"
            />
          </div>

          <div className="flex items-center">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={docsComplete}
                onChange={(e) => setDocsComplete(e.target.checked)}
                className="w-4 h-4 text-blue-500 bg-gray-800 border-gray-600 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-300">Documents Complete</span>
            </label>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded transition-colors"
        >
          {loading ? 'Scoring...' : 'Score Shipment'}
        </button>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded">
          <p className="text-red-400 text-sm font-medium">Error</p>
          <p className="text-red-300 text-sm mt-1">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-4 border-t border-gray-700 pt-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-400 mb-1">Shipment ID</p>
              <p className="text-lg font-mono text-white">{result.shipmentId}</p>
            </div>

            <div>
              <p className="text-sm text-gray-400 mb-1">Risk Score</p>
              <p className="text-3xl font-bold text-white">{result.riskScore}</p>
            </div>
          </div>

          <div>
            <p className="text-sm text-gray-400 mb-2">Severity</p>
            <span className={`inline-block px-4 py-2 rounded border font-medium ${getSeverityColor(result.severity)}`}>
              {result.severity}
            </span>
          </div>

          <div>
            <p className="text-sm text-gray-400 mb-2">Recommended Action</p>
            <p className={`text-lg font-semibold ${getActionColor(result.recommended_action)}`}>
              {result.recommended_action.replace(/_/g, ' ')}
            </p>
          </div>

          {result.reasonCodes.length > 0 && (
            <div>
              <p className="text-sm text-gray-400 mb-2">Reason Codes</p>
              <ul className="space-y-1">
                {result.reasonCodes.map((code, idx) => (
                  <li key={idx} className="text-sm text-gray-300 font-mono">
                    • {code}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
