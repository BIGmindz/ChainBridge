// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust Governance Status Panel
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY governance status visualization.
// Displays: Governance status (PASS/FAIL), active invariant count, runtime mode.
//
// DATA SOURCE: lint_v2.LintV2Engine.get_activation_status()
// INVARIANT: INV-LINT-PLAT-003 — UI renders only lint-validated state
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type { GovernanceStatusDTO } from '../../types/chaintrust';
import { STATUS_COLORS } from '../../types/chaintrust';

interface GovernanceStatusPanelProps {
  status: GovernanceStatusDTO | null;
  loading: boolean;
  error: string | null;
}

/**
 * Status badge component.
 */
const StatusBadge: React.FC<{ status: 'PASS' | 'FAIL' }> = ({ status }) => {
  const colorClass = STATUS_COLORS[status];
  return (
    <span className={`${colorClass} text-white text-lg px-4 py-2 rounded-full font-bold`}>
      {status}
    </span>
  );
};

/**
 * Runtime activation check indicator.
 */
const ActivationCheck: React.FC<{ label: string; enabled: boolean }> = ({ label, enabled }) => (
  <div className="flex items-center justify-between py-1">
    <span className="text-sm text-gray-300">{label}</span>
    <span className={`text-sm font-mono ${enabled ? 'text-green-400' : 'text-red-400'}`}>
      {enabled ? '✓ TRUE' : '✗ FALSE'}
    </span>
  </div>
);

/**
 * Loading skeleton.
 */
const LoadingSkeleton: React.FC = () => (
  <div className="animate-pulse">
    <div className="h-8 bg-gray-700 rounded w-32 mb-4"></div>
    <div className="space-y-2">
      {[1, 2, 3, 4, 5, 6, 7].map((i) => (
        <div key={i} className="h-4 bg-gray-700 rounded"></div>
      ))}
    </div>
  </div>
);

/**
 * Governance Status Panel for ChainTrust Overview.
 * Displays governance health, runtime activation, and fail mode.
 */
export const GovernanceStatusPanel: React.FC<GovernanceStatusPanelProps> = ({
  status,
  loading,
  error,
}) => {
  if (error) {
    return (
      <div className="bg-gray-900 border border-red-500 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-400 mb-2">Governance Status Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Governance Status</h3>
        {!loading && status && <StatusBadge status={status.status} />}
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : status ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-blue-400">{status.invariant_count}</div>
              <div className="text-xs text-gray-400 mt-1">Total Invariants</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-red-400">{status.uniform_invariant_count}</div>
              <div className="text-xs text-gray-400 mt-1">Uniform Invariants</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <div className={`text-xl font-bold ${status.fail_mode === 'HARD_FAIL' ? 'text-red-400' : 'text-yellow-400'}`}>
                {status.fail_mode}
              </div>
              <div className="text-xs text-gray-400 mt-1">Fail Mode</div>
            </div>
          </div>

          {/* Runtime Activation Status */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-sm font-medium text-gray-300 mb-3">Runtime Activation</h4>
            <div className="space-y-1">
              <ActivationCheck 
                label="Schema Validation" 
                enabled={status.runtime_activation.schema_validation_enabled} 
              />
              <ActivationCheck 
                label="Invariant Registry" 
                enabled={status.runtime_activation.invariant_registry_loaded} 
              />
              <ActivationCheck 
                label="Lint V2 Compiler" 
                enabled={status.runtime_activation.lint_v2_compiler_active} 
              />
              <ActivationCheck 
                label="Runtime ACK Enforced" 
                enabled={status.runtime_activation.runtime_ack_enforced} 
              />
              <ActivationCheck 
                label="Agent ACK Enforced" 
                enabled={status.runtime_activation.agent_ack_enforced} 
              />
              <ActivationCheck 
                label="Deterministic Order" 
                enabled={status.runtime_activation.deterministic_execution_order} 
              />
              <ActivationCheck 
                label="Fail Closed" 
                enabled={status.runtime_activation.fail_closed_enabled} 
              />
            </div>
          </div>

          {/* Validation Info */}
          <div className="border-t border-gray-700 pt-4 mt-4">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Last Validated: {new Date(status.last_validated_at).toLocaleString()}</span>
              <span className="font-mono truncate max-w-[150px]" title={status.validation_hash}>
                Hash: {status.validation_hash.slice(0, 12)}...
              </span>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};

export default GovernanceStatusPanel;
