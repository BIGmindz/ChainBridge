// ═══════════════════════════════════════════════════════════════════════════════
// OCC Phase 2 — SOP Execution Monitor
// PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
// Agents: SONNY (GID-02) — Frontend / OCC UI
//         LIRA (GID-09) — Accessibility & UX
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * SOPExecutionMonitor — Real-time SOP execution monitoring
 *
 * PURPOSE:
 *   Display real-time SOP execution status with approval progress,
 *   precondition validation, and audit trail visibility.
 *
 * FEATURES:
 *   - Live execution state tracking
 *   - Approval workflow visualization
 *   - Precondition check display
 *   - Execution timeline
 *
 * ACCESSIBILITY (LIRA):
 *   - ARIA live regions for state changes
 *   - Progress indicators with percentages
 *   - Color-blind safe status indicators
 *
 * INVARIANTS:
 *   INV-UI-SOP-001: Display-only SOP state (no execution triggers)
 *   INV-UI-SOP-002: Approval counts accurately reflect backend state
 */

import React, { useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type SOPExecutionState =
  | 'PENDING'
  | 'APPROVED'
  | 'EXECUTING'
  | 'COMPLETED'
  | 'FAILED'
  | 'ROLLED_BACK'
  | 'REJECTED';

export type SOPCategory = 'SHIPMENT' | 'PAYMENT' | 'RISK' | 'GOVERNANCE' | 'SYSTEM';
export type SOPSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface SOPApprovalView {
  approver_id: string;
  approver_role: string;
  approved_at: string;
  notes?: string;
}

export interface SOPExecutionView {
  execution_id: string;
  sop_id: string;
  sop_name: string;
  category: SOPCategory;
  severity: SOPSeverity;
  state: SOPExecutionState;
  initiator_id: string;
  initiated_at: string;
  approval_count: number;
  approval_required: number;
  approvals: SOPApprovalView[];
  precondition_checks: Record<string, boolean>;
  progress_percent: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface SOPExecutionMonitorProps {
  /** SOP executions to display */
  executions: SOPExecutionView[];
  /** Selected execution ID */
  selectedId?: string;
  /** Selection handler */
  onSelect?: (id: string) => void;
  /** Show only active executions */
  showActiveOnly?: boolean;
  /** Maximum executions to display */
  maxDisplay?: number;
  /** ARIA label */
  ariaLabel?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const STATE_CONFIG: Record<SOPExecutionState, {
  icon: string;
  label: string;
  color: string;
  bgColor: string;
}> = {
  PENDING: {
    icon: '⏳',
    label: 'Pending Approval',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50 border-yellow-200',
  },
  APPROVED: {
    icon: '✓',
    label: 'Approved',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50 border-blue-200',
  },
  EXECUTING: {
    icon: '⚡',
    label: 'Executing',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50 border-purple-200',
  },
  COMPLETED: {
    icon: '✅',
    label: 'Completed',
    color: 'text-green-700',
    bgColor: 'bg-green-50 border-green-200',
  },
  FAILED: {
    icon: '❌',
    label: 'Failed',
    color: 'text-red-700',
    bgColor: 'bg-red-50 border-red-200',
  },
  ROLLED_BACK: {
    icon: '↩️',
    label: 'Rolled Back',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50 border-orange-200',
  },
  REJECTED: {
    icon: '🚫',
    label: 'Rejected',
    color: 'text-gray-700',
    bgColor: 'bg-gray-50 border-gray-200',
  },
};

const SEVERITY_BADGE: Record<SOPSeverity, string> = {
  LOW: 'bg-gray-100 text-gray-700',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  HIGH: 'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

const CATEGORY_ICON: Record<SOPCategory, string> = {
  SHIPMENT: '📦',
  PAYMENT: '💳',
  RISK: '⚠️',
  GOVERNANCE: '⚖️',
  SYSTEM: '🖥️',
};

// ═══════════════════════════════════════════════════════════════════════════════
// SUBCOMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface ApprovalProgressProps {
  count: number;
  required: number;
  approvals: SOPApprovalView[];
}

const ApprovalProgress: React.FC<ApprovalProgressProps> = ({
  count,
  required,
  approvals,
}) => {
  const percentage = required > 0 ? Math.min((count / required) * 100, 100) : 100;
  const isComplete = count >= required;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-600">
          Approvals: {count}/{required}
        </span>
        <span className={isComplete ? 'text-green-600' : 'text-yellow-600'}>
          {isComplete ? 'Ready' : 'Pending'}
        </span>
      </div>
      <div
        className="h-2 bg-gray-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={count}
        aria-valuemin={0}
        aria-valuemax={required}
        aria-label={`${count} of ${required} approvals`}
      >
        <div
          className={`h-full transition-all duration-300 ${
            isComplete ? 'bg-green-500' : 'bg-yellow-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {approvals.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {approvals.map((approval, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-800"
              title={`Approved by ${approval.approver_id} at ${new Date(approval.approved_at).toLocaleString()}`}
            >
              ✓ {approval.approver_role}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

interface PreconditionChecksProps {
  checks: Record<string, boolean>;
}

const PreconditionChecks: React.FC<PreconditionChecksProps> = ({ checks }) => {
  const entries = Object.entries(checks);
  const passedCount = entries.filter(([, passed]) => passed).length;

  if (entries.length === 0) {
    return (
      <span className="text-xs text-gray-500">No precondition checks</span>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <span>Preconditions:</span>
        <span
          className={`font-medium ${
            passedCount === entries.length ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {passedCount}/{entries.length} passed
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {entries.map(([id, passed]) => (
          <span
            key={id}
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs ${
              passed
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
            title={id}
          >
            {passed ? '✓' : '✗'} {id.slice(-6)}
          </span>
        ))}
      </div>
    </div>
  );
};

interface ExecutionCardProps {
  execution: SOPExecutionView;
  isSelected: boolean;
  onSelect: () => void;
}

const ExecutionCard: React.FC<ExecutionCardProps> = ({
  execution,
  isSelected,
  onSelect,
}) => {
  const stateConfig = STATE_CONFIG[execution.state];
  const severityClass = SEVERITY_BADGE[execution.severity];
  const categoryIcon = CATEGORY_ICON[execution.category];

  return (
    <div
      role="article"
      aria-selected={isSelected}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      tabIndex={0}
      className={`
        p-3 border rounded-lg cursor-pointer transition-all duration-150
        ${stateConfig.bgColor}
        ${isSelected ? 'ring-2 ring-blue-500 ring-offset-1' : 'hover:shadow-md'}
        focus:outline-none focus:ring-2 focus:ring-blue-500
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span
            className="text-lg"
            role="img"
            aria-label={execution.category}
          >
            {categoryIcon}
          </span>
          <div>
            <h3 className="font-medium text-gray-900 text-sm">
              {execution.sop_name}
            </h3>
            <p className="text-xs text-gray-500 font-mono">
              {execution.sop_id}
            </p>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${severityClass}`}>
          {execution.severity}
        </span>
      </div>

      {/* State Badge */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${stateConfig.color}`}
          role="status"
        >
          <span aria-hidden="true">{stateConfig.icon}</span>
          {stateConfig.label}
        </span>
        <span className="text-xs text-gray-500">
          {execution.progress_percent}% complete
        </span>
      </div>

      {/* Progress Bar */}
      <div
        className="h-1.5 bg-gray-200 rounded-full overflow-hidden mb-3"
        role="progressbar"
        aria-valuenow={execution.progress_percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full transition-all duration-500 ${
            execution.state === 'COMPLETED'
              ? 'bg-green-500'
              : execution.state === 'FAILED'
              ? 'bg-red-500'
              : 'bg-blue-500'
          }`}
          style={{ width: `${execution.progress_percent}%` }}
        />
      </div>

      {/* Approval Progress */}
      <div className="mb-3">
        <ApprovalProgress
          count={execution.approval_count}
          required={execution.approval_required}
          approvals={execution.approvals}
        />
      </div>

      {/* Precondition Checks */}
      <PreconditionChecks checks={execution.precondition_checks} />

      {/* Error Message */}
      {execution.error_message && (
        <div
          className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-xs text-red-800"
          role="alert"
        >
          <strong>Error:</strong> {execution.error_message}
        </div>
      )}

      {/* Timestamps */}
      <div className="mt-3 pt-2 border-t border-gray-200 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>Initiated: {new Date(execution.initiated_at).toLocaleString()}</span>
          <span>By: {execution.initiator_id}</span>
        </div>
        {execution.completed_at && (
          <div className="mt-1">
            Completed: {new Date(execution.completed_at).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const SOPExecutionMonitor: React.FC<SOPExecutionMonitorProps> = ({
  executions,
  selectedId,
  onSelect,
  showActiveOnly = false,
  maxDisplay = 20,
  ariaLabel = 'SOP Execution Monitor',
}) => {
  // Filter and limit executions
  const displayExecutions = useMemo(() => {
    let filtered = [...executions];

    if (showActiveOnly) {
      const terminalStates: SOPExecutionState[] = [
        'COMPLETED',
        'FAILED',
        'ROLLED_BACK',
        'REJECTED',
      ];
      filtered = filtered.filter((e) => !terminalStates.includes(e.state));
    }

    // Sort by state priority, then timestamp
    const statePriority: Record<SOPExecutionState, number> = {
      EXECUTING: 0,
      PENDING: 1,
      APPROVED: 2,
      FAILED: 3,
      ROLLED_BACK: 4,
      COMPLETED: 5,
      REJECTED: 6,
    };

    filtered.sort((a, b) => {
      const priorityDiff = statePriority[a.state] - statePriority[b.state];
      if (priorityDiff !== 0) return priorityDiff;
      return new Date(b.initiated_at).getTime() - new Date(a.initiated_at).getTime();
    });

    return filtered.slice(0, maxDisplay);
  }, [executions, showActiveOnly, maxDisplay]);

  // Statistics
  const stats = useMemo(() => {
    const executing = executions.filter((e) => e.state === 'EXECUTING').length;
    const pending = executions.filter((e) => e.state === 'PENDING').length;
    const failed = executions.filter((e) => e.state === 'FAILED').length;
    return { total: executions.length, executing, pending, failed };
  }, [executions]);

  return (
    <div
      className="flex flex-col h-full bg-white rounded-lg border border-gray-200 shadow-sm"
      aria-label={ariaLabel}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            SOP Execution Monitor
          </h2>
          <div
            className="flex items-center gap-2 text-sm"
            role="status"
            aria-live="polite"
          >
            {stats.executing > 0 && (
              <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full text-xs animate-pulse">
                {stats.executing} executing
              </span>
            )}
            {stats.pending > 0 && (
              <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs">
                {stats.pending} pending
              </span>
            )}
            {stats.failed > 0 && (
              <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded-full text-xs">
                {stats.failed} failed
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Execution Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {displayExecutions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <span className="text-2xl mb-2">📋</span>
            <p>No SOP executions</p>
            <p className="text-xs mt-1">
              {showActiveOnly ? 'No active executions' : 'No executions recorded'}
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {displayExecutions.map((execution) => (
              <ExecutionCard
                key={execution.execution_id}
                execution={execution}
                isSelected={selectedId === execution.execution_id}
                onSelect={() => onSelect?.(execution.execution_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span>
          Showing {displayExecutions.length} of {executions.length} executions
          {showActiveOnly && ' (active only)'}
        </span>
      </div>
    </div>
  );
};

export default SOPExecutionMonitor;
