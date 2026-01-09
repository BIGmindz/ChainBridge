/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC Dashboard — Main Operator Control Center Component
 * PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
 * 
 * Integrates all OCC panels:
 * - Lane Grid (agent tiles with health states)
 * - Decision Stream (PDO cards + BER actions)
 * - Governance Rail (active invariants visible)
 * - Kill Switch UI (disabled unless authorized)
 * 
 * INVARIANTS:
 * - INV-OCC-001: No mutation routes - read-only state display
 * - INV-OCC-002: Always reflects backend state (no optimistic rendering)
 * - INV-OCC-003: UI reflects invariant failures with rule IDs
 * - INV-SAM-001: No hidden execution paths
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Security: SAM (GID-06)
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useEffect, useCallback } from 'react';
import { LaneGrid } from './LaneGrid';
import { DecisionStream } from './DecisionStream';
import { GovernanceRail } from './GovernanceRail';
import { KillSwitchUI } from './KillSwitchUI';
import type { OCCDashboardState, AgentLaneTile, DecisionStreamItem, GovernanceRailState, KillSwitchStatus } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// MOCK DATA (Remove when connected to backend)
// ═══════════════════════════════════════════════════════════════════════════════

const MOCK_AGENTS: AgentLaneTile[] = [
  { agentId: 'GID-00', agentName: 'BENSON', lane: 'orchestration', health: 'healthy', executionState: 'executing', currentPacId: 'PAC-BENSON-P21-C', tasksCompleted: 4, tasksPending: 8, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-01', agentName: 'CODY', lane: 'backend', health: 'healthy', executionState: 'idle', currentPacId: null, tasksCompleted: 2, tasksPending: 3, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-02', agentName: 'SONNY', lane: 'frontend', health: 'healthy', executionState: 'executing', currentPacId: 'PAC-BENSON-P21-C', tasksCompleted: 5, tasksPending: 2, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-04', agentName: 'CINDY', lane: 'backend', health: 'healthy', executionState: 'blocked', currentPacId: 'PAC-BENSON-P21-C', tasksCompleted: 1, tasksPending: 2, lastHeartbeat: new Date().toISOString(), blockedReason: 'Waiting for CODY endpoint completion' },
  { agentId: 'GID-06', agentName: 'SAM', lane: 'security', health: 'healthy', executionState: 'idle', currentPacId: null, tasksCompleted: 0, tasksPending: 1, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-07', agentName: 'DAN', lane: 'ci', health: 'healthy', executionState: 'executing', currentPacId: 'PAC-BENSON-P21-C', tasksCompleted: 1, tasksPending: 1, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-08', agentName: 'ALEX', lane: 'governance', health: 'healthy', executionState: 'idle', currentPacId: null, tasksCompleted: 0, tasksPending: 1, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-09', agentName: 'LIRA', lane: 'frontend', health: 'healthy', executionState: 'completed', currentPacId: 'PAC-BENSON-P21-C', tasksCompleted: 3, tasksPending: 0, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-10', agentName: 'MAGGIE', lane: 'ml', health: 'healthy', executionState: 'idle', currentPacId: null, tasksCompleted: 0, tasksPending: 0, lastHeartbeat: new Date().toISOString() },
  { agentId: 'GID-11', agentName: 'ATLAS', lane: 'integrity', health: 'healthy', executionState: 'idle', currentPacId: 'PAC-BENSON-P21-C', tasksCompleted: 1, tasksPending: 1, lastHeartbeat: new Date().toISOString() },
];

const MOCK_DECISIONS: DecisionStreamItem[] = [
  {
    id: 'pdo-001',
    type: 'pdo',
    timestamp: new Date().toISOString(),
    card: {
      pdoId: 'PDO-P21C-001',
      pacId: 'PAC-BENSON-P21-C',
      agentId: 'GID-02',
      agentName: 'SONNY',
      decisionType: 'FILE_CREATE',
      description: 'Create KillSwitchUI.tsx component',
      outcome: 'APPROVED',
      invariantsChecked: ['INV-KILL-001', 'INV-SAM-001'],
      timestamp: new Date().toISOString(),
    },
  },
  {
    id: 'pdo-002',
    type: 'pdo',
    timestamp: new Date(Date.now() - 60000).toISOString(),
    card: {
      pdoId: 'PDO-P21C-002',
      pacId: 'PAC-BENSON-P21-C',
      agentId: 'GID-02',
      agentName: 'SONNY',
      decisionType: 'FILE_CREATE',
      description: 'Create GovernanceRail.tsx component',
      outcome: 'APPROVED',
      invariantsChecked: ['INV-OCC-003', 'INV-ALEX-001'],
      timestamp: new Date(Date.now() - 60000).toISOString(),
    },
  },
];

const MOCK_GOVERNANCE: GovernanceRailState = {
  invariants: [
    { invariantId: 'INV-OCC-001', ruleId: 'RULE-OCC-001', description: 'No mutation routes - read-only state display', class: 'S-INV', status: 'passing', lastChecked: new Date().toISOString(), source: 'SAM' },
    { invariantId: 'INV-OCC-002', ruleId: 'RULE-OCC-002', description: 'Always reflects backend state (no optimistic rendering)', class: 'S-INV', status: 'passing', lastChecked: new Date().toISOString(), source: 'SAM' },
    { invariantId: 'INV-OCC-003', ruleId: 'RULE-OCC-003', description: 'UI reflects invariant failures with rule IDs', class: 'A-INV', status: 'passing', lastChecked: new Date().toISOString(), source: 'ALEX' },
    { invariantId: 'INV-KILL-001', ruleId: 'RULE-KILL-001', description: 'Kill switch DISABLED unless authorized', class: 'X-INV', status: 'passing', lastChecked: new Date().toISOString(), source: 'SAM' },
    { invariantId: 'INV-LIRA-001', ruleId: 'RULE-ACC-001', description: 'ARIA labels on all interactive elements', class: 'A-INV', status: 'passing', lastChecked: new Date().toISOString(), source: 'LIRA' },
  ],
  lintV2Passing: true,
  schemaRegistryValid: true,
  failClosedActive: true,
  lastRefresh: new Date().toISOString(),
};

const MOCK_KILL_SWITCH: KillSwitchStatus = {
  state: 'DISARMED',
  authLevel: 'ARM_ONLY',
  engagedBy: null,
  engagedAt: null,
  engagementReason: null,
  affectedPacs: [],
  cooldownRemaining: null,
};

// ═══════════════════════════════════════════════════════════════════════════════
// OCC HEADER
// ═══════════════════════════════════════════════════════════════════════════════

interface OCCHeaderProps {
  activePac: string | null;
  lastRefresh: string | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

const OCCHeader: React.FC<OCCHeaderProps> = ({
  activePac,
  lastRefresh,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="bg-gray-900 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-gray-100">
            <span className="text-blue-400">OCC</span> Operator Control Center
          </h1>
          {activePac && (
            <span className="px-3 py-1 bg-blue-900/30 border border-blue-700 rounded text-sm text-blue-400 font-mono">
              {activePac}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {lastRefresh && (
            <span className="text-xs text-gray-500">
              Last refresh: {new Date(lastRefresh).toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className={`
              px-3 py-1.5 text-sm font-medium rounded transition-colors
              focus:outline-none focus:ring-2 focus:ring-blue-500
              ${isRefreshing
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            `}
            aria-label="Refresh OCC data"
          >
            {isRefreshing ? '⟳ Refreshing...' : '⟳ Refresh'}
          </button>
        </div>
      </div>
    </header>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CONNECTION STATUS
// ═══════════════════════════════════════════════════════════════════════════════

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

interface ConnectionIndicatorProps {
  status: ConnectionStatus;
}

const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({ status }) => {
  const config: Record<ConnectionStatus, { color: string; label: string }> = {
    connected: { color: 'bg-green-500', label: 'Connected' },
    connecting: { color: 'bg-yellow-500 animate-pulse', label: 'Connecting...' },
    disconnected: { color: 'bg-gray-500', label: 'Disconnected' },
    error: { color: 'bg-red-500', label: 'Connection Error' },
  };

  const { color, label } = config[status];

  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <span className={`w-2 h-2 rounded-full ${color}`} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN OCC DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════════

interface OCCDashboardProps {
  /** Override initial state for testing */
  initialState?: Partial<OCCDashboardState>;
}

export const OCCDashboard: React.FC<OCCDashboardProps> = ({ initialState }) => {
  // State
  const [agents, setAgents] = useState<AgentLaneTile[]>(initialState?.agents || MOCK_AGENTS);
  const [decisions, setDecisions] = useState<DecisionStreamItem[]>(initialState?.decisionStream || MOCK_DECISIONS);
  const [governance, setGovernance] = useState<GovernanceRailState>(initialState?.governanceRail || MOCK_GOVERNANCE);
  const [killSwitch, setKillSwitch] = useState<KillSwitchStatus>(initialState?.killSwitch || MOCK_KILL_SWITCH);

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connected');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string>(new Date().toISOString());
  const [error, setError] = useState<string | null>(null);

  // Active PAC detection
  const activePac = agents.find(a => a.executionState === 'executing')?.currentPacId || null;

  // Refresh handler
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setError(null);

    try {
      // TODO: Replace with actual API calls when CODY completes endpoints
      // const [agentsRes, decisionsRes, governanceRes, killSwitchRes] = await Promise.all([
      //   fetch('/api/occ/agents'),
      //   fetch('/api/occ/decisions'),
      //   fetch('/api/occ/governance'),
      //   fetch('/api/occ/kill-switch'),
      // ]);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Update mock data timestamps
      setAgents(prev => prev.map(a => ({ ...a, lastHeartbeat: new Date().toISOString() })));
      setGovernance(prev => ({ ...prev, lastRefresh: new Date().toISOString() }));
      setLastRefresh(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh OCC data');
      setConnectionStatus('error');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(handleRefresh, 30000);
    return () => clearInterval(interval);
  }, [handleRefresh]);

  // Kill switch handlers (placeholders)
  const handleArm = async () => {
    // TODO: API call
    setKillSwitch(prev => ({ ...prev, state: 'ARMED' }));
  };

  const handleEngage = async (reason: string) => {
    // TODO: API call
    setKillSwitch(prev => ({
      ...prev,
      state: 'ENGAGED',
      engagedBy: 'OPERATOR',
      engagedAt: new Date().toISOString(),
      engagementReason: reason,
      affectedPacs: activePac ? [activePac] : [],
    }));
  };

  const handleDisarm = async () => {
    // TODO: API call
    setKillSwitch(prev => ({
      ...prev,
      state: 'COOLDOWN',
      cooldownRemaining: 30000,
    }));
    // Simulate cooldown
    setTimeout(() => {
      setKillSwitch(prev => ({
        ...prev,
        state: 'DISARMED',
        engagedBy: null,
        engagedAt: null,
        engagementReason: null,
        affectedPacs: [],
        cooldownRemaining: null,
      }));
    }, 30000);
  };

  return (
    <div
      className="flex flex-col h-screen bg-gray-950 text-gray-100"
      role="main"
      aria-label="Operator Control Center Dashboard"
    >
      {/* Header */}
      <OCCHeader
        activePac={activePac}
        lastRefresh={lastRefresh}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Error Banner */}
      {error && (
        <div
          className="bg-red-900/30 border-b border-red-700 px-6 py-3 text-sm text-red-400"
          role="alert"
          aria-live="assertive"
        >
          <span className="font-medium">Error:</span> {error}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-12 gap-4 p-4">
          {/* Left Column: Lane Grid + Kill Switch */}
          <div className="col-span-4 flex flex-col gap-4 overflow-y-auto">
            <LaneGrid agents={agents} loading={isRefreshing} />
            <KillSwitchUI
              status={killSwitch}
              loading={isRefreshing}
              onArm={handleArm}
              onEngage={handleEngage}
              onDisarm={handleDisarm}
            />
          </div>

          {/* Middle Column: Decision Stream */}
          <div className="col-span-5 overflow-y-auto">
            <DecisionStream items={decisions} loading={isRefreshing} />
          </div>

          {/* Right Column: Governance Rail */}
          <div className="col-span-3 overflow-y-auto">
            <GovernanceRail state={governance} loading={isRefreshing} />
          </div>
        </div>
      </div>

      {/* Footer Status Bar */}
      <footer className="bg-gray-900 border-t border-gray-700 px-6 py-2">
        <div className="flex items-center justify-between">
          <ConnectionIndicator status={connectionStatus} />
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>Agents: {agents.length}</span>
            <span>Decisions: {decisions.length}</span>
            <span>Invariants: {governance.invariants.length}</span>
          </div>
          <span className="text-xs text-gray-600 font-mono">
            PAC-BENSON-P21-C | OCC v1.0
          </span>
        </div>
      </footer>
    </div>
  );
};

export default OCCDashboard;
