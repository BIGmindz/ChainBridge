// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust Agent Uniform Inspection Panel
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY agent uniform visualization.
// Displays: GID, role, scope, PAC/ACK/WRAP/BER indicators, compliance status.
//
// DATA SOURCE: gid_registry + lint_v2 uniform invariants
// INVARIANTS:
// - INV-UNIFORM-001: No agent executes without uniform
// - INV-UNIFORM-002: Unknown agents forbidden
// - INV-UNIFORM-003: PAC required for all execution
// - INV-UNIFORM-004: BER required for finality
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type { AgentUniformPanelDTO, AgentUniformStatus } from '../../types/chaintrust';
import { STATUS_COLORS } from '../../types/chaintrust';

interface AgentUniformPanelProps {
  data: AgentUniformPanelDTO | null;
  loading: boolean;
  error: string | null;
}

/**
 * Uniform requirement indicator (PAC/ACK/WRAP/BER).
 */
const UniformIndicator: React.FC<{ label: string; present: boolean }> = ({ label, present }) => (
  <div className={`flex flex-col items-center px-2 py-1 rounded ${present ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
    <span className={`text-xs font-mono ${present ? 'text-green-400' : 'text-red-400'}`}>
      {label}
    </span>
    <span className={`text-lg ${present ? 'text-green-400' : 'text-red-400'}`}>
      {present ? '✓' : '✗'}
    </span>
  </div>
);

/**
 * Single agent row in the uniform inspection panel.
 */
const AgentUniformRow: React.FC<{ agent: AgentUniformStatus }> = ({ agent }) => {
  const complianceColor = agent.uniform_compliant ? STATUS_COLORS.PASS : STATUS_COLORS.FAIL;
  
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-3">
      {/* Agent Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-white">{agent.name}</span>
          <span className="text-sm text-gray-400 font-mono">({agent.gid})</span>
          <span className={`${complianceColor} text-white text-xs px-2 py-1 rounded-full font-medium`}>
            {agent.uniform_compliant ? 'COMPLIANT' : 'NON-COMPLIANT'}
          </span>
        </div>
      </div>

      {/* Agent Details */}
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <span className="text-xs text-gray-500">Role</span>
          <div className="text-sm text-gray-300">{agent.role}</div>
        </div>
        <div>
          <span className="text-xs text-gray-500">Scope</span>
          <div className="text-sm text-gray-300 font-mono">{agent.scope}</div>
        </div>
      </div>

      {/* Uniform Indicators */}
      <div className="flex items-center gap-2">
        <UniformIndicator label="PAC" present={agent.pac_present} />
        <UniformIndicator label="ACK" present={agent.ack_present} />
        <UniformIndicator label="WRAP" present={agent.wrap_present} />
        <UniformIndicator label="BER" present={agent.ber_eligible} />
      </div>

      {/* Last Execution */}
      {agent.last_execution_at && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <span className="text-xs text-gray-500">
            Last Execution: {new Date(agent.last_execution_at).toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
};

/**
 * Loading skeleton for agent panel.
 */
const LoadingSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-3">
    {[1, 2, 3, 4].map((i) => (
      <div key={i} className="bg-gray-800 rounded-lg p-4">
        <div className="h-6 bg-gray-700 rounded w-48 mb-3"></div>
        <div className="h-4 bg-gray-700 rounded w-32 mb-3"></div>
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((j) => (
            <div key={j} className="h-12 w-12 bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    ))}
  </div>
);

/**
 * Agent Uniform Inspection Panel for ChainTrust.
 * Shows all agents and their uniform compliance status.
 */
export const AgentUniformPanel: React.FC<AgentUniformPanelProps> = ({
  data,
  loading,
  error,
}) => {
  if (error) {
    return (
      <div className="bg-gray-900 border border-red-500 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-400 mb-2">Agent Uniform Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Agent Uniform Inspection</h3>
        {!loading && data && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-green-400">
              {data.compliant_agents} Compliant
            </span>
            <span className="text-sm text-red-400">
              {data.non_compliant_agents} Non-Compliant
            </span>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      {!loading && data && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-400">{data.total_agents}</div>
            <div className="text-xs text-gray-400">Total Agents</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-400">{data.compliant_agents}</div>
            <div className="text-xs text-gray-400">Compliant</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-red-400">{data.non_compliant_agents}</div>
            <div className="text-xs text-gray-400">Non-Compliant</div>
          </div>
        </div>
      )}

      {/* Uniform Invariants */}
      {!loading && data && data.uniform_invariants.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Uniform Invariants</h4>
          <div className="flex flex-wrap gap-2">
            {data.uniform_invariants.map((inv) => (
              <span
                key={inv}
                className="text-xs bg-red-900/30 text-red-400 px-2 py-1 rounded font-mono"
              >
                {inv}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Agent List */}
      {loading ? (
        <LoadingSkeleton />
      ) : data ? (
        <div className="max-h-[500px] overflow-y-auto">
          {data.agents.map((agent) => (
            <AgentUniformRow key={agent.gid} agent={agent} />
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default AgentUniformPanel;
