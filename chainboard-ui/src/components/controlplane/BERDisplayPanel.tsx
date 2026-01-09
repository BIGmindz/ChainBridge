/**
 * BER Display Panel — Control Plane UI
 * PAC-CP-UI-EXEC-001: ORDER 5 — BER Read-Only Rendering
 *
 * Displays BER (Benson Execution Report) status in read-only mode.
 *
 * INVARIANTS:
 * - INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
 * - BER is read-only in the Control Plane UI
 * - All BER states are deterministic
 *
 * Author: Benson Execution Orchestrator (GID-00)
 */

import React from 'react';
import {
  ControlPlaneStateDTO,
  BERRecordDTO,
  BERState,
  BER_STATE_CONFIG,
  formatTimestamp,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// BER STATE BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface BERStateBadgeProps {
  state: BERState;
  size?: 'sm' | 'md' | 'lg';
}

export const BERStateBadge: React.FC<BERStateBadgeProps> = ({
  state,
  size = 'md',
}) => {
  const config = BER_STATE_CONFIG[state];
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.bgColor} ${config.color} ${sizeClasses[size]}`}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// BER ELIGIBILITY CHECKER
// ═══════════════════════════════════════════════════════════════════════════════

interface BERPrerequisitesProps {
  state: ControlPlaneStateDTO;
}

export const BERPrerequisites: React.FC<BERPrerequisitesProps> = ({ state }) => {
  // Check prerequisites
  const allACKsReceived = state.ack_summary.acknowledged === state.ack_summary.total && 
                          state.ack_summary.total > 0;
  const noRejectedACKs = state.ack_summary.rejected === 0;
  const noTimeoutACKs = state.ack_summary.timeout === 0;
  const hasValidWRAP = Object.values(state.wraps).some(w => w.validation_state === 'VALID');
  const noInvalidWRAPs = !Object.values(state.wraps).some(w => 
    ['INVALID', 'SCHEMA_ERROR', 'MISSING_ACK'].includes(w.validation_state)
  );

  const prerequisites = [
    {
      label: 'All ACKs Received',
      passed: allACKsReceived,
      critical: true,
      detail: `${state.ack_summary.acknowledged}/${state.ack_summary.total} agents acknowledged`,
    },
    {
      label: 'No Rejected ACKs',
      passed: noRejectedACKs,
      critical: true,
      detail: state.ack_summary.rejected > 0 
        ? `${state.ack_summary.rejected} agent(s) rejected` 
        : 'All agents cooperating',
    },
    {
      label: 'No Timeout ACKs',
      passed: noTimeoutACKs,
      critical: true,
      detail: state.ack_summary.timeout > 0
        ? `${state.ack_summary.timeout} agent(s) timed out`
        : 'All agents responded in time',
    },
    {
      label: 'Valid WRAP Submitted',
      passed: hasValidWRAP,
      critical: true,
      detail: hasValidWRAP ? 'WRAP validated successfully' : 'Awaiting valid WRAP',
    },
    {
      label: 'No Invalid WRAPs',
      passed: noInvalidWRAPs,
      critical: true,
      detail: noInvalidWRAPs ? 'No validation failures' : 'WRAP validation failed',
    },
  ];

  const allPassed = prerequisites.every(p => p.passed);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className={allPassed ? 'text-green-400' : 'text-yellow-400'}>
          {allPassed ? '✅' : '⏳'}
        </span>
        <span className="text-sm font-medium text-gray-200">
          BER Prerequisites {allPassed ? 'Met' : 'Pending'}
        </span>
      </div>
      
      <div className="space-y-2">
        {prerequisites.map((prereq, idx) => (
          <div
            key={idx}
            className={`flex items-center justify-between p-2 rounded ${
              prereq.passed 
                ? 'bg-green-900/20 border border-green-800/50' 
                : prereq.critical 
                  ? 'bg-red-900/20 border border-red-800/50'
                  : 'bg-yellow-900/20 border border-yellow-800/50'
            }`}
          >
            <div className="flex items-center gap-2">
              <span>{prereq.passed ? '✅' : prereq.critical ? '❌' : '⏳'}</span>
              <span className="text-sm text-gray-200">{prereq.label}</span>
            </div>
            <span className="text-xs text-gray-400">{prereq.detail}</span>
          </div>
        ))}
      </div>

      {!allPassed && (
        <div className="mt-2 p-2 bg-yellow-900/20 rounded text-xs text-yellow-400">
          <strong>Note:</strong> BER cannot be issued until all prerequisites are met.
          No BER → No settlement (INV-CP-005).
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// BER DETAIL CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface BERDetailCardProps {
  ber: BERRecordDTO;
}

export const BERDetailCard: React.FC<BERDetailCardProps> = ({ ber }) => {
  const config = BER_STATE_CONFIG[ber.state];
  const isIssued = ber.state === 'ISSUED';
  const isChallenged = ber.state === 'CHALLENGED';
  const isRevoked = ber.state === 'REVOKED';

  return (
    <div
      className={`rounded-lg border p-4 ${
        isIssued
          ? 'border-green-800 bg-green-900/10'
          : isChallenged
            ? 'border-orange-800 bg-orange-900/10'
            : isRevoked
              ? 'border-red-800 bg-red-900/10'
              : 'border-gray-700 bg-gray-800/50'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📜</span>
          <div>
            <h4 className="font-mono text-lg text-gray-200">{ber.ber_id}</h4>
            <p className="text-xs text-gray-500">Benson Execution Report</p>
          </div>
        </div>
        <BERStateBadge state={ber.state} size="lg" />
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">PAC ID</span>
          <p className="font-mono text-gray-200 truncate">{ber.pac_id}</p>
        </div>
        <div>
          <span className="text-gray-500">WRAP ID</span>
          <p className="font-mono text-gray-200 truncate">{ber.wrap_id}</p>
        </div>
        <div>
          <span className="text-gray-500">Issuer</span>
          <p className="font-mono text-gray-200">{ber.issuer_gid}</p>
        </div>
        <div>
          <span className="text-gray-500">Issued At</span>
          <p className="text-gray-200">{formatTimestamp(ber.issued_at)}</p>
        </div>
      </div>

      {/* Settlement Eligibility */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Settlement Eligible</span>
          <span className={`text-sm font-medium ${
            ber.settlement_eligible ? 'text-green-400' : 'text-red-400'
          }`}>
            {ber.settlement_eligible ? '✅ Yes' : '❌ No'}
          </span>
        </div>
      </div>

      {/* Challenged Warning */}
      {isChallenged && (
        <div className="mt-4 p-3 bg-orange-900/30 rounded text-sm text-orange-400">
          <div className="flex items-center gap-2">
            <span>⚔️</span>
            <span className="font-medium">BER Under Challenge</span>
          </div>
          <p className="mt-1 text-xs text-orange-300">
            Settlement is suspended pending challenge resolution.
          </p>
        </div>
      )}

      {/* Revoked Warning */}
      {isRevoked && (
        <div className="mt-4 p-3 bg-red-900/30 rounded text-sm text-red-400">
          <div className="flex items-center gap-2">
            <span>🗑️</span>
            <span className="font-medium">BER Revoked</span>
          </div>
          <p className="mt-1 text-xs text-red-300">
            This BER has been revoked and cannot be used for settlement.
          </p>
        </div>
      )}

      {/* Hash for audit */}
      <div className="mt-4 pt-2 border-t border-gray-700">
        <span className="text-[10px] text-gray-600 font-mono break-all">
          Hash: {ber.ber_hash}
        </span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// BER DISPLAY PANEL (MAIN COMPONENT)
// ═══════════════════════════════════════════════════════════════════════════════

interface BERDisplayPanelProps {
  state: ControlPlaneStateDTO | null;
  loading?: boolean;
  error?: string | null;
}

export const BERDisplayPanel: React.FC<BERDisplayPanelProps> = ({
  state,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-800 rounded w-1/3" />
          <div className="h-40 bg-gray-800 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg border border-red-800 p-4">
        <div className="flex items-center gap-2 text-red-400">
          <span>🛑</span>
          <span className="font-medium">BER Panel Error</span>
        </div>
        <p className="mt-2 text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-gray-500 text-center py-8">
          <span className="text-2xl">📜</span>
          <p className="mt-2">No BER data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-200">
            📜 Benson Execution Report (BER)
          </h3>
          {state.ber && (
            <BERStateBadge state={state.ber.state} size="sm" />
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {state.ber ? (
          <BERDetailCard ber={state.ber} />
        ) : (
          <div className="space-y-4">
            <div className="text-center py-4">
              <span className="text-3xl">⏳</span>
              <p className="mt-2 text-gray-400">BER Not Yet Issued</p>
              <p className="text-xs text-gray-500 mt-1">
                BER will be generated when all prerequisites are met.
              </p>
            </div>
            
            {/* Prerequisites Checklist */}
            <BERPrerequisites state={state} />
          </div>
        )}
      </div>

      {/* Read-Only Notice */}
      <div className="px-4 py-2 border-t border-gray-800 bg-gray-800/30">
        <p className="text-[10px] text-gray-600">
          🔒 READ-ONLY: BER records are immutable. 
          INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs.
        </p>
      </div>
    </div>
  );
};

export default BERDisplayPanel;
