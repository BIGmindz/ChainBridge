/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Execution State Banner — Persistent PAC Status Display
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Persistent banner showing:
 * - Current PAC ID and state
 * - Active agents count
 * - Progress indicators
 * - Error/warning alerts
 * - Quick actions
 * 
 * INVARIANTS:
 * - INV-OCC-002: Always reflects backend state
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type ExecutionPhase =
  | 'idle'
  | 'admission'
  | 'runtime_activation'
  | 'agent_activation'
  | 'executing'
  | 'wrap_collection'
  | 'review_gate'
  | 'ber_issuance'
  | 'settled'
  | 'failed';

export interface ExecutionStateData {
  /** Active PAC ID */
  pacId: string | null;
  /** PAC title */
  pacTitle: string | null;
  /** Current execution phase */
  phase: ExecutionPhase;
  /** Active agents count */
  activeAgents: number;
  /** Total agents */
  totalAgents: number;
  /** Completed tasks */
  completedTasks: number;
  /** Total tasks */
  totalTasks: number;
  /** Current phase progress (0-100) */
  phaseProgress: number;
  /** Error message (if any) */
  error: string | null;
  /** Warning message (if any) */
  warning: string | null;
  /** Last updated timestamp */
  lastUpdated: string;
}

export interface ExecutionStateBannerProps {
  state: ExecutionStateData;
  onViewTimeline?: () => void;
  onViewDashboard?: () => void;
  onEmergencyStop?: () => void;
  compact?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const PHASE_CONFIG: Record<ExecutionPhase, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
  description: string;
}> = {
  idle: {
    label: 'IDLE',
    color: 'text-gray-400',
    bgColor: 'bg-gray-800',
    icon: '○',
    description: 'No active execution',
  },
  admission: {
    label: 'ADMISSION',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    icon: '📋',
    description: 'PAC admission in progress',
  },
  runtime_activation: {
    label: 'RUNTIME',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    icon: '⚡',
    description: 'Runtime activation',
  },
  agent_activation: {
    label: 'AGENTS',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30',
    icon: '🤖',
    description: 'Agent activation & ACK collection',
  },
  executing: {
    label: 'EXECUTING',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/30',
    icon: '⚙️',
    description: 'Tasks in execution',
  },
  wrap_collection: {
    label: 'WRAP',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
    icon: '📦',
    description: 'WRAP collection in progress',
  },
  review_gate: {
    label: 'REVIEW',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/30',
    icon: '🚦',
    description: 'Review gate evaluation',
  },
  ber_issuance: {
    label: 'BER',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-900/30',
    icon: '📄',
    description: 'BER issuance',
  },
  settled: {
    label: 'SETTLED',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    icon: '✓',
    description: 'Execution complete',
  },
  failed: {
    label: 'FAILED',
    color: 'text-red-400',
    bgColor: 'bg-red-900/30',
    icon: '✗',
    description: 'Execution failed',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface ProgressBarProps {
  progress: number;
  colorClass: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, colorClass }) => (
  <div className="w-full bg-gray-700 rounded-full h-1.5">
    <div
      className={`${colorClass} h-1.5 rounded-full transition-all duration-500`}
      style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
    />
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const ExecutionStateBanner: React.FC<ExecutionStateBannerProps> = ({
  state,
  onViewTimeline,
  onViewDashboard,
  onEmergencyStop,
  compact = false,
}) => {
  const phaseConfig = PHASE_CONFIG[state.phase];

  // Calculate overall progress
  const overallProgress = useMemo(() => {
    if (state.totalTasks === 0) return 0;
    return Math.round((state.completedTasks / state.totalTasks) * 100);
  }, [state.completedTasks, state.totalTasks]);

  // Determine if execution is active
  const isActive = !['idle', 'settled', 'failed'].includes(state.phase);

  if (compact) {
    return (
      <div
        className={`
          flex items-center gap-3 px-3 py-2 rounded-lg
          ${phaseConfig.bgColor} border border-gray-700
        `}
        role="status"
        aria-live="polite"
        aria-label="Execution status"
      >
        <span className={`${phaseConfig.color}`}>{phaseConfig.icon}</span>
        <span className={`text-sm font-medium ${phaseConfig.color}`}>
          {phaseConfig.label}
        </span>
        {state.pacId && (
          <span className="text-xs font-mono text-gray-500">{state.pacId}</span>
        )}
        {isActive && (
          <span className="text-xs text-gray-500">
            {state.activeAgents}/{state.totalAgents} agents
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className={`
        ${phaseConfig.bgColor} border border-gray-700 rounded-lg
        ${state.error ? 'border-red-700' : ''}
        ${state.warning ? 'border-yellow-700' : ''}
      `}
      role="status"
      aria-live="polite"
      aria-label="Execution state banner"
    >
      {/* Error/Warning alerts */}
      {state.error && (
        <div className="bg-red-900/50 border-b border-red-700 px-4 py-2 text-sm text-red-400" role="alert">
          <span className="font-medium">Error:</span> {state.error}
        </div>
      )}
      {state.warning && !state.error && (
        <div className="bg-yellow-900/50 border-b border-yellow-700 px-4 py-2 text-sm text-yellow-400" role="alert">
          <span className="font-medium">Warning:</span> {state.warning}
        </div>
      )}

      {/* Main content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Left: Status info */}
          <div className="flex items-center gap-4">
            {/* Phase indicator */}
            <div className={`
              w-12 h-12 rounded-lg flex items-center justify-center text-2xl
              ${phaseConfig.bgColor} border ${phaseConfig.color.replace('text-', 'border-')}
            `}>
              {phaseConfig.icon}
            </div>

            {/* Details */}
            <div>
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold ${phaseConfig.color}`}>
                  {phaseConfig.label}
                </span>
                {isActive && (
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                )}
              </div>
              {state.pacId ? (
                <div className="text-sm">
                  <span className="font-mono text-blue-400">{state.pacId}</span>
                  {state.pacTitle && (
                    <span className="text-gray-500 ml-2">— {state.pacTitle}</span>
                  )}
                </div>
              ) : (
                <div className="text-sm text-gray-500">{phaseConfig.description}</div>
              )}
            </div>
          </div>

          {/* Right: Stats & Actions */}
          <div className="flex items-center gap-4">
            {/* Stats */}
            {isActive && (
              <div className="flex items-center gap-6 text-sm">
                <div className="text-center">
                  <div className="text-gray-500">Agents</div>
                  <div className="font-bold text-gray-200">
                    {state.activeAgents}/{state.totalAgents}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-gray-500">Tasks</div>
                  <div className="font-bold text-gray-200">
                    {state.completedTasks}/{state.totalTasks}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-gray-500">Progress</div>
                  <div className="font-bold text-gray-200">{overallProgress}%</div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2">
              {onViewTimeline && (
                <button
                  onClick={onViewTimeline}
                  className="px-3 py-1.5 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  📊 Timeline
                </button>
              )}
              {onViewDashboard && (
                <button
                  onClick={onViewDashboard}
                  className="px-3 py-1.5 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  🖥️ Dashboard
                </button>
              )}
              {onEmergencyStop && isActive && (
                <button
                  onClick={onEmergencyStop}
                  className="px-3 py-1.5 text-xs font-medium bg-red-900/50 hover:bg-red-900 text-red-400 border border-red-700 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
                  aria-label="Emergency stop execution"
                >
                  ⏹ Stop
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        {isActive && state.totalTasks > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>Phase: {phaseConfig.description}</span>
              <span>{state.phaseProgress}% complete</span>
            </div>
            <ProgressBar
              progress={state.phaseProgress}
              colorClass={phaseConfig.color.replace('text-', 'bg-')}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
        <span>Last updated: {new Date(state.lastUpdated).toLocaleTimeString()}</span>
        <span>INV-OCC-002: Backend state reflection</span>
      </div>
    </div>
  );
};

export default ExecutionStateBanner;
