/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Lane Grid Component — Agent Tiles with Health States
 * PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
 * 
 * Displays agent tiles in a grid layout showing:
 * - Agent identity (GID, name, lane)
 * - Health state (visual indicators)
 * - Execution state
 * - Active PAC binding
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display, no agent control
 * - INV-UI-001: No optimistic state rendering
 * 
 * Author: SONNY (GID-02) — Frontend
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useCallback } from 'react';
import type { AgentLaneTile, AgentHealthState, AgentExecutionState } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const HEALTH_STATE_CONFIG: Record<AgentHealthState, { color: string; label: string; icon: string }> = {
  HEALTHY: { color: 'bg-green-500', label: 'Healthy', icon: '●' },
  DEGRADED: { color: 'bg-yellow-500', label: 'Degraded', icon: '◐' },
  UNHEALTHY: { color: 'bg-red-500', label: 'Unhealthy', icon: '○' },
  OFFLINE: { color: 'bg-gray-600', label: 'Offline', icon: '◌' },
  UNKNOWN: { color: 'bg-gray-500', label: 'Unknown', icon: '?' },
};

const EXECUTION_STATE_CONFIG: Record<AgentExecutionState, { color: string; label: string }> = {
  IDLE: { color: 'text-gray-400', label: 'Idle' },
  EXECUTING: { color: 'text-blue-400', label: 'Executing' },
  BLOCKED: { color: 'text-red-400', label: 'Blocked' },
  COMPLETED: { color: 'text-green-400', label: 'Completed' },
  FAILED: { color: 'text-red-500', label: 'Failed' },
  AWAITING_ACK: { color: 'text-yellow-400', label: 'Awaiting ACK' },
};

const LANE_COLORS: Record<string, string> = {
  orchestration: 'border-l-purple-500',
  backend: 'border-l-blue-500',
  frontend: 'border-l-green-500',
  ci_cd: 'border-l-orange-500',
  security: 'border-l-red-500',
  governance: 'border-l-yellow-500',
  repo_integrity: 'border-l-cyan-500',
  accessibility: 'border-l-pink-500',
  observer: 'border-l-gray-500',
};

// ═══════════════════════════════════════════════════════════════════════════════
// HEALTH INDICATOR COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface HealthIndicatorProps {
  state: AgentHealthState;
}

