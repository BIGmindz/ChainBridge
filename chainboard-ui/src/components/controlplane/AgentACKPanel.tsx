/**
 * Agent ACK Panel — Control Plane UI
 * PAC-CP-UI-EXEC-001: ORDER 3 — Agent Activation + ACK Panels
 *
 * Displays agent acknowledgment status with latency visibility.
 *
 * INVARIANTS:
 * - INV-CP-001: No execution without explicit ACK
 * - INV-CP-002: Missing ACK blocks execution AND settlement
 * - ACK latency is visible for all agents
 * - Missing ACK blocks execution and settlement
 *
 * Author: Benson Execution Orchestrator (GID-00)
 */

import React, { useMemo } from 'react';
import {
  ControlPlaneStateDTO,
  AgentACKDTO,
  AgentACKState,
  ACK_STATE_CONFIG,
  formatTimestamp,
  formatLatency,
  isACKOverdue,
  getACKTimeRemaining,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// ACK STATE BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface ACKStateBadgeProps {
  state: AgentACKState;
  isOverdue?: boolean;
}

export const ACKStateBadge: React.FC<ACKStateBadgeProps> = ({
  state,
  isOverdue = false,
}) => {
  const config = ACK_STATE_CONFIG[state];
  
  // Override for overdue pending
  const displayConfig = isOverdue && state === 'PENDING'
    ? { ...config, color: 'text-red-400', bgColor: 'bg-red-900/50', icon: '⏰', label: 'OVERDUE' }
    : config;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${displayConfig.bgColor} ${displayConfig.color}`}
    >
      <span>{displayConfig.icon}</span>
      <span>{displayConfig.label}</span>
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// ACK LATENCY INDICATOR
// ═══════════════════════════════════════════════════════════════════════════════

interface ACKLatencyIndicatorProps {
  latency_ms: number | null;
}

export const ACKLatencyIndicator: React.FC<ACKLatencyIndicatorProps> = ({
  latency_ms,
}) => {
  if (latency_ms === null) {
    return <span className="text-gray-500">—</span>;
  }

  // Color based on latency threshold
  let colorClass = 'text-green-400';
  if (latency_ms > 5000) colorClass = 'text-red-400';
  else if (latency_ms > 2000) colorClass = 'text-orange-400';
  else if (latency_ms > 1000) colorClass = 'text-yellow-400';

  return (
    <span className={`font-mono text-xs ${colorClass}`}>
      {formatLatency(latency_ms)}
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SINGLE ACK CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface ACKCardProps {
  ack: AgentACKDTO;
}

export const ACKCard: React.FC<ACKCardProps> = ({ ack }) => {
  const overdue = isACKOverdue(ack);
  const timeRemaining = getACKTimeRemaining(ack);
  const config = ACK_STATE_CONFIG[ack.state];

  return (
    <div
      className={`rounded-lg border p-3 ${
        ack.state === 'ACKNOWLEDGED'
          ? 'border-green-800 bg-green-900/10'
          : ack.state === 'REJECTED' || ack.state === 'TIMEOUT' || overdue
            ? 'border-red-800 bg-red-900/10'
            : 'border-gray-700 bg-gray-800/50'
      }`}
    >
      {/* Agent Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <div>
            <span className="font-medium text-gray-200">{ack.agent_name}</span>
            <span className="ml-2 text-xs text-gray-500 font-mono">{ack.agent_gid}</span>
          </div>
        </div>
        <ACKStateBadge state={ack.state} isOverdue={overdue} />
      </div>

      {/* ACK Details */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-500">Order ID</span>
          <p className="font-mono text-gray-300 truncate">{ack.order_id}</p>
        </div>
        <div>
          <span className="text-gray-500">Latency</span>
          <p><ACKLatencyIndicator latency_ms={ack.latency_ms} /></p>
        </div>
        <div>
          <span className="text-gray-500">Requested</span>
          <p className="text-gray-300">{formatTimestamp(ack.requested_at)}</p>
        </div>
        <div>
          <span className="text-gray-500">
            {ack.state === 'PENDING' ? 'Deadline' : 'ACKed'}
          </span>
          <p className="text-gray-300">
            {ack.state === 'PENDING'
              ? timeRemaining
              : formatTimestamp(ack.acknowledged_at)}
          </p>
        </div>
      </div>

      {/* Rejection Reason */}
      {ack.rejection_reason && (
        <div className="mt-2 p-2 bg-red-900/20 rounded text-xs text-red-300">
          <span className="font-medium">Rejection Reason:</span> {ack.rejection_reason}
        </div>
      )}

      {/* Overdue Warning */}
      {overdue && (
        <div className="mt-2 p-2 bg-red-900/30 rounded text-xs text-red-400 flex items-center gap-2">
          <span>🛑</span>
          <span>
            <strong>FAIL_CLOSED:</strong> ACK deadline exceeded. Execution blocked.
          </span>
        </div>
      )}

      {/* Hash for audit */}
      <div className="mt-2 pt-2 border-t border-gray-700">
        <span className="text-[10px] text-gray-600 font-mono break-all">
          Hash: {ack.ack_hash.slice(0, 16)}...
        </span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// ACK SUMMARY BAR
// ═══════════════════════════════════════════════════════════════════════════════

interface ACKSummaryBarProps {
  summary: ControlPlaneStateDTO['ack_summary'];
}

export const ACKSummaryBar: React.FC<ACKSummaryBarProps> = ({ summary }) => {
  const total = summary.total || 1; // Avoid division by zero
  
  const segments = [
    { key: 'acknowledged', count: summary.acknowledged, color: 'bg-green-500', label: 'ACKed' },
    { key: 'pending', count: summary.pending, color: 'bg-yellow-500', label: 'Pending' },
    { key: 'timeout', count: summary.timeout, color: 'bg-orange-500', label: 'Timeout' },
    { key: 'rejected', count: summary.rejected, color: 'bg-red-500', label: 'Rejected' },
  ];

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden flex">
        {segments.map((seg) => (
          <div
            key={seg.key}
            className={`${seg.color} transition-all duration-300`}
            style={{ width: `${(seg.count / total) * 100}%` }}
          />
        ))}
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs">
        {segments.map((seg) => (
          <div key={seg.key} className="flex items-center gap-1">
            <div className={`w-2 h-2 rounded-full ${seg.color}`} />
            <span className="text-gray-400">{seg.label}:</span>
            <span className="font-medium text-gray-200">{seg.count}</span>
          </div>
        ))}
      </div>
      
      {/* Latency summary */}
      {summary.latency.avg_ms !== null && (
        <div className="text-xs text-gray-500">
          Latency: min {formatLatency(summary.latency.min_ms)} / 
          avg {formatLatency(summary.latency.avg_ms)} / 
          max {formatLatency(summary.latency.max_ms)}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT ACK PANEL (MAIN COMPONENT)
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentACKPanelProps {
  state: ControlPlaneStateDTO | null;
  loading?: boolean;
  error?: string | null;
}

export const AgentACKPanel: React.FC<AgentACKPanelProps> = ({
  state,
  loading = false,
  error = null,
}) => {
  // Memoized sorted ACKs
  const sortedAcks = useMemo(() => {
    if (!state) return [];
    return Object.values(state.agent_acks).sort((a, b) => {
      // Sort by: Pending first, then by requested_at
      if (a.state === 'PENDING' && b.state !== 'PENDING') return -1;
      if (a.state !== 'PENDING' && b.state === 'PENDING') return 1;
      return new Date(a.requested_at).getTime() - new Date(b.requested_at).getTime();
    });
  }, [state]);

  // Check for blocking conditions
  const hasBlockingCondition = useMemo(() => {
    if (!state) return false;
    return state.ack_summary.rejected > 0 || 
           state.ack_summary.timeout > 0 ||
           sortedAcks.some(isACKOverdue);
  }, [state, sortedAcks]);

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-800 rounded w-1/3" />
          <div className="h-4 bg-gray-800 rounded w-full" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-32 bg-gray-800 rounded" />
            <div className="h-32 bg-gray-800 rounded" />
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
          <span className="font-medium">ACK Panel Error</span>
        </div>
        <p className="mt-2 text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-gray-500 text-center py-8">
          <span className="text-2xl">✅</span>
          <p className="mt-2">No ACK data available</p>
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
            ✅ Agent Acknowledgments
          </h3>
          <span className="text-xs text-gray-500">
            {state.ack_summary.acknowledged}/{state.ack_summary.total} ACKed
          </span>
        </div>
      </div>

      {/* Blocking Condition Banner */}
      {hasBlockingCondition && (
        <div className="px-4 py-3 border-b border-red-800 bg-red-900/20">
          <div className="flex items-center gap-2 text-red-400">
            <span>🛑</span>
            <span className="font-medium">FAIL_CLOSED: Execution Blocked</span>
          </div>
          <p className="text-xs text-red-300 mt-1">
            Missing or rejected ACKs prevent execution and settlement.
            No execution without explicit ACK (INV-CP-001).
          </p>
        </div>
      )}

      {/* ACK Summary */}
      <div className="px-4 py-3 border-b border-gray-800">
        <ACKSummaryBar summary={state.ack_summary} />
      </div>

      {/* ACK Cards */}
      <div className="p-4">
        {sortedAcks.length === 0 ? (
          <div className="text-gray-500 text-center py-4">
            No agent ACKs registered for this PAC.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sortedAcks.map((ack) => (
              <ACKCard key={ack.ack_id} ack={ack} />
            ))}
          </div>
        )}
      </div>

      {/* Governance Footer */}
      <div className="px-4 py-2 border-t border-gray-800 bg-gray-800/30">
        <p className="text-[10px] text-gray-600">
          INV-CP-001: No execution without explicit ACK • 
          INV-CP-002: Missing ACK blocks execution AND settlement
        </p>
      </div>
    </div>
  );
};

export default AgentACKPanel;
