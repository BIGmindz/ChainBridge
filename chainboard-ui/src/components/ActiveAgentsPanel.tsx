/**
 * ChainBridge Active Agents Panel
 * PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
 * 
 * OC panel showing currently active agents across all PACs.
 * 
 * INVARIANTS:
 * - INV-AGENT-004: OC is read-only; no agent control actions
 * - No buttons that modify agent state
 */

import React, { useEffect, useState } from 'react';
import type { AgentExecutionView } from '../types/agentExecution';
import {
  STATE_COLORS,
  STATE_LABELS,
  AGENT_COLOR_MAP,
  formatDuration,
  formatTimestamp,
  UNAVAILABLE_MARKER,
} from '../types/agentExecution';
import { fetchActiveAgents } from '../api/agentExecution';

/**
 * Agent state badge component
 */
const StateBadge: React.FC<{ state: string }> = ({ state }) => {
  const colorClass = STATE_COLORS[state as keyof typeof STATE_COLORS] || 'bg-gray-500';
  const label = STATE_LABELS[state as keyof typeof STATE_LABELS] || state;
  
  return (
    <span className={`${colorClass} text-white text-xs px-2 py-1 rounded-full font-medium`}>
      {label}
    </span>
  );
};

/**
 * Agent color indicator
 */
const AgentColorIndicator: React.FC<{ color: string }> = ({ color }) => {
  const colorClass = AGENT_COLOR_MAP[color] || 'bg-gray-400';
  
  return (
    <div className={`w-3 h-3 rounded-full ${colorClass}`} title={color} />
  );
};

/**
 * Single agent card in the active agents panel
 */
const AgentCard: React.FC<{ agent: AgentExecutionView }> = ({ agent }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <AgentColorIndicator color={agent.agent_color} />
          <span className="font-semibold text-gray-900">{agent.agent_name}</span>
          <span className="text-xs text-gray-500">({agent.agent_gid})</span>
        </div>
        <StateBadge state={agent.current_state} />
      </div>
      
      {/* Role */}
      <div className="text-sm text-gray-600 mb-2">{agent.agent_role}</div>
      
      {/* PAC & Order */}
      <div className="text-xs text-gray-500 mb-2">
        <span className="font-medium">PAC:</span> {agent.pac_id}
        {agent.execution_order !== null && (
          <span className="ml-2">
            <span className="font-medium">Order:</span> {agent.execution_order}
          </span>
        )}
      </div>
      
      {/* Order Description */}
      {agent.order_description !== UNAVAILABLE_MARKER && (
        <div className="text-sm text-gray-700 bg-gray-50 rounded p-2 mb-2">
          {agent.order_description}
        </div>
      )}
      
      {/* Timing */}
      <div className="text-xs text-gray-500 space-y-1">
        {agent.started_at && (
          <div>
            <span className="font-medium">Started:</span> {formatTimestamp(agent.started_at)}
          </div>
        )}
        {agent.duration_ms !== null && (
          <div>
            <span className="font-medium">Duration:</span> {formatDuration(agent.duration_ms)}
          </div>
        )}
      </div>
      
      {/* Artifacts (if any) */}
      {agent.artifacts_created.length > 0 && (
        <div className="mt-2">
          <div className="text-xs font-medium text-gray-600">Artifacts:</div>
          <div className="flex flex-wrap gap-1 mt-1">
            {agent.artifacts_created.map((artifact, idx) => (
              <span
                key={idx}
                className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded"
              >
                {artifact}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Ledger Hash */}
      {agent.ledger_entry_hash !== UNAVAILABLE_MARKER && (
        <div className="mt-2 text-xs text-gray-400 font-mono truncate" title={agent.ledger_entry_hash}>
          Hash: {agent.ledger_entry_hash.substring(0, 16)}...
        </div>
      )}
    </div>
  );
};

/**
 * Active Agents Panel Component
 */
export const ActiveAgentsPanel: React.FC = () => {
  const [agents, setAgents] = useState<AgentExecutionView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const loadAgents = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetchActiveAgents();
        setAgents(response.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load agents');
      } finally {
        setLoading(false);
      }
    };
    
    loadAgents();
    
    // Poll every 5 seconds for updates
    const interval = setInterval(loadAgents, 5000);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Active Agents</h2>
        <span className="text-xs text-gray-500 bg-yellow-100 px-2 py-1 rounded">
          READ-ONLY VIEW
        </span>
      </div>
      
      {/* Content */}
      {loading && agents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          Loading active agents...
        </div>
      ) : error ? (
        <div className="text-center py-8 text-red-500">
          Error: {error}
        </div>
      ) : agents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No active agents at this time.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={`${agent.pac_id}-${agent.agent_gid}`} agent={agent} />
          ))}
        </div>
      )}
      
      {/* Footer */}
      <div className="mt-4 text-xs text-gray-400 text-center">
        INV-AGENT-004: Operator Console is read-only. No control actions permitted.
      </div>
    </div>
  );
};

export default ActiveAgentsPanel;
