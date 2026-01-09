/**
 * Multi-Agent WRAP Aggregation Panel — Control Plane UI
 * PAC-JEFFREY-P01: SECTION 7 — Multi-Agent WRAP Collection
 *
 * Displays multi-agent WRAP aggregation status per PAC-JEFFREY-P01:
 * - Expected agents for WRAP submission
 * - Collected WRAPs with validation status
 * - Missing agents indicator
 * - Set completion status
 *
 * INVARIANTS:
 * - INV-CP-006: Multi-agent WRAPs required before BER
 * - Each executing agent MUST return a WRAP
 * - WRAP Authority: BENSON
 * - WRAP Validation: HARD FAIL on omission
 *
 * Author: Benson Execution Orchestrator (GID-00)
 * Frontend Lane: SONNY (GID-02)
 */

import React from 'react';
import {
  MultiAgentWRAPSetDTO,
  WRAPValidationState,
  WRAP_STATE_CONFIG,
  formatTimestamp,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT REGISTRY (display names)
// ═══════════════════════════════════════════════════════════════════════════════

const AGENT_NAMES: Record<string, string> = {
  'GID-00': 'BENSON',
  'GID-01': 'CODY',
  'GID-02': 'SONNY',
  'GID-06': 'SAM',
  'GID-07': 'DAN',
};

// ═══════════════════════════════════════════════════════════════════════════════
// WRAP STATUS BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface WRAPStatusBadgeProps {
  state: WRAPValidationState;
}

const WRAPStatusBadge: React.FC<WRAPStatusBadgeProps> = ({ state }) => {
  const config = WRAP_STATE_CONFIG[state];
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color}`}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT WRAP CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentWRAPCardProps {
  gid: string;
  wrap?: {
    wrap_id: string;
    submitted_at: string;
    validation_state: WRAPValidationState;
    validated_at: string | null;
    artifact_refs: string[];
    wrap_hash: string;
  };
  isMissing: boolean;
}

const AgentWRAPCard: React.FC<AgentWRAPCardProps> = ({ gid, wrap, isMissing }) => {
  const agentName = AGENT_NAMES[gid] || gid;

  if (isMissing) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
              <span className="text-gray-400">⏳</span>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-300">{agentName}</div>
              <div className="text-xs text-gray-500">{gid}</div>
            </div>
          </div>
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-900/50 text-yellow-400">
            ⏳ Awaiting WRAP
          </span>
        </div>
        <div className="text-xs text-gray-500 italic">
          WRAP not yet submitted
        </div>
      </div>
    );
  }

  if (!wrap) return null;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-green-900/50 flex items-center justify-center">
            <span className="text-green-400">✅</span>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-300">{agentName}</div>
            <div className="text-xs text-gray-500">{gid}</div>
          </div>
        </div>
        <WRAPStatusBadge state={wrap.validation_state} />
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-gray-500">WRAP ID:</span>
          <span className="font-mono text-gray-300">{wrap.wrap_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500">Submitted:</span>
          <span className="text-gray-300">{formatTimestamp(wrap.submitted_at)}</span>
        </div>
        {wrap.validated_at && (
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Validated:</span>
            <span className="text-gray-300">{formatTimestamp(wrap.validated_at)}</span>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span className="text-gray-500">Artifacts:</span>
          <span className="text-gray-300">{wrap.artifact_refs.length} refs</span>
        </div>
        <div className="mt-2 pt-2 border-t border-gray-700">
          <span className="text-gray-500">Hash: </span>
          <span className="font-mono text-gray-400 text-[10px]">
            {wrap.wrap_hash.slice(0, 16)}...
          </span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLETION PROGRESS BAR
// ═══════════════════════════════════════════════════════════════════════════════

interface CompletionProgressProps {
  total: number;
  collected: number;
  allValid: boolean;
}

const CompletionProgress: React.FC<CompletionProgressProps> = ({
  total,
  collected,
  allValid,
}) => {
  const percentage = total > 0 ? (collected / total) * 100 : 0;
  const isComplete = collected === total;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">WRAP Collection Progress</span>
        <span className={isComplete ? 'text-green-400' : 'text-yellow-400'}>
          {collected}/{total} ({Math.round(percentage)}%)
        </span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isComplete
              ? allValid
                ? 'bg-green-500'
                : 'bg-orange-500'
              : 'bg-yellow-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {isComplete && (
        <div className="flex items-center gap-2 text-xs">
          {allValid ? (
            <>
              <span className="text-green-400">✅</span>
              <span className="text-green-400">All WRAPs collected and valid</span>
            </>
          ) : (
            <>
              <span className="text-orange-400">⚠️</span>
              <span className="text-orange-400">All WRAPs collected but some invalid</span>
            </>
          )}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface MultiAgentWRAPPanelProps {
  data: MultiAgentWRAPSetDTO;
  className?: string;
}

export const MultiAgentWRAPPanel: React.FC<MultiAgentWRAPPanelProps> = ({
  data,
  className = '',
}) => {
  // Build a map of collected WRAPs by agent GID
  const wrapsByAgent = React.useMemo(() => {
    const map: Record<string, typeof data.collected_wraps[0]> = {};
    data.collected_wraps.forEach((wrap) => {
      map[wrap.agent_gid] = wrap;
    });
    return map;
  }, [data.collected_wraps]);

  return (
    <div className={`bg-gray-900 rounded-lg p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span>📦</span>
            <span>Multi-Agent WRAP Collection</span>
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            PAC-JEFFREY-P01 Section 7 · {data.schema_version}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {data.is_complete ? (
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-900/50 text-green-400">
              ✅ Complete
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-900/50 text-yellow-400">
              ⏳ In Progress
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <CompletionProgress
        total={data.expected_agents.length}
        collected={data.collected_wraps.length}
        allValid={data.all_valid}
      />

      {/* Governance Invariant Banner */}
      <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-3">
        <div className="flex items-center gap-2 text-blue-400 text-xs">
          <span>📋</span>
          <span className="font-medium">{data.governance_invariant}</span>
        </div>
      </div>

      {/* Agent WRAP Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.expected_agents.map((gid) => (
          <AgentWRAPCard
            key={gid}
            gid={gid}
            wrap={wrapsByAgent[gid]}
            isMissing={!wrapsByAgent[gid]}
          />
        ))}
      </div>

      {/* Missing Agents Warning */}
      {data.missing_agents.length > 0 && (
        <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-yellow-400 text-sm font-medium mb-2">
            <span>⚠️</span>
            <span>Missing WRAPs ({data.missing_agents.length})</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.missing_agents.map((gid) => (
              <span
                key={gid}
                className="px-2 py-1 bg-yellow-900/30 rounded text-xs text-yellow-400"
              >
                {AGENT_NAMES[gid] || gid} ({gid})
              </span>
            ))}
          </div>
          <p className="text-xs text-yellow-500/70 mt-2 italic">
            WRAP Validation: HARD FAIL on omission (PAC-JEFFREY-P01 Section 7)
          </p>
        </div>
      )}

      {/* Set Hash */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-800 text-xs">
        <span className="text-gray-500">Set Hash:</span>
        <span className="font-mono text-gray-400">{data.set_hash.slice(0, 24)}...</span>
      </div>
    </div>
  );
};

export default MultiAgentWRAPPanel;
