/**
 * ChainBridge Agent Execution Page
 * PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
 * 
 * Main page for agent execution visibility in Operator Console.
 * 
 * INVARIANTS:
 * - INV-AGENT-001: Agent activation must be explicit and visible
 * - INV-AGENT-002: Each execution step maps to exactly one agent
 * - INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
 * - INV-AGENT-004: OC is read-only; no agent control actions
 * - INV-AGENT-005: Missing state must be explicit (no inference)
 */

import React, { useEffect, useState } from 'react';
import { ActiveAgentsPanel } from '../components/ActiveAgentsPanel';
import { AgentTimeline } from '../components/AgentTimeline';
import {
  StateBadge,
  StateCountBadge,
  ExecutionStatusBadge,
} from '../components/AgentStateBadges';
import type {
  PACExecutionView,
  PACListItem,
  AgentExecutionView,
} from '../types/agentExecution';
import {
  UNAVAILABLE_MARKER,
  formatTimestamp,
  formatDuration,
  AGENT_COLOR_MAP,
} from '../types/agentExecution';
import {
  fetchPACList,
  fetchPACExecution,
} from '../api/agentExecution';

/**
 * PAC Card Component
 */
const PACCard: React.FC<{
  pac: PACListItem;
  selected: boolean;
  onSelect: () => void;
}> = ({ pac, selected, onSelect }) => {
  return (
    <button
      onClick={onSelect}
      className={`
        w-full text-left p-3 rounded-lg border transition-colors
        ${selected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 bg-white hover:border-gray-300'
        }
      `}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-gray-900 text-sm truncate">{pac.pac_id}</span>
        <ExecutionStatusBadge status={pac.execution_status as any} />
      </div>
      <div className="text-xs text-gray-500">
        {pac.agents_complete}/{pac.total_agents} agents complete
        {pac.agents_failed > 0 && (
          <span className="text-red-500 ml-2">({pac.agents_failed} failed)</span>
        )}
      </div>
      {pac.execution_started_at && (
        <div className="text-xs text-gray-400 mt-1">
          Started: {formatTimestamp(pac.execution_started_at)}
        </div>
      )}
    </button>
  );
};

/**
 * Agent Row Component
 */
const AgentRow: React.FC<{ agent: AgentExecutionView }> = ({ agent }) => {
  const colorClass = AGENT_COLOR_MAP[agent.agent_color] || 'bg-gray-400';
  
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 mb-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${colorClass}`} />
          <span className="font-medium text-gray-900">{agent.agent_name}</span>
          <span className="text-xs text-gray-500">({agent.agent_gid})</span>
          {agent.execution_order !== null && (
            <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">
              Order {agent.execution_order}
            </span>
          )}
        </div>
        <StateBadge state={agent.current_state} />
      </div>
      
      <div className="mt-2 text-sm text-gray-600">{agent.agent_role}</div>
      
      {agent.order_description !== UNAVAILABLE_MARKER && (
        <div className="mt-1 text-sm text-gray-700 bg-gray-50 rounded p-2">
          {agent.order_description}
        </div>
      )}
      
      <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
        <span>Mode: {agent.execution_mode}</span>
        {agent.duration_ms !== null && (
          <span>Duration: {formatDuration(agent.duration_ms)}</span>
        )}
        {agent.artifacts_created.length > 0 && (
          <span>{agent.artifacts_created.length} artifacts</span>
        )}
      </div>
      
      {agent.error_message && (
        <div className="mt-2 text-sm text-red-600 bg-red-50 rounded p-2">
          Error: {agent.error_message}
        </div>
      )}
    </div>
  );
};

/**
 * PAC Detail Panel Component
 */
const PACDetailPanel: React.FC<{ pacId: string }> = ({ pacId }) => {
  const [execution, setExecution] = useState<PACExecutionView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'agents' | 'timeline'>('agents');
  
  useEffect(() => {
    const loadExecution = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchPACExecution(pacId);
        setExecution(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };
    
    loadExecution();
  }, [pacId]);
  
  if (loading) {
    return (
      <div className="text-center py-8 text-gray-500">Loading PAC execution...</div>
    );
  }
  
  if (error || !execution) {
    return (
      <div className="text-center py-8 text-red-500">
        Error: {error || 'Failed to load execution'}
      </div>
    );
  }
  
  return (
    <div>
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900">{execution.pac_id}</h2>
          <ExecutionStatusBadge status={execution.execution_status as any} />
        </div>
        <StateCountBadge
          queued={execution.agents_queued}
          active={execution.agents_active}
          complete={execution.agents_complete}
          failed={execution.agents_failed}
        />
      </div>
      
      {/* View Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setView('agents')}
          className={`px-4 py-2 text-sm rounded-lg transition-colors ${
            view === 'agents'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Agents ({execution.total_agents})
        </button>
        <button
          onClick={() => setView('timeline')}
          className={`px-4 py-2 text-sm rounded-lg transition-colors ${
            view === 'timeline'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Timeline ({execution.timeline.length})
        </button>
      </div>
      
      {/* Content */}
      {view === 'agents' ? (
        <div>
          {execution.agents.map((agent) => (
            <AgentRow key={agent.agent_gid} agent={agent} />
          ))}
          {execution.agents.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No agents found for this PAC.
            </div>
          )}
        </div>
      ) : (
        <AgentTimeline events={execution.timeline} />
      )}
    </div>
  );
};

/**
 * Main Agent Execution Page
 */
export const AgentExecutionPage: React.FC = () => {
  const [pacs, setPacs] = useState<PACListItem[]>([]);
  const [selectedPac, setSelectedPac] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const loadPacs = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetchPACList();
        setPacs(response.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };
    
    loadPacs();
  }, []);
  
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              Agent Execution Visibility
            </h1>
            <p className="text-sm text-gray-500">
              Operator Console — PAC-008
            </p>
          </div>
          <span className="bg-yellow-100 text-yellow-800 text-xs px-3 py-1 rounded-full font-medium">
            READ-ONLY OPERATOR VIEW
          </span>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="p-6">
        {/* Active Agents Panel */}
        <div className="mb-6">
          <ActiveAgentsPanel />
        </div>
        
        {/* PAC List & Detail */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* PAC List */}
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              PAC Executions
            </h2>
            
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : error ? (
              <div className="text-center py-8 text-red-500">Error: {error}</div>
            ) : pacs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No PAC executions recorded.
              </div>
            ) : (
              <div className="space-y-2">
                {pacs.map((pac) => (
                  <PACCard
                    key={pac.pac_id}
                    pac={pac}
                    selected={selectedPac === pac.pac_id}
                    onSelect={() => setSelectedPac(pac.pac_id)}
                  />
                ))}
              </div>
            )}
          </div>
          
          {/* PAC Detail */}
          <div className="lg:col-span-2 bg-white rounded-lg p-4 shadow-sm">
            {selectedPac ? (
              <PACDetailPanel pacId={selectedPac} />
            ) : (
              <div className="text-center py-16 text-gray-500">
                Select a PAC to view execution details
              </div>
            )}
          </div>
        </div>
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 px-6 py-3 text-center text-xs text-gray-500">
        INV-AGENT-004: Operator Console is read-only. No control actions permitted.
      </footer>
    </div>
  );
};

export default AgentExecutionPage;
