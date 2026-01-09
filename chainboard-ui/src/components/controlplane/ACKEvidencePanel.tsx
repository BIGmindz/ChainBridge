/**
 * ACK Evidence Panel Component
 * PAC-JEFFREY-P02R Section 1 — Full ACK Evidence
 *
 * ACK REQUIREMENTS (HARD):
 * - agent_id
 * - gid
 * - lane
 * - concrete ISO-8601 timestamp
 * - ack_latency_ms
 * - authorization_scope
 * - evidence_hash
 *
 * Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
 *
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React from 'react';
import { AgentACKEvidenceDTO, ACKEvidenceResponseDTO } from '../../types/controlPlane';

interface ACKEvidencePanelProps {
  data: ACKEvidenceResponseDTO | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * Lane badge configuration.
 */
const LANE_CONFIG: Record<string, { color: string; bgColor: string; icon: string }> = {
  orchestration: {
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/50',
    icon: '🎯',
  },
  backend: {
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    icon: '⚙️',
  },
  frontend: {
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '🎨',
  },
  ci_cd: {
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '🔧',
  },
  security: {
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '🛡️',
  },
};

/**
 * Mode badge.
 */
const ModeBadge: React.FC<{ mode: string }> = ({ mode }) => {
  const isExecuting = mode === 'EXECUTING';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono ${
      isExecuting
        ? 'bg-green-900/50 text-green-400'
        : 'bg-gray-700 text-gray-400'
    }`}>
      {isExecuting ? '▶ EXECUTING' : '⏸ NON-EXEC'}
    </span>
  );
};

/**
 * Latency indicator.
 */
const LatencyIndicator: React.FC<{ ms: number }> = ({ ms }) => {
  const getColor = () => {
    if (ms < 100) return 'text-green-400';
    if (ms < 500) return 'text-yellow-400';
    if (ms < 2000) return 'text-orange-400';
    return 'text-red-400';
  };
  
  return (
    <span className={`font-mono ${getColor()}`}>
      {ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`}
    </span>
  );
};

/**
 * Individual ACK evidence card.
 */
const EvidenceCard: React.FC<{ evidence: AgentACKEvidenceDTO }> = ({ evidence }) => {
  const laneConfig = LANE_CONFIG[evidence.lane] || LANE_CONFIG.backend;
  
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-mono ${laneConfig.bgColor} ${laneConfig.color}`}>
            {laneConfig.icon} {evidence.lane.toUpperCase()}
          </span>
          <span className="text-gray-300 font-medium">{evidence.agent_id}</span>
          <span className="text-gray-500 text-xs">({evidence.gid})</span>
        </div>
        <ModeBadge mode={evidence.mode} />
      </div>
      
      {/* Evidence Details */}
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            ISO-8601 Timestamp
          </div>
          <div className="text-sm text-cyan-300 font-mono bg-gray-900/50 rounded p-2">
            {evidence.timestamp}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            ACK Latency
          </div>
          <div className="text-sm bg-gray-900/50 rounded p-2">
            <LatencyIndicator ms={evidence.ack_latency_ms} />
          </div>
        </div>
      </div>
      
      {/* Authorization Scope */}
      <div className="mb-3">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          Authorization Scope
        </div>
        <div className="text-sm text-gray-300 bg-gray-900/50 rounded p-2 font-mono">
          {evidence.authorization_scope}
        </div>
      </div>
      
      {/* Evidence Hash */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">Evidence Hash:</span>
        <span className="text-gray-400 font-mono truncate max-w-[300px]">
          {evidence.evidence_hash}
        </span>
      </div>
    </div>
  );
};

/**
 * ACK Evidence Panel — Displays full ACK evidence for all agents.
 */
export const ACKEvidencePanel: React.FC<ACKEvidencePanelProps> = ({
  data,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-32 bg-gray-800 rounded mb-3"></div>
          <div className="h-32 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-red-700 rounded-lg p-6">
        <div className="text-red-400">
          <span className="text-xl mr-2">⚠️</span>
          Error loading ACK evidence: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📋</span>
          <h3 className="text-lg font-semibold text-white">ACK Evidence (Full)</h3>
          {data && data.total_evidence > 0 && (
            <span className="px-2 py-0.5 bg-cyan-900/50 text-cyan-400 rounded text-sm">
              {data.total_evidence} agent{data.total_evidence !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500 font-mono">
          PAC-JEFFREY-P02R §1
        </span>
      </div>

      {/* Schema Info */}
      {data && (
        <div className="text-xs text-gray-500 mb-4 font-mono">
          Schema: {data.schema_version}
        </div>
      )}

      {/* Requirement Notice */}
      <div className="bg-blue-900/20 border border-blue-700 rounded p-3 mb-4 text-sm">
        <div className="text-blue-300 font-medium mb-1">PAG-01 ACK Requirements (HARD)</div>
        <ul className="text-blue-200/70 text-xs list-disc list-inside space-y-1">
          <li>agent_id, gid, lane — Agent identification</li>
          <li>concrete ISO-8601 timestamp — Deterministic timing</li>
          <li>ack_latency_ms — Settlement eligibility binding</li>
          <li>authorization_scope — Execution boundaries</li>
          <li>evidence_hash — Integrity verification</li>
        </ul>
      </div>

      {/* Empty State */}
      {(!data || data.total_evidence === 0) && (
        <div className="text-center py-8 text-gray-500">
          <span className="text-4xl mb-3 block">📭</span>
          <p>No ACK evidence recorded yet.</p>
        </div>
      )}

      {/* Evidence List */}
      {data && data.evidence.length > 0 && (
        <div className="space-y-3">
          {data.evidence.map((evidence, index) => (
            <EvidenceCard key={`${evidence.gid}-${index}`} evidence={evidence} />
          ))}
        </div>
      )}

      {/* Governance Invariant */}
      {data && (
        <div className="mt-4 text-xs text-gray-600">
          {data.governance_invariant}
        </div>
      )}
    </div>
  );
};

export default ACKEvidencePanel;
