/**
 * Settlement Eligibility Panel — Control Plane UI
 * PAC-CP-UI-EXEC-001: ORDER 6 — Settlement Eligibility Indicator
 *
 * Displays settlement eligibility status with blocking conditions.
 *
 * INVARIANTS:
 * - INV-CP-002: Missing ACK blocks execution AND settlement
 * - INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
 * - Settlement requires: All ACKs + Valid WRAP + Issued BER
 *
 * Author: Benson Execution Orchestrator (GID-00)
 */

import React, { useMemo } from 'react';
import {
  ControlPlaneStateDTO,
  SettlementEligibility,
  SETTLEMENT_CONFIG,
  LIFECYCLE_STATE_CONFIG,
  formatTimestamp,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT STATUS BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface SettlementStatusBadgeProps {
  eligibility: SettlementEligibility;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const SettlementStatusBadge: React.FC<SettlementStatusBadgeProps> = ({
  eligibility,
  size = 'md',
}) => {
  const config = SETTLEMENT_CONFIG[eligibility];
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
    xl: 'px-6 py-3 text-lg',
  };

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-lg font-medium ${config.bgColor} ${config.color} ${sizeClasses[size]}`}
    >
      <span className="text-xl">{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT GATE CHECKLIST
// ═══════════════════════════════════════════════════════════════════════════════

interface SettlementGate {
  id: string;
  label: string;
  passed: boolean;
  blocking: boolean;
  detail: string;
}

interface SettlementGateChecklistProps {
  gates: SettlementGate[];
}

export const SettlementGateChecklist: React.FC<SettlementGateChecklistProps> = ({
  gates,
}) => {
  const passedCount = gates.filter(g => g.passed).length;
  const totalCount = gates.length;

  return (
    <div className="space-y-3">
      {/* Progress indicator */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">Settlement Gates</span>
        <span className={passedCount === totalCount ? 'text-green-400' : 'text-yellow-400'}>
          {passedCount}/{totalCount} Passed
        </span>
      </div>
      
      {/* Gate list */}
      <div className="space-y-2">
        {gates.map((gate) => (
          <div
            key={gate.id}
            className={`flex items-center gap-3 p-3 rounded-lg border ${
              gate.passed
                ? 'bg-green-900/10 border-green-800/50'
                : gate.blocking
                  ? 'bg-red-900/10 border-red-800/50'
                  : 'bg-gray-800/50 border-gray-700'
            }`}
          >
            {/* Status icon */}
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              gate.passed
                ? 'bg-green-900/50 text-green-400'
                : gate.blocking
                  ? 'bg-red-900/50 text-red-400'
                  : 'bg-gray-700 text-gray-400'
            }`}>
              {gate.passed ? '✓' : gate.blocking ? '✗' : '○'}
            </div>
            
            {/* Gate info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`font-medium ${
                  gate.passed ? 'text-green-400' : gate.blocking ? 'text-red-400' : 'text-gray-300'
                }`}>
                  {gate.label}
                </span>
                {gate.blocking && !gate.passed && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-red-900/50 text-red-400 rounded">
                    BLOCKING
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-0.5">{gate.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT ELIGIBILITY PANEL (MAIN COMPONENT)
// ═══════════════════════════════════════════════════════════════════════════════

interface SettlementEligibilityPanelProps {
  state: ControlPlaneStateDTO | null;
  loading?: boolean;
  error?: string | null;
}

export const SettlementEligibilityPanel: React.FC<SettlementEligibilityPanelProps> = ({
  state,
  loading = false,
  error = null,
}) => {
  // Compute settlement gates
  const gates = useMemo<SettlementGate[]>(() => {
    if (!state) return [];

    const allACKsReceived = state.ack_summary.acknowledged === state.ack_summary.total &&
                            state.ack_summary.total > 0;
    const noRejectedACKs = state.ack_summary.rejected === 0;
    const noTimeoutACKs = state.ack_summary.timeout === 0;
    const hasValidWRAP = Object.values(state.wraps).some(w => w.validation_state === 'VALID');
    const noInvalidWRAPs = !Object.values(state.wraps).some(w =>
      ['INVALID', 'SCHEMA_ERROR', 'MISSING_ACK'].includes(w.validation_state)
    );
    const berIssued = state.ber?.state === 'ISSUED';
    const berNotChallenged = state.ber?.state !== 'CHALLENGED' && state.ber?.state !== 'REVOKED';
    const lifecycleNotFailed = !LIFECYCLE_STATE_CONFIG[state.lifecycle_state].isFailed;

    return [
      {
        id: 'ack-all',
        label: 'All Agents Acknowledged',
        passed: allACKsReceived,
        blocking: true,
        detail: allACKsReceived
          ? `${state.ack_summary.acknowledged} agent(s) acknowledged`
          : `${state.ack_summary.pending} pending, ${state.ack_summary.acknowledged}/${state.ack_summary.total} complete`,
      },
      {
        id: 'ack-no-reject',
        label: 'No Rejected ACKs',
        passed: noRejectedACKs,
        blocking: true,
        detail: noRejectedACKs
          ? 'No agents rejected the PAC'
          : `${state.ack_summary.rejected} agent(s) rejected`,
      },
      {
        id: 'ack-no-timeout',
        label: 'No Timeout ACKs',
        passed: noTimeoutACKs,
        blocking: true,
        detail: noTimeoutACKs
          ? 'All agents responded within deadline'
          : `${state.ack_summary.timeout} agent(s) timed out`,
      },
      {
        id: 'wrap-valid',
        label: 'Valid WRAP Submitted',
        passed: hasValidWRAP,
        blocking: true,
        detail: hasValidWRAP
          ? 'WRAP validated and accepted'
          : 'Awaiting valid WRAP submission',
      },
      {
        id: 'wrap-no-invalid',
        label: 'No Invalid WRAPs',
        passed: noInvalidWRAPs,
        blocking: true,
        detail: noInvalidWRAPs
          ? 'No WRAP validation failures'
          : 'WRAP validation failed - check errors',
      },
      {
        id: 'ber-issued',
        label: 'BER Issued',
        passed: berIssued || false,
        blocking: true,
        detail: berIssued
          ? `BER ${state.ber?.ber_id} issued`
          : 'BER not yet issued',
      },
      {
        id: 'ber-valid',
        label: 'BER Not Challenged/Revoked',
        passed: berNotChallenged,
        blocking: true,
        detail: berNotChallenged
          ? 'BER is in good standing'
          : `BER status: ${state.ber?.state}`,
      },
      {
        id: 'lifecycle-ok',
        label: 'PAC Lifecycle Valid',
        passed: lifecycleNotFailed,
        blocking: true,
        detail: lifecycleNotFailed
          ? `Current state: ${state.lifecycle_state}`
          : `Failed state: ${state.lifecycle_state}`,
      },
    ];
  }, [state]);

  const allGatesPassed = gates.every(g => g.passed);

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/2 mx-auto" />
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 bg-gray-800 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg border border-red-800 p-4">
        <div className="flex items-center gap-2 text-red-400">
          <span>🛑</span>
          <span className="font-medium">Settlement Panel Error</span>
        </div>
        <p className="mt-2 text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-gray-500 text-center py-8">
          <span className="text-2xl">💰</span>
          <p className="mt-2">No settlement data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/50">
        <h3 className="text-sm font-medium text-gray-200">
          💰 Settlement Eligibility
        </h3>
      </div>

      {/* Main Status Display */}
      <div className={`p-6 text-center border-b border-gray-800 ${
        state.settlement_eligibility === 'BLOCKED'
          ? 'bg-red-900/20'
          : state.settlement_eligibility === 'ELIGIBLE'
            ? 'bg-green-900/20'
            : state.settlement_eligibility === 'SETTLED'
              ? 'bg-emerald-900/20'
              : 'bg-gray-800/30'
      }`}>
        <SettlementStatusBadge eligibility={state.settlement_eligibility} size="xl" />
        
        {state.settlement_block_reason && (
          <p className="mt-3 text-sm text-red-400">
            <strong>Block Reason:</strong> {state.settlement_block_reason}
          </p>
        )}
        
        {state.settlement_eligibility === 'SETTLED' && (
          <p className="mt-3 text-sm text-emerald-400">
            ✅ Settlement completed successfully.
          </p>
        )}
        
        {state.settlement_eligibility === 'ELIGIBLE' && (
          <p className="mt-3 text-sm text-green-400">
            ✅ All gates passed. Ready for settlement.
          </p>
        )}
      </div>

      {/* Gate Checklist */}
      <div className="p-4">
        <SettlementGateChecklist gates={gates} />
      </div>

      {/* FAIL_CLOSED Notice */}
      {state.settlement_eligibility === 'BLOCKED' && (
        <div className="px-4 py-3 border-t border-red-800 bg-red-900/20">
          <div className="flex items-start gap-2 text-red-400">
            <span className="text-lg">🛑</span>
            <div>
              <p className="font-medium">FAIL_CLOSED: Settlement Blocked</p>
              <p className="text-xs text-red-300 mt-1">
                One or more blocking gates have failed. Settlement cannot proceed until all gates pass.
                Manual intervention may be required.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Governance Footer */}
      <div className="px-4 py-2 border-t border-gray-800 bg-gray-800/30">
        <p className="text-[10px] text-gray-600">
          INV-CP-002: Missing ACK blocks settlement • 
          INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
        </p>
      </div>
    </div>
  );
};

export default SettlementEligibilityPanel;
