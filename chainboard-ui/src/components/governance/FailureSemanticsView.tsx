// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Failure Semantics Display
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type { FailureSemanticsDTO } from '../../types/governance';

interface FailureSemanticsViewProps {
  semantics: FailureSemanticsDTO;
}

/**
 * Failure mode description.
 */
function getFailureModeDescription(mode: string): string {
  switch (mode) {
    case 'FAIL_CLOSED':
      return 'Halt all downstream execution immediately';
    case 'FAIL_OPEN':
      return 'Continue with degraded state';
    case 'FAIL_RETRY':
      return 'Retry with exponential backoff';
    case 'FAIL_COMPENSATE':
      return 'Execute compensation action';
    default:
      return mode;
  }
}

/**
 * Rollback strategy description.
 */
function getRollbackDescription(strategy: string): string {
  switch (strategy) {
    case 'NONE':
      return 'No rollback possible';
    case 'COMPENSATING':
      return 'Execute compensating transaction';
    case 'CHECKPOINT':
      return 'Restore from checkpoint';
    case 'FULL_REVERT':
      return 'Revert all changes';
    default:
      return strategy;
  }
}

/**
 * Propagation mode description.
 */
function getPropagationDescription(mode: string): string {
  switch (mode) {
    case 'IMMEDIATE':
      return 'Fail all dependents immediately';
    case 'CASCADING':
      return 'Propagate sequentially through graph';
    case 'CONTAINED':
      return 'Contain to affected branch only';
    case 'ISOLATED':
      return 'No propagation (soft dependencies)';
    default:
      return mode;
  }
}

/**
 * Semantics card component.
 */
const SemanticsCard: React.FC<{
  title: string;
  icon: string;
  items: string[];
  getDescription: (item: string) => string;
  colorClass: string;
}> = ({ title, icon, items, getDescription, colorClass }) => {
  return (
    <div className={`border rounded-lg p-4 ${colorClass}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <h4 className="font-medium">{title}</h4>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item} className="flex items-start gap-2 text-sm">
            <span className="font-mono bg-white/50 px-2 py-0.5 rounded text-xs">
              {item}
            </span>
            <span className="opacity-75 text-xs">{getDescription(item)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Failure semantics display component.
 * 
 * INV-GOV-003: No silent partial success.
 * INV-GOV-008: Fail-closed on any violation.
 */
export const FailureSemanticsView: React.FC<FailureSemanticsViewProps> = ({
  semantics,
}) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Failure Semantics & Boundaries
        </h3>
      </div>

      {/* Invariant warnings */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="p-2 bg-orange-50 border border-orange-200 rounded text-xs text-orange-800">
          <strong>INV-GOV-003:</strong> No silent partial success — all outcomes must be explicit
        </div>
        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
          <strong>INV-GOV-008:</strong> Fail-closed on any governance violation
        </div>
      </div>

      {/* Semantics grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Failure modes */}
        <SemanticsCard
          title="Failure Modes"
          icon="⚠️"
          items={semantics.failure_modes}
          getDescription={getFailureModeDescription}
          colorClass="bg-red-50 border-red-200"
        />

        {/* Rollback strategies */}
        <SemanticsCard
          title="Rollback Strategies"
          icon="↩️"
          items={semantics.rollback_strategies}
          getDescription={getRollbackDescription}
          colorClass="bg-yellow-50 border-yellow-200"
        />

        {/* Propagation modes */}
        <SemanticsCard
          title="Failure Propagation"
          icon="📡"
          items={semantics.propagation_modes}
          getDescription={getPropagationDescription}
          colorClass="bg-blue-50 border-blue-200"
        />

        {/* Human intervention */}
        <div className="border rounded-lg p-4 bg-purple-50 border-purple-200">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">👤</span>
            <h4 className="font-medium">Human Intervention Types</h4>
          </div>
          <div className="space-y-1">
            {semantics.human_intervention_types.map((type) => (
              <span
                key={type}
                className="inline-block mr-2 mb-1 font-mono bg-white/50 px-2 py-0.5 rounded text-xs"
              >
                {type}
              </span>
            ))}
          </div>
          <div className="mt-3 text-xs text-purple-700">
            <strong>INV-GOV-005:</strong> Override requires PDO reference
          </div>
        </div>
      </div>

      {/* Human boundary statuses */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-2">
          Human Boundary Resolution States
        </h4>
        <div className="flex flex-wrap gap-2">
          {semantics.human_boundary_statuses.map((status) => (
            <span
              key={status}
              className={`px-2 py-1 rounded text-xs font-medium ${
                status === 'APPROVED'
                  ? 'bg-green-100 text-green-800'
                  : status === 'REJECTED'
                  ? 'bg-red-100 text-red-800'
                  : status === 'BYPASSED'
                  ? 'bg-orange-100 text-orange-800'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {status}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FailureSemanticsView;
