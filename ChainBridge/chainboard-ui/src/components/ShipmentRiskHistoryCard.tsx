import { useState, useEffect } from 'react';

import { getRecentRisk, type RiskHistoryItem } from '../lib/apiClient';

/**
 * ShipmentRiskHistoryCard.tsx
 *
 * Business Purpose: Dashboard view of recent risk decisions
 *
 * Enables operators to:
 * - See recent risk scoring activity
 * - Identify patterns (clusters of high-risk shipments)
 * - Quick access to shipment IDs for investigation
 *
 * Auto-refreshes every 30s for live monitoring.
 */

export function ShipmentRiskHistoryCard() {
  const [scores, setScores] = useState<RiskHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecentScores = async () => {
    try {
      const response = await getRecentRisk(20);
      setScores(response.scores);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load risk history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentScores();

    // Auto-refresh every 30s
    const interval = setInterval(fetchRecentScores, 30000);

    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'LOW':
        return 'text-green-400 bg-green-500/10';
      case 'MEDIUM':
        return 'text-yellow-400 bg-yellow-500/10';
      case 'HIGH':
        return 'text-orange-400 bg-orange-500/10';
      case 'CRITICAL':
        return 'text-red-400 bg-red-500/10';
      default:
        return 'text-gray-400 bg-gray-500/10';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;

      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;

      return date.toLocaleDateString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 shadow-xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white mb-1">Risk Decision History</h3>
          <p className="text-sm text-gray-400">
            Recent scoring activity across all shipments
          </p>
        </div>
        <button
          onClick={fetchRecentScores}
          disabled={loading}
          className="px-3 py-1 text-sm bg-gray-800 hover:bg-gray-700 disabled:bg-gray-800 disabled:opacity-50 text-gray-300 rounded transition-colors"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {!loading && scores.length === 0 && !error && (
        <div className="text-center py-12">
          <p className="text-gray-400">No risk scores recorded yet</p>
          <p className="text-sm text-gray-500 mt-1">
            Score a shipment to see it appear here
          </p>
        </div>
      )}

      {scores.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-2 text-gray-400 font-medium">Shipment ID</th>
                <th className="text-left py-3 px-2 text-gray-400 font-medium">Score</th>
                <th className="text-left py-3 px-2 text-gray-400 font-medium">Severity</th>
                <th className="text-left py-3 px-2 text-gray-400 font-medium">Action</th>
                <th className="text-left py-3 px-2 text-gray-400 font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {scores.map((score) => (
                <tr
                  key={score.id}
                  className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors"
                >
                  <td className="py-3 px-2">
                    <span className="font-mono text-white">{score.shipmentId}</span>
                  </td>
                  <td className="py-3 px-2">
                    <span className="text-white font-semibold">{score.riskScore}</span>
                  </td>
                  <td className="py-3 px-2">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getSeverityColor(score.severity)}`}>
                      {score.severity}
                    </span>
                  </td>
                  <td className="py-3 px-2">
                    <span className="text-gray-300 text-xs">
                      {score.recommended_action.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-gray-400 text-xs">
                    {formatTimestamp(score.scored_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {scores.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <p className="text-xs text-gray-500">
            Showing {scores.length} most recent scores • Auto-refreshes every 30s
          </p>
        </div>
      )}
    </div>
  );
}
