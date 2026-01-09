/**
 * Settlement Readiness Panel
 * PAC-JEFFREY-P04: Settlement Readiness Wiring · Gold Standard
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-CP-017: SettlementReadinessVerdict REQUIRED before BER FINAL
 * - INV-CP-018: Settlement eligibility is BINARY - ELIGIBLE or BLOCKED
 * - INV-CP-019: No human override on settlement verdict
 * - INV-CP-020: Verdict must be machine-computed
 * 
 * Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
 * 
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React, { useEffect, useState } from 'react';
import {
  SettlementReadinessVerdictDTO,
  BlockingReasonEvidenceDTO,
  BLOCKING_REASON_CONFIG,
  SettlementBlockingReason,
  formatTimestamp,
} from '../../types/controlPlane';

interface SettlementReadinessPanelProps {
  pacId: string;
  onRefresh?: () => void;
}

/**
 * Settlement Readiness Panel Component
 * 
 * Displays the binary settlement readiness verdict for a PAC.
 * NO UI-LEVEL LOGIC for eligibility — verdict is machine-computed.
 */
export const SettlementReadinessPanel: React.FC<SettlementReadinessPanelProps> = ({
  pacId,
  onRefresh,
}) => {
  const [verdict, setVerdict] = useState<SettlementReadinessVerdictDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVerdict();
  }, [pacId]);

  const fetchVerdict = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/oc/controlplane/settlement-readiness/${pacId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch settlement readiness: ${response.status}`);
      }
      
      const data = await response.json();
      setVerdict(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">Computing settlement readiness...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-red-700">
        <div className="text-red-400 flex items-center gap-2">
          <span>⚠️</span>
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  if (!verdict) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="text-gray-400">No verdict available</div>
      </div>
    );
  }

  const isEligible = verdict.is_eligible;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className={`px-6 py-4 ${isEligible ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{isEligible ? '✅' : '🚫'}</span>
            <div>
              <h3 className="text-lg font-semibold text-white">
                Settlement Readiness Verdict
              </h3>
              <p className="text-sm text-gray-400">
                PAC-JEFFREY-P04 · Machine-Computed · No Override
              </p>
            </div>
          </div>
          
          {/* Status Badge */}
          <div className={`px-4 py-2 rounded-lg font-bold text-lg ${
            isEligible 
              ? 'bg-green-600 text-white' 
              : 'bg-red-600 text-white'
          }`}>
            {verdict.status}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 space-y-6">
        {/* Verdict Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-700/50 rounded-lg p-4">
            <div className="text-sm text-gray-400">Status</div>
            <div className={`text-xl font-bold ${isEligible ? 'text-green-400' : 'text-red-400'}`}>
              {verdict.status}
            </div>
          </div>
          
          <div className="bg-gray-700/50 rounded-lg p-4">
            <div className="text-sm text-gray-400">Blocking Reasons</div>
            <div className={`text-xl font-bold ${
              verdict.blocking_count > 0 ? 'text-red-400' : 'text-green-400'
            }`}>
              {verdict.blocking_count}
            </div>
          </div>
          
          <div className="bg-gray-700/50 rounded-lg p-4">
            <div className="text-sm text-gray-400">Computed By</div>
            <div className="text-xl font-bold text-blue-400">
              {verdict.computation.computed_by}
            </div>
          </div>
          
          <div className="bg-gray-700/50 rounded-lg p-4">
            <div className="text-sm text-gray-400">Method</div>
            <div className="text-xl font-bold text-purple-400">
              {verdict.computation.method}
            </div>
          </div>
        </div>

        {/* Blocking Reasons (if any) */}
        {verdict.blocking_count > 0 && (
          <div>
            <h4 className="text-md font-semibold text-white mb-3 flex items-center gap-2">
              <span>⛔</span> Blocking Reasons
            </h4>
            <div className="space-y-2">
              {verdict.blocking_reasons.map((reason, index) => (
                <BlockingReasonItem key={index} reason={reason} />
              ))}
            </div>
          </div>
        )}

        {/* Source Evidence */}
        <div>
          <h4 className="text-md font-semibold text-white mb-3 flex items-center gap-2">
            <span>📋</span> Source Evidence
          </h4>
          <div className="bg-gray-700/30 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">WRAP Refs:</span>
              <span className="text-gray-200 font-mono">
                {verdict.source_evidence.wrap_refs.length > 0 
                  ? verdict.source_evidence.wrap_refs.join(', ').slice(0, 50) + '...'
                  : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">BER Ref:</span>
              <span className="text-gray-200 font-mono">
                {verdict.source_evidence.ber_ref?.slice(0, 16) || '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">RG-01 Ref:</span>
              <span className="text-gray-200 font-mono">
                {verdict.source_evidence.rg01_ref || '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">BSRG-01 Ref:</span>
              <span className="text-gray-200 font-mono">
                {verdict.source_evidence.bsrg01_ref || '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Computation Metadata */}
        <div className="bg-gray-700/30 rounded-lg p-4 text-sm">
          <div className="flex justify-between mb-2">
            <span className="text-gray-400">Computed At:</span>
            <span className="text-gray-200">
              {formatTimestamp(verdict.computation.computed_at)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Verdict Hash:</span>
            <span className="text-gray-200 font-mono text-xs">
              {verdict.verdict_hash.slice(0, 32)}...
            </span>
          </div>
        </div>

        {/* Governance Invariants Notice */}
        <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4 text-sm">
          <div className="flex items-start gap-2">
            <span>⚖️</span>
            <div>
              <div className="text-yellow-400 font-semibold mb-1">
                Governance Invariants (PAC-JEFFREY-P04)
              </div>
              <ul className="text-yellow-200/70 space-y-1">
                <li>INV-CP-017: Verdict REQUIRED before BER FINAL</li>
                <li>INV-CP-018: Settlement eligibility is BINARY</li>
                <li>INV-CP-019: No human override permitted</li>
                <li>INV-CP-020: Verdict is machine-computed</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Refresh Button */}
        <div className="flex justify-end">
          <button
            onClick={() => {
              fetchVerdict();
              onRefresh?.();
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg 
                       transition-colors flex items-center gap-2"
          >
            <span>🔄</span>
            Recompute Verdict
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * Individual blocking reason display component.
 */
const BlockingReasonItem: React.FC<{ reason: BlockingReasonEvidenceDTO }> = ({ reason }) => {
  const config = BLOCKING_REASON_CONFIG[reason.reason as SettlementBlockingReason] || {
    label: reason.reason,
    severity: 'high',
    icon: '⚠️',
    color: 'text-orange-500',
  };

  const severityColors = {
    critical: 'border-red-600 bg-red-900/20',
    high: 'border-orange-600 bg-orange-900/20',
    medium: 'border-yellow-600 bg-yellow-900/20',
  };

  return (
    <div className={`rounded-lg border p-3 ${severityColors[config.severity]}`}>
      <div className="flex items-start gap-3">
        <span className="text-xl">{config.icon}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`font-semibold ${config.color}`}>
              {config.label}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${
              config.severity === 'critical' ? 'bg-red-600' :
              config.severity === 'high' ? 'bg-orange-600' : 'bg-yellow-600'
            } text-white uppercase`}>
              {config.severity}
            </span>
          </div>
          <div className="text-sm text-gray-300 mt-1">
            {reason.description}
          </div>
          <div className="text-xs text-gray-500 mt-2 flex gap-4">
            <span>Source: {reason.source_type}</span>
            {reason.source_ref && (
              <span className="font-mono">Ref: {reason.source_ref.slice(0, 12)}...</span>
            )}
            <span>Detected: {formatTimestamp(reason.detected_at)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettlementReadinessPanel;
