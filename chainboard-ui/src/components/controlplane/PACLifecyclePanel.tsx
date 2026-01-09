/**
 * PAC Lifecycle Panel — Control Plane UI
 * PAC-CP-UI-EXEC-001: ORDER 2 — PAC Lifecycle Visualization
 *
 * Displays deterministic PAC state transitions with full audit trail.
 *
 * INVARIANTS:
 * - INV-CP-003: All state transitions are deterministic and auditable
 * - Every state change is visible with timestamp and actor
 *
 * Author: Benson Execution Orchestrator (GID-00)
 */

import React from 'react';
import {
  ControlPlaneStateDTO,
  PACLifecycleState,
  StateTransitionRecord,
  LIFECYCLE_STATE_CONFIG,
  formatTimestamp,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// LIFECYCLE STATE BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface LifecycleStateBadgeProps {
  state: PACLifecycleState;
  size?: 'sm' | 'md' | 'lg';
}

export const LifecycleStateBadge: React.FC<LifecycleStateBadgeProps> = ({
  state,
  size = 'md',
}) => {
  const config = LIFECYCLE_STATE_CONFIG[state];
  
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
// LIFECYCLE PROGRESS BAR
// ═══════════════════════════════════════════════════════════════════════════════

const HAPPY_PATH_STATES: PACLifecycleState[] = [
  'DRAFT',
  'ACK_PENDING',
  'EXECUTING',
  'WRAP_PENDING',
  'WRAP_SUBMITTED',
  'WRAP_VALIDATED',
  'BER_ISSUED',
  'SETTLED',
];

interface LifecycleProgressBarProps {
  currentState: PACLifecycleState;
}

export const LifecycleProgressBar: React.FC<LifecycleProgressBarProps> = ({
  currentState,
}) => {
  const config = LIFECYCLE_STATE_CONFIG[currentState];
  const isFailed = config.isFailed;
  
  // Find position in happy path
  const currentIndex = HAPPY_PATH_STATES.indexOf(currentState);
  const progressPercent = isFailed
    ? 0
    : currentIndex >= 0
      ? ((currentIndex + 1) / HAPPY_PATH_STATES.length) * 100
      : 0;

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            isFailed ? 'bg-red-500' : 'bg-gradient-to-r from-blue-500 via-green-500 to-emerald-500'
          }`}
          style={{ width: `${isFailed ? 100 : progressPercent}%` }}
        />
      </div>
      
      {/* State markers */}
      <div className="flex justify-between text-xs">
        {HAPPY_PATH_STATES.map((state, idx) => {
          const stateConfig = LIFECYCLE_STATE_CONFIG[state];
          const isCompleted = !isFailed && currentIndex >= idx;
          const isCurrent = state === currentState;
          
          return (
            <div
              key={state}
              className={`flex flex-col items-center ${
                isCurrent
                  ? stateConfig.color
                  : isCompleted
                    ? 'text-green-400'
                    : 'text-gray-500'
              }`}
            >
              <span className="text-lg">{stateConfig.icon}</span>
              <span className="hidden md:block mt-1 max-w-[60px] text-center truncate">
                {stateConfig.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// STATE TRANSITION TIMELINE
// ═══════════════════════════════════════════════════════════════════════════════

interface StateTransitionTimelineProps {
  transitions: StateTransitionRecord[];
}

export const StateTransitionTimeline: React.FC<StateTransitionTimelineProps> = ({
  transitions,
}) => {
  if (transitions.length === 0) {
    return (
      <div className="text-gray-500 text-sm italic py-4">
        No state transitions recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {transitions.map((transition, idx) => {
        const fromConfig = LIFECYCLE_STATE_CONFIG[transition.from_state];
        const toConfig = LIFECYCLE_STATE_CONFIG[transition.to_state];
        
        return (
          <div key={idx} className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
            {/* Timeline connector */}
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full ${toConfig.bgColor} border-2 border-gray-700`} />
              {idx < transitions.length - 1 && (
                <div className="w-0.5 h-full bg-gray-700 mt-1" />
              )}
            </div>
            
            {/* Transition details */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <LifecycleStateBadge state={transition.from_state} size="sm" />
                <span className="text-gray-500">→</span>
                <LifecycleStateBadge state={transition.to_state} size="sm" />
              </div>
              
              <div className="mt-1 text-sm text-gray-400">
                <span className="font-mono text-xs">{formatTimestamp(transition.timestamp)}</span>
                <span className="mx-2">•</span>
                <span className="text-gray-300">{transition.reason}</span>
              </div>
              
              <div className="mt-0.5 text-xs text-gray-500">
                Actor: <span className="font-mono">{transition.actor}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// PAC LIFECYCLE PANEL (MAIN COMPONENT)
// ═══════════════════════════════════════════════════════════════════════════════

interface PACLifecyclePanelProps {
  state: ControlPlaneStateDTO | null;
  loading?: boolean;
  error?: string | null;
}

export const PACLifecyclePanel: React.FC<PACLifecyclePanelProps> = ({
  state,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-800 rounded w-1/3" />
          <div className="h-4 bg-gray-800 rounded w-full" />
          <div className="h-20 bg-gray-800 rounded w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg border border-red-800 p-4">
        <div className="flex items-center gap-2 text-red-400">
          <span>🛑</span>
          <span className="font-medium">Control Plane Error</span>
        </div>
        <p className="mt-2 text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-gray-500 text-center py-8">
          <span className="text-2xl">📋</span>
          <p className="mt-2">No PAC selected</p>
        </div>
      </div>
    );
  }

  const config = LIFECYCLE_STATE_CONFIG[state.lifecycle_state];

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-200">
            📋 PAC Lifecycle
          </h3>
          <LifecycleStateBadge state={state.lifecycle_state} size="md" />
        </div>
      </div>

      {/* PAC Info */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">PAC ID</span>
            <p className="font-mono text-gray-200 truncate">{state.pac_id}</p>
          </div>
          <div>
            <span className="text-gray-500">Runtime ID</span>
            <p className="font-mono text-gray-200 truncate">{state.runtime_id}</p>
          </div>
          <div>
            <span className="text-gray-500">Created</span>
            <p className="text-gray-200">{formatTimestamp(state.created_at)}</p>
          </div>
          <div>
            <span className="text-gray-500">Last Updated</span>
            <p className="text-gray-200">{formatTimestamp(state.updated_at)}</p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="px-4 py-4 border-b border-gray-800">
        <LifecycleProgressBar currentState={state.lifecycle_state} />
      </div>

      {/* Failed State Warning */}
      {config.isFailed && (
        <div className="px-4 py-3 border-b border-gray-800 bg-red-900/20">
          <div className="flex items-start gap-2">
            <span className="text-red-400 text-lg">🛑</span>
            <div>
              <p className="text-red-400 font-medium">
                Execution Failed: {config.label}
              </p>
              {state.settlement_block_reason && (
                <p className="text-sm text-red-300 mt-1">
                  {state.settlement_block_reason}
                </p>
              )}
              <p className="text-xs text-red-400/70 mt-2">
                FAIL_CLOSED: Settlement blocked. Manual intervention required.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* State Transition Timeline */}
      <div className="px-4 py-3">
        <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">
          State Transitions (Audit Trail)
        </h4>
        <div className="max-h-64 overflow-y-auto">
          <StateTransitionTimeline transitions={state.state_transitions} />
        </div>
      </div>
    </div>
  );
};

export default PACLifecyclePanel;
