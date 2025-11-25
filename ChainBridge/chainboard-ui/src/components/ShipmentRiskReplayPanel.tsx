import { useState } from 'react';

import { replayRisk, type ReplayResponse } from '../lib/apiClient';

/**
 * ShipmentRiskReplayPanel.tsx
 *
 * Business Purpose: Deterministic replay verification
 *
 * Enables operators to:
 * - Verify scoring algorithm consistency
 * - Audit historical risk decisions
 * - Detect algorithm drift or changes
 *
 * Shows BEFORE vs AFTER comparison with match indicator.
 */

export function ShipmentRiskReplayPanel() {
  const [shipmentId, setShipmentId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReplayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReplay = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!shipmentId.trim()) {
      setError('Shipment ID is required');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await replayRisk(shipmentId);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Replay failed');
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

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 shadow-xl">
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-white mb-1">Risk Score Replay</h3>
        <p className="text-sm text-gray-400">
          Deterministically replay past risk decisions for audit verification
        </p>
      </div>

      <form onSubmit={handleReplay} className="mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={shipmentId}
            onChange={(e) => setShipmentId(e.target.value)}
            placeholder="Enter Shipment ID (e.g., SHP-1001)"
            className="flex-1 px-4 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !shipmentId.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded transition-colors"
          >
            {loading ? 'Replaying...' : 'Replay Score'}
          </button>
        </div>
      </form>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded">
          <p className="text-red-400 text-sm font-medium">Error</p>
          <p className="text-red-300 text-sm mt-1">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Match Status Banner */}
          <div className={`p-4 rounded border ${
            result.match
              ? 'bg-green-500/10 border-green-500/30'
              : 'bg-yellow-500/10 border-yellow-500/30'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`font-semibold ${result.match ? 'text-green-400' : 'text-yellow-400'}`}>
                  {result.match ? '✓ Scores Match' : '⚠ Scores Differ'}
                </p>
                <p className={`text-sm mt-1 ${result.match ? 'text-green-300' : 'text-yellow-300'}`}>
                  {result.match
                    ? 'Algorithm is deterministic - original score reproduced exactly'
                    : 'Algorithm has changed since original scoring'
                  }
                </p>
              </div>
              <span className="text-2xl">
                {result.match ? '✓' : '⚠'}
              </span>
            </div>
          </div>

          {/* Before vs After Comparison */}
          <div className="grid grid-cols-2 gap-6">
            {/* Original Score */}
            <div className="border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                  Original Score
                </h4>
                <span className="text-xs text-gray-500">
                  {new Date(result.original_scored_at).toLocaleDateString()}
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Risk Score</p>
                  <p className="text-3xl font-bold text-white">{result.original_score}</p>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-1">Severity</p>
                  <span className={`inline-block px-3 py-1 rounded border text-sm font-medium ${getSeverityColor(result.original_severity)}`}>
                    {result.original_severity}
                  </span>
                </div>
              </div>
            </div>

            {/* Replayed Score */}
            <div className="border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                  Replayed Score
                </h4>
                <span className="text-xs text-gray-500">Just now</span>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Risk Score</p>
                  <p className="text-3xl font-bold text-white">{result.replayed_score}</p>
                </div>

                <div>
                  <p className="text-xs text-gray-500 mb-1">Severity</p>
                  <span className={`inline-block px-3 py-1 rounded border text-sm font-medium ${getSeverityColor(result.replayed_severity)}`}>
                    {result.replayed_severity}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Replayed Details */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
              Replayed Decision Details
            </h4>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500 mb-1">Recommended Action</p>
                <p className="text-base font-medium text-white">
                  {result.replayed_action.replace(/_/g, ' ')}
                </p>
              </div>

              {result.replayed_reasonCodes.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Reason Codes</p>
                  <div className="flex flex-wrap gap-2">
                    {result.replayed_reasonCodes.map((code, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs font-mono text-gray-300"
                      >
                        {code}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {!result && !error && (
        <div className="text-center py-8 text-gray-500 text-sm">
          Enter a shipment ID to replay its risk score calculation
        </div>
      )}
    </div>
  );
}
