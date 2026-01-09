/**
 * ExecutionBarrierPanel — PAC-JEFFREY-P03 Section 2
 * 
 * Displays execution barrier status with ACK collection progress.
 * 
 * INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs
 * 
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React from 'react';
import type { ExecutionBarrierDTO, AgentACKEvidenceDTO } from '../../types/controlPlane';
import { formatTimestamp, formatLatency } from '../../types/controlPlane';

interface ExecutionBarrierPanelProps {
  barrier: ExecutionBarrierDTO | null;
  loading?: boolean;
  error?: string | null;
}

const LANE_COLORS: Record<string, string> = {
  orchestration: 'text-purple-400 bg-purple-900/50',
  backend: 'text-blue-400 bg-blue-900/50',
  frontend: 'text-green-400 bg-green-900/50',
  ci_cd: 'text-orange-400 bg-orange-900/50',
  security: 'text-red-400 bg-red-900/50',
};

const MODE_BADGES: Record<string, { label: string; className: string }> = {
  EXECUTING: { label: 'EXEC', className: 'bg-green-600 text-white' },
  NON_EXECUTING: { label: 'NON-EXEC', className: 'bg-gray-600 text-white' },
};

export const ExecutionBarrierPanel: React.FC<ExecutionBarrierPanelProps> = ({
  barrier,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <div className="animate-spin h-5 w-5 border-2 border-cyan-500 border-t-transparent rounded-full" />
          <h3 className="text-lg font-semibold text-gray-200">Loading Execution Barrier...</h3>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 rounded-lg p-4 border border-red-700">
        <h3 className="text-lg font-semibold text-red-400 mb-2">Barrier Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  if (!barrier) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-400">No Execution Barrier</h3>
        <p className="text-gray-500 text-sm mt-2">No barrier configured for this PAC.</p>
      </div>
    );
  }

  const receivedCount = Object.keys(barrier.received_acks).length;
  const totalRequired = barrier.required_agents.length;
  const progressPercent = totalRequired > 0 ? (receivedCount / totalRequired) * 100 : 0;

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{barrier.released ? '🔓' : '🔒'}</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-200">
              Execution Barrier
            </h3>
            <p className="text-xs text-gray-500 font-mono">{barrier.barrier_id}</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          barrier.released 
            ? 'bg-green-600 text-white' 
            : 'bg-yellow-600 text-white'
        }`}>
          {barrier.released ? 'RELEASED' : 'BLOCKED'}
        </div>
      </div>

      {/* Barrier Configuration */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-gray-900/50 rounded p-2">
          <p className="text-xs text-gray-500 uppercase">Mode</p>
          <p className="text-sm font-medium text-cyan-400">{barrier.execution_mode}</p>
        </div>
        <div className="bg-gray-900/50 rounded p-2">
          <p className="text-xs text-gray-500 uppercase">Type</p>
          <p className="text-sm font-medium text-purple-400">{barrier.barrier_type}</p>
        </div>
        <div className="bg-gray-900/50 rounded p-2">
          <p className="text-xs text-gray-500 uppercase">Release Condition</p>
          <p className="text-xs font-medium text-orange-400">{barrier.release_condition}</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-400">ACK Progress</span>
          <span className="text-gray-300">{receivedCount} / {totalRequired}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              progressPercent === 100 ? 'bg-green-500' : 'bg-cyan-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Received ACKs */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Received ACKs</h4>
        {Object.entries(barrier.received_acks).length > 0 ? (
          <div className="space-y-2">
            {Object.entries(barrier.received_acks).map(([gid, ack]) => (
              <ACKRow key={gid} gid={gid} ack={ack} />
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm italic">No ACKs received yet</p>
        )}
      </div>

      {/* Missing ACKs */}
      {barrier.missing_acks.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-yellow-400 mb-2">⏳ Awaiting ACKs</h4>
          <div className="flex flex-wrap gap-2">
            {barrier.missing_acks.map((gid) => (
              <span 
                key={gid}
                className="px-2 py-1 bg-yellow-900/30 text-yellow-400 text-xs rounded-full border border-yellow-700"
              >
                {gid}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Release Info */}
      {barrier.released && barrier.released_at && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-green-400">✓</span>
            <span className="text-sm text-gray-400">
              Released at: <span className="text-gray-200">{formatTimestamp(barrier.released_at)}</span>
            </span>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-gray-700 flex justify-between text-xs text-gray-500">
        <span>Created: {formatTimestamp(barrier.created_at)}</span>
        <span className="font-mono">{barrier.barrier_hash.slice(0, 16)}...</span>
      </div>
    </div>
  );
};

interface ACKRowProps {
  gid: string;
  ack: AgentACKEvidenceDTO;
}

const ACKRow: React.FC<ACKRowProps> = ({ gid, ack }) => {
  const laneClass = LANE_COLORS[ack.lane] || 'text-gray-400 bg-gray-700';
  const modeBadge = MODE_BADGES[ack.mode] || MODE_BADGES.EXECUTING;

  return (
    <div className="flex items-center justify-between bg-gray-900/50 rounded p-2">
      <div className="flex items-center gap-2">
        <span className="text-green-400">✓</span>
        <span className="font-medium text-gray-200">{ack.agent_id}</span>
        <span className="text-xs text-gray-500">({gid})</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`px-2 py-0.5 rounded text-xs ${laneClass}`}>
          {ack.lane}
        </span>
        <span className={`px-2 py-0.5 rounded text-xs ${modeBadge.className}`}>
          {modeBadge.label}
        </span>
        <span className="text-xs text-gray-400">
          {formatLatency(ack.ack_latency_ms)}
        </span>
      </div>
    </div>
  );
};

export default ExecutionBarrierPanel;
