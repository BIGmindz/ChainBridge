/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Agent Drilldown — Agent History, Failures, Evidence Display
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Detailed agent view with:
 * - Overview with health and metrics
 * - Execution history
 * - Failure records
 * - Evidence artifacts
 * - Performance charts
 * 
 * INVARIANTS:
 * - INV-OCC-005: Evidence immutability visible
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type {
  AgentDrilldownState,
  AgentDrilldownTab,
  AgentExecutionRecord,
  AgentFailureRecord,
  AgentEvidenceArtifact,
  AgentPerformanceMetrics,
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const TAB_CONFIG: Record<AgentDrilldownTab, { label: string; icon: string }> = {
  overview: { label: 'Overview', icon: '📊' },
  executions: { label: 'Executions', icon: '⚙️' },
  failures: { label: 'Failures', icon: '❌' },
  evidence: { label: 'Evidence', icon: '📁' },
  metrics: { label: 'Metrics', icon: '📈' },
};

const HEALTH_CONFIG = {
  healthy: { color: 'text-green-400', bg: 'bg-green-900/30', icon: '🟢' },
  degraded: { color: 'text-yellow-400', bg: 'bg-yellow-900/30', icon: '🟡' },
  critical: { color: 'text-red-400', bg: 'bg-red-900/30', icon: '🔴' },
  unknown: { color: 'text-gray-400', bg: 'bg-gray-700', icon: '⚪' },
};

const EXECUTION_STATUS_CONFIG = {
  success: { color: 'text-green-400', bg: 'bg-green-900/30', icon: '✓' },
  partial_success: { color: 'text-yellow-400', bg: 'bg-yellow-900/30', icon: '◐' },
  failed: { color: 'text-red-400', bg: 'bg-red-900/30', icon: '✗' },
  blocked: { color: 'text-orange-400', bg: 'bg-orange-900/30', icon: '⏸' },
  cancelled: { color: 'text-gray-400', bg: 'bg-gray-700', icon: '○' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

function formatTimestamp(ts: string): string {
  return new Date(ts).toLocaleString();
}

function truncateHash(hash: string, len = 8): string {
  if (!hash || hash.length <= len * 2) return hash;
  return `${hash.slice(0, len)}...${hash.slice(-len)}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// OVERVIEW TAB
// ═══════════════════════════════════════════════════════════════════════════════

interface OverviewTabProps {
  state: AgentDrilldownState;
}

const OverviewTab: React.FC<OverviewTabProps> = ({ state }) => {
  const healthConfig = HEALTH_CONFIG[state.health];

  return (
    <div className="space-y-4">
      {/* Health & Status */}
      <div className={`p-4 rounded-lg ${healthConfig.bg}`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">{healthConfig.icon}</span>
          <div>
            <h4 className={`font-medium ${healthConfig.color}`}>
              {state.health.toUpperCase()}
            </h4>
            <p className="text-sm text-gray-400">
              {state.executionState === 'executing'
                ? `Executing ${state.currentPacId}`
                : state.executionState.replace('_', ' ')}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-800 rounded-lg p-3">
          <span className="text-xs text-gray-500">Success Rate</span>
          <div className="text-xl font-bold text-green-400">
            {state.metrics.successRate.toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <span className="text-xs text-gray-500">Avg Task Duration</span>
          <div className="text-xl font-bold text-blue-400">
            {formatDuration(state.metrics.avgTaskDurationMs)}
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <span className="text-xs text-gray-500">Total Tasks</span>
          <div className="text-xl font-bold text-gray-100">
            {state.metrics.totalTasksCompleted}
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <span className="text-xs text-gray-500">PACs Participated</span>
          <div className="text-xl font-bold text-gray-100">
            {state.metrics.totalPacsParticipated}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      {state.recentExecutions.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Recent Activity</h4>
          <div className="space-y-2">
            {state.recentExecutions.slice(0, 3).map((exec) => {
              const statusConfig = EXECUTION_STATUS_CONFIG[exec.status];
              return (
                <div key={exec.executionId} className="flex items-center gap-2 text-sm">
                  <span className={statusConfig.color}>{statusConfig.icon}</span>
                  <span className="text-gray-300 truncate flex-1">{exec.pacTitle}</span>
                  <span className="text-gray-500 text-xs">
                    {new Date(exec.startedAt).toLocaleDateString()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// EXECUTIONS TAB
// ═══════════════════════════════════════════════════════════════════════════════

interface ExecutionsTabProps {
  executions: AgentExecutionRecord[];
  onSelect?: (execution: AgentExecutionRecord) => void;
}

const ExecutionsTab: React.FC<ExecutionsTabProps> = ({ executions, onSelect }) => {
  if (executions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No execution history available
      </div>
    );
  }

  return (
    <div className="space-y-2" role="list" aria-label="Execution history">
      {executions.map((exec) => {
        const statusConfig = EXECUTION_STATUS_CONFIG[exec.status];
        return (
          <button
            key={exec.executionId}
            onClick={() => onSelect?.(exec)}
            className={`
              w-full text-left p-3 rounded-lg border-l-4 transition-colors
              bg-gray-800 hover:bg-gray-750
              ${statusConfig.color.replace('text-', 'border-')}
            `}
            aria-label={`${exec.pacTitle} - ${exec.status}`}
          >
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={statusConfig.color}>{statusConfig.icon}</span>
                  <span className="font-medium text-gray-200 truncate">
                    {exec.pacTitle}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  <span className="font-mono">{exec.pacId}</span>
                </div>
              </div>
              <div className="text-right text-xs">
                <div className="text-gray-400">
                  {formatTimestamp(exec.startedAt)}
                </div>
                {exec.durationMs && (
                  <div className="text-gray-500">
                    {formatDuration(exec.durationMs)}
                  </div>
                )}
              </div>
            </div>

            {/* Task progress */}
            <div className="mt-2 flex items-center gap-4 text-xs">
              <span className="text-green-400">
                ✓ {exec.tasksCompleted} completed
              </span>
              {exec.tasksFailed > 0 && (
                <span className="text-red-400">
                  ✗ {exec.tasksFailed} failed
                </span>
              )}
            </div>

            {/* Evidence hash */}
            <div className="mt-2 text-xs">
              <span className="text-gray-500">Evidence: </span>
              <code className="font-mono text-teal-400">
                {truncateHash(exec.evidenceHash)}
              </code>
            </div>
          </button>
        );
      })}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// FAILURES TAB
// ═══════════════════════════════════════════════════════════════════════════════

interface FailuresTabProps {
  failures: AgentFailureRecord[];
}

const FailuresTab: React.FC<FailuresTabProps> = ({ failures }) => {
  if (failures.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <span className="text-2xl">🎉</span>
        <p className="mt-2">No failures recorded</p>
      </div>
    );
  }

  return (
    <div className="space-y-3" role="list" aria-label="Failure records">
      {failures.map((failure) => (
        <div
          key={failure.failureId}
          className={`
            p-3 rounded-lg border-l-4
            ${failure.resolved ? 'bg-gray-800 border-green-600' : 'bg-red-900/20 border-red-600'}
          `}
        >
          <div className="flex items-start justify-between">
            <div>
              <span className={`
                text-xs px-2 py-0.5 rounded
                ${failure.resolved ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}
              `}>
                {failure.failureType.replace('_', ' ')}
              </span>
              <p className="mt-2 text-sm text-gray-300">{failure.errorMessage}</p>
            </div>
            <span className="text-xs text-gray-500">
              {new Date(failure.timestamp).toLocaleString()}
            </span>
          </div>

          {failure.resolved && failure.resolution && (
            <div className="mt-2 text-xs text-green-400">
              ✓ Resolved: {failure.resolution}
            </div>
          )}

          {failure.stackTrace && (
            <details className="mt-2">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
                Stack trace
              </summary>
              <pre className="mt-1 text-xs font-mono bg-gray-900 p-2 rounded overflow-x-auto text-gray-400">
                {failure.stackTrace}
              </pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// EVIDENCE TAB
// ═══════════════════════════════════════════════════════════════════════════════

interface EvidenceTabProps {
  artifacts: AgentEvidenceArtifact[];
  onSelect?: (artifact: AgentEvidenceArtifact) => void;
}

const EvidenceTab: React.FC<EvidenceTabProps> = ({ artifacts, onSelect }) => {
  if (artifacts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No evidence artifacts available
      </div>
    );
  }

  const typeIcons: Record<string, string> = {
    pdo: '📋',
    file_change: '📄',
    api_call: '🔗',
    command: '⌨️',
    ack: '✅',
    wrap: '📦',
    ber: '📑',
    other: '📎',
  };

  return (
    <div className="space-y-2" role="list" aria-label="Evidence artifacts">
      {artifacts.map((artifact) => (
        <button
          key={artifact.artifactId}
          onClick={() => onSelect?.(artifact)}
          className="w-full text-left p-3 rounded-lg bg-gray-800 hover:bg-gray-750 transition-colors"
        >
          <div className="flex items-start gap-3">
            <span className="text-lg">{typeIcons[artifact.artifactType] || '📎'}</span>
            <div className="min-w-0 flex-1">
              <div className="font-medium text-gray-200 truncate">
                {artifact.title}
              </div>
              <div className="text-sm text-gray-400 truncate">
                {artifact.description}
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs">
                <span className="text-gray-500">
                  {new Date(artifact.timestamp).toLocaleString()}
                </span>
                {artifact.path && (
                  <span className="font-mono text-blue-400 truncate">
                    {artifact.path}
                  </span>
                )}
              </div>
              <div className="mt-1">
                <span className="text-xs text-gray-500">Hash: </span>
                <code className="text-xs font-mono text-teal-400">
                  {truncateHash(artifact.evidenceHash)}
                </code>
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// METRICS TAB
// ═══════════════════════════════════════════════════════════════════════════════

interface MetricsTabProps {
  metrics: AgentPerformanceMetrics;
}

const MetricsTab: React.FC<MetricsTabProps> = ({ metrics }) => {
  return (
    <div className="space-y-4">
      {/* Primary metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-800 rounded-lg p-4">
          <span className="text-xs text-gray-500">Success Rate</span>
          <div className="mt-1 flex items-end gap-2">
            <span className="text-3xl font-bold text-green-400">
              {metrics.successRate.toFixed(1)}%
            </span>
          </div>
          <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full"
              style={{ width: `${metrics.successRate}%` }}
            />
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-4">
          <span className="text-xs text-gray-500">Uptime</span>
          <div className="mt-1 flex items-end gap-2">
            <span className="text-3xl font-bold text-blue-400">
              {metrics.uptimePercent.toFixed(1)}%
            </span>
          </div>
          <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${metrics.uptimePercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Detailed metrics */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Performance Details</h4>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-gray-500">Total PACs</dt>
            <dd className="font-medium text-gray-200">{metrics.totalPacsParticipated}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Tasks Completed</dt>
            <dd className="font-medium text-gray-200">{metrics.totalTasksCompleted}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Tasks Failed</dt>
            <dd className="font-medium text-red-400">{metrics.totalTasksFailed}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Current Streak</dt>
            <dd className="font-medium text-green-400">{metrics.currentStreak}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Avg Task Duration</dt>
            <dd className="font-medium text-gray-200">
              {formatDuration(metrics.avgTaskDurationMs)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500">Avg ACK Latency</dt>
            <dd className="font-medium text-gray-200">
              {formatDuration(metrics.avgAckLatencyMs)}
            </dd>
          </div>
        </dl>
      </div>

      {/* Last active */}
      <div className="text-xs text-gray-500">
        Last active: {formatTimestamp(metrics.lastActiveAt)}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN AGENT DRILLDOWN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentDrilldownProps {
  agentId: string;
  state: AgentDrilldownState | null;
  loading?: boolean;
  error?: string | null;
  onClose?: () => void;
  onExecutionSelect?: (execution: AgentExecutionRecord) => void;
  onArtifactSelect?: (artifact: AgentEvidenceArtifact) => void;
}

export const AgentDrilldown: React.FC<AgentDrilldownProps> = ({
  agentId,
  state,
  loading = false,
  error = null,
  onClose,
  onExecutionSelect,
  onArtifactSelect,
}) => {
  const [activeTab, setActiveTab] = useState<AgentDrilldownTab>('overview');

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose?.();
    }
  }, [onClose]);

  // Error state
  if (error) {
    return (
      <div className="bg-gray-800 border border-red-700 rounded-lg p-4" role="alert">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span>🛑</span>
          <span className="font-medium">Error loading agent data</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  // Loading state
  if (loading && !state) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
          <p className="mt-2 text-sm text-gray-400">Loading agent {agentId}...</p>
        </div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center">
        <p className="text-gray-400">No data available for agent {agentId}</p>
      </div>
    );
  }

  const healthConfig = HEALTH_CONFIG[state.health];

  return (
    <div
      className="bg-gray-900 rounded-lg flex flex-col h-full"
      role="dialog"
      aria-label={`Agent ${state.agentName} details`}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <header className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{healthConfig.icon}</span>
            <div>
              <h2 className="text-lg font-bold text-gray-100">
                {state.agentName}
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({state.agentId})
                </span>
              </h2>
              <div className="text-sm text-gray-400">
                Lane: <span className="text-purple-400">{state.lane}</span>
              </div>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
              aria-label="Close drilldown"
            >
              ✕
            </button>
          )}
        </div>
      </header>

      {/* Tabs */}
      <nav className="flex border-b border-gray-700" role="tablist">
        {(Object.keys(TAB_CONFIG) as AgentDrilldownTab[]).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            className={`
              flex-1 px-3 py-2 text-sm font-medium transition-colors
              focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500
              ${activeTab === tab
                ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-800'
                : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }
            `}
          >
            <span className="mr-1">{TAB_CONFIG[tab].icon}</span>
            {TAB_CONFIG[tab].label}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4" role="tabpanel">
        {activeTab === 'overview' && <OverviewTab state={state} />}
        {activeTab === 'executions' && (
          <ExecutionsTab
            executions={state.recentExecutions}
            onSelect={onExecutionSelect}
          />
        )}
        {activeTab === 'failures' && <FailuresTab failures={state.recentFailures} />}
        {activeTab === 'evidence' && (
          <EvidenceTab
            artifacts={state.recentArtifacts}
            onSelect={onArtifactSelect}
          />
        )}
        {activeTab === 'metrics' && <MetricsTab metrics={state.metrics} />}
      </div>

      {/* Footer */}
      <footer className="p-3 border-t border-gray-700 text-xs text-gray-500">
        Last updated: {formatTimestamp(state.lastUpdated)}
      </footer>
    </div>
  );
};

export default AgentDrilldown;
