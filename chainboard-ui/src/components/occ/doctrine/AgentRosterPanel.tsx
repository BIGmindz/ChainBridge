/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Agent Roster Panel (MANDATORY)
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * DOCTRINE LAW 4, §4.5 — Agent Roster (MANDATORY)
 * 
 * Displays all agents with:
 * - Status per agent (GID registry)
 * - Last PAC executed
 * - Compliance indicator
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-DOC-007: Agent status traceable to backend
 * 
 * Author: SONNY (GID-02) — UI Implementation Lead
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type { 
  AgentRosterEntry, 
  AgentStatus, 
  ComplianceIndicator 
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS CONFIGS (LAW 6 - Visual Invariants)
// ═══════════════════════════════════════════════════════════════════════════════

const AGENT_STATUS_CONFIG: Record<AgentStatus, { icon: string; color: string; bg: string; label: string }> = {
  ACTIVE: { icon: '●', color: 'text-green-400', bg: 'bg-green-500', label: 'Active' },
  IDLE: { icon: '○', color: 'text-gray-400', bg: 'bg-gray-500', label: 'Idle' },
  BLOCKED: { icon: '◐', color: 'text-red-400', bg: 'bg-red-500', label: 'Blocked' },
  OFFLINE: { icon: '◌', color: 'text-gray-600', bg: 'bg-gray-700', label: 'Offline' },
};

const COMPLIANCE_CONFIG: Record<ComplianceIndicator, { icon: string; color: string; label: string }> = {
  COMPLIANT: { icon: '✓', color: 'text-green-400', label: 'Compliant' },
  WARNING: { icon: '⚠', color: 'text-yellow-400', label: 'Warning' },
  VIOLATION: { icon: '✗', color: 'text-red-400', label: 'Violation' },
};

// Known agent colors for visual distinction
const AGENT_COLORS: Record<string, string> = {
  'GID-00': 'border-l-purple-500',  // BENSON
  'GID-01': 'border-l-blue-500',    // CODY
  'GID-02': 'border-l-green-500',   // SONNY
  'GID-03': 'border-l-cyan-500',    // Research Benson
  'GID-05': 'border-l-orange-500',  // PAX
  'GID-06': 'border-l-red-500',     // SAM
  'GID-07': 'border-l-yellow-500',  // DAN
  'GID-08': 'border-l-pink-500',    // ALEX
  'GID-09': 'border-l-indigo-500',  // LIRA
  'GID-10': 'border-l-teal-500',    // MAGGIE
  'GID-11': 'border-l-emerald-500', // ATLAS
};

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT ROW COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentRowProps {
  agent: AgentRosterEntry;
  isExpanded: boolean;
  onToggle: () => void;
}

const AgentRow: React.FC<AgentRowProps> = ({ agent, isExpanded, onToggle }) => {
  const statusConfig = AGENT_STATUS_CONFIG[agent.status];
  const complianceConfig = COMPLIANCE_CONFIG[agent.complianceIndicator];
  const borderColor = AGENT_COLORS[agent.gid] ?? 'border-l-gray-500';

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onToggle();
      }
    },
    [onToggle]
  );

  return (
    <div className={`border-l-4 ${borderColor} bg-gray-800 rounded-r-lg overflow-hidden`}>
      {/* Main Row */}
      <button
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-750 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset"
        aria-expanded={isExpanded}
        aria-controls={`agent-details-${agent.gid}`}
      >
        <div className="flex items-center gap-3">
          {/* Status Indicator */}
          <span 
            className={`w-3 h-3 rounded-full ${statusConfig.bg} ${
              agent.status === 'ACTIVE' ? 'animate-pulse' : ''
            }`}
            aria-hidden="true"
          />
          
          {/* Agent Identity */}
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-200">{agent.name}</span>
              <span className="text-xs text-gray-500 font-mono">{agent.gid}</span>
            </div>
            <span className={`text-xs ${statusConfig.color}`}>{statusConfig.label}</span>
          </div>
        </div>

        {/* Compliance Badge */}
        <div className="flex items-center gap-3">
          <span 
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs ${complianceConfig.color}`}
            role="status"
            aria-label={`Compliance: ${complianceConfig.label}`}
          >
            <span aria-hidden="true">{complianceConfig.icon}</span>
            {complianceConfig.label}
          </span>

          {/* Task Counts */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500">
              {agent.tasksCompleted} done
            </span>
            {agent.tasksPending > 0 && (
              <span className="text-yellow-400">
                {agent.tasksPending} pending
              </span>
            )}
          </div>

          {/* Expand Icon */}
          <span className={`text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div 
          id={`agent-details-${agent.gid}`}
          className="px-4 pb-4 pt-2 border-t border-gray-700 bg-gray-850"
        >
          <div className="grid grid-cols-2 gap-4 text-sm">
            {/* Last PAC */}
            <div>
              <span className="text-gray-500">Last PAC Executed:</span>
              {agent.lastPacExecuted ? (
                <div className="mt-1">
                  <code className="text-xs text-blue-400 font-mono">{agent.lastPacExecuted}</code>
                  {agent.lastPacTimestamp && (
                    <div className="text-xs text-gray-500">
                      {new Date(agent.lastPacTimestamp).toLocaleString()}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-xs text-gray-500 mt-1">No PAC executed</div>
              )}
            </div>

            {/* Task Stats */}
            <div>
              <span className="text-gray-500">Task Statistics:</span>
              <div className="mt-1 flex gap-4">
                <div className="flex items-center gap-1">
                  <span className="text-green-400">✓</span>
                  <span className="text-gray-300">{agent.tasksCompleted}</span>
                  <span className="text-xs text-gray-500">completed</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-yellow-400">⏳</span>
                  <span className="text-gray-300">{agent.tasksPending}</span>
                  <span className="text-xs text-gray-500">pending</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentRosterPanelProps {
  /** Agent roster entries from backend */
  agents: AgentRosterEntry[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to refresh */
  onRefresh: () => void;
}

export const AgentRosterPanel: React.FC<AgentRosterPanelProps> = ({
  agents,
  isLoading,
  error,
  onRefresh,
}) => {
  const [expandedGid, setExpandedGid] = useState<string | null>(null);

  const handleToggle = useCallback((gid: string) => {
    setExpandedGid((prev) => (prev === gid ? null : gid));
  }, []);

  // Calculate summary stats
  const activeCount = agents.filter((a) => a.status === 'ACTIVE').length;
  const blockedCount = agents.filter((a) => a.status === 'BLOCKED').length;
  const violationCount = agents.filter((a) => a.complianceIndicator === 'VIOLATION').length;

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && agents.length === 0) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-6"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <span className="animate-spin">⟳</span>
          <span>Loading agent roster...</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Error State
  // ═══════════════════════════════════════════════════════════════════════════
  if (error) {
    return (
      <div 
        className="bg-red-900/20 border border-red-700 rounded-lg p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <span>✗</span>
            <span>Agent Roster Error: {error}</span>
          </div>
          <button
            onClick={onRefresh}
            className="px-3 py-1 bg-red-700 hover:bg-red-600 text-white text-sm rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="roster-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 id="roster-title" className="text-lg font-semibold text-gray-100">
              Agent Roster
            </h2>
            <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
              {agents.length} agents
            </span>
          </div>

          {/* Summary Stats */}
          <div className="flex items-center gap-4 text-xs">
            <span className="text-green-400">
              {activeCount} active
            </span>
            {blockedCount > 0 && (
              <span className="text-red-400">
                {blockedCount} blocked
              </span>
            )}
            {violationCount > 0 && (
              <span className="px-2 py-0.5 bg-red-900/50 text-red-400 rounded">
                {violationCount} violations
              </span>
            )}
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
              aria-label="Refresh agent roster"
            >
              ⟳
            </button>
          </div>
        </div>
      </header>

      {/* Agent List */}
      <div className="p-4 space-y-2 max-h-[500px] overflow-y-auto">
        {agents.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No agents registered.
          </div>
        ) : (
          agents.map((agent) => (
            <AgentRow
              key={agent.gid}
              agent={agent}
              isExpanded={expandedGid === agent.gid}
              onToggle={() => handleToggle(agent.gid)}
            />
          ))
        )}
      </div>
    </section>
  );
};

export default AgentRosterPanel;