const HealthIndicator: React.FC<HealthIndicatorProps> = ({ state }) => {
  const config = HEALTH_STATE_CONFIG[state];
  
  return (
    <div
      className="flex items-center gap-1.5"
      role="status"
      aria-label={`Health: ${config.label}`}
    >
      <span
        className={`w-2.5 h-2.5 rounded-full ${config.color} ${
          state === 'EXECUTING' ? 'animate-pulse' : ''
        }`}
        aria-hidden="true"
      />
      <span className="sr-only">{config.label}</span>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// EXECUTION STATE BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface ExecutionStateBadgeProps {
  state: AgentExecutionState;
}

const ExecutionStateBadge: React.FC<ExecutionStateBadgeProps> = ({ state }) => {
  const config = EXECUTION_STATE_CONFIG[state];
  
  return (
    <span
      className={`text-xs font-medium ${config.color}`}
      role="status"
      aria-label={`Execution state: ${config.label}`}
    >
      {config.label}
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT TILE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentTileProps {
  agent: AgentLaneTile;
  isSelected?: boolean;
  onSelect?: (gid: string) => void;
}

const AgentTile: React.FC<AgentTileProps> = ({
  agent,
  isSelected = false,
  onSelect,
}) => {
  const laneColor = LANE_COLORS[agent.lane] || 'border-l-gray-500';
  
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === 'Enter' || e.key === ' ') && onSelect) {
        e.preventDefault();
        onSelect(agent.gid);
      }
    },
    [agent.gid, onSelect]
  );

  return (
    <div
      className={`
        bg-gray-800 border border-gray-700 rounded-lg p-3
        border-l-4 ${laneColor}
        ${isSelected ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-900' : ''}
        ${onSelect ? 'cursor-pointer hover:bg-gray-750 focus:outline-none focus:ring-2 focus:ring-blue-500' : ''}
        transition-all duration-150
      `}
      role="article"
      aria-label={`Agent ${agent.name} (${agent.gid})`}
      aria-selected={isSelected}
      tabIndex={onSelect ? 0 : -1}
      onClick={() => onSelect?.(agent.gid)}
      onKeyDown={handleKeyDown}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <HealthIndicator state={agent.healthState} />
          <span className="font-bold text-gray-100 text-sm">{agent.name}</span>
          <span className="text-xs text-gray-500 font-mono">{agent.gid}</span>
        </div>
        <ExecutionStateBadge state={agent.executionState} />
      </div>

      {/* Lane Badge */}
      <div className="mb-2">
        <span className="text-xs text-gray-400 capitalize">{agent.lane.replace('_', ' ')}</span>
      </div>

      {/* Active PAC (if any) */}
      {agent.activePacId && (
        <div className="mb-2">
          <span className="text-xs text-gray-500">Active: </span>
          <span className="text-xs text-blue-400 font-mono">{agent.activePacId}</span>
        </div>
      )}

      {/* Stats Row */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          {agent.pendingAcks > 0 && (
            <span
              className="text-yellow-400"
              aria-label={`${agent.pendingAcks} pending acknowledgments`}
            >
              ACK: {agent.pendingAcks}
            </span>
          )}
          <span aria-label={`${agent.completedTasks} completed tasks`}>
            ✓ {agent.completedTasks}
          </span>
        </div>
        {agent.lastHeartbeat && (
          <span
            className="text-gray-600 font-mono"
            aria-label="Last heartbeat"
            title={agent.lastHeartbeat}
          >
            {formatRelativeTime(agent.lastHeartbeat)}
          </span>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// LANE GRID COMPONENT (MAIN EXPORT)
// ═══════════════════════════════════════════════════════════════════════════════

interface LaneGridProps {
  /** Agent tiles to display */
  agents: AgentLaneTile[];
  /** Currently selected agent GID */
  selectedAgentGid?: string | null;
  /** Callback when agent is selected */
  onSelectAgent?: (gid: string) => void;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
}

export const LaneGrid: React.FC<LaneGridProps> = ({
  agents,
  selectedAgentGid = null,
  onSelectAgent,
  loading = false,
  error = null,
}) => {
  // Group agents by lane
  const agentsByLane = React.useMemo(() => {
    const grouped: Record<string, AgentLaneTile[]> = {};
    agents.forEach((agent) => {
      if (!grouped[agent.lane]) {
        grouped[agent.lane] = [];
      }
      grouped[agent.lane].push(agent);
    });
    return grouped;
  }, [agents]);

  // Calculate health summary
  const healthSummary = React.useMemo(() => {
    const healthy = agents.filter((a) => a.healthState === 'HEALTHY').length;
    const degraded = agents.filter((a) => a.healthState === 'DEGRADED').length;
    const unhealthy = agents.filter((a) => a.healthState === 'UNHEALTHY').length;
    const offline = agents.filter((a) => a.healthState === 'OFFLINE').length;
    return { healthy, degraded, unhealthy, offline, total: agents.length };
  }, [agents]);

  if (error) {
    return (
      <div
        className="bg-gray-800 border border-red-700 rounded-lg p-4"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span aria-hidden="true">🛑</span>
          <span className="font-medium">Lane Grid Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg"
      aria-label="Agent Lane Grid"
    >
      {/* Header */}
      <div className="border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg" aria-hidden="true">🎯</span>
            <div>
              <h2 className="text-lg font-bold text-gray-100">Agent Lanes</h2>
              <p className="text-xs text-gray-500">
                Real-time agent health and execution states
              </p>
            </div>
          </div>

          {/* Health Summary */}
          <div
            className="flex items-center gap-4 text-xs"
            role="status"
            aria-label="Health summary"
          >
            <span className="text-green-400">● {healthSummary.healthy} healthy</span>
            {healthSummary.degraded > 0 && (
              <span className="text-yellow-400">◐ {healthSummary.degraded} degraded</span>
            )}
            {healthSummary.unhealthy > 0 && (
              <span className="text-red-400">○ {healthSummary.unhealthy} unhealthy</span>
            )}
            {healthSummary.offline > 0 && (
              <span className="text-gray-500">◌ {healthSummary.offline} offline</span>
            )}
          </div>
        </div>
      </div>

      {/* Grid Content */}
      <div className="p-4">
        {loading ? (
          <div
            className="flex items-center justify-center py-8"
            role="status"
            aria-label="Loading agents"
          >
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            <span className="sr-only">Loading agent data...</span>
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <span aria-hidden="true">📭</span>
            <p className="mt-2">No agents registered</p>
          </div>
        ) : (
          <div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3"
            role="list"
            aria-label="Agent tiles"
          >
            {Object.entries(agentsByLane).map(([lane, laneAgents]) => (
              <React.Fragment key={lane}>
                {laneAgents.map((agent) => (
                  <AgentTile
                    key={agent.gid}
                    agent={agent}
                    isSelected={selectedAgentGid === agent.gid}
                    onSelect={onSelectAgent}
                  />
                ))}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatRelativeTime(isoTimestamp: string): string {
  const now = Date.now();
  const then = new Date(isoTimestamp).getTime();
  const diffSeconds = Math.floor((now - then) / 1000);

  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
  return `${Math.floor(diffSeconds / 86400)}d ago`;
}

export default LaneGrid;
