/**
 * Training Signal Panel Component
 * PAC-JEFFREY-P02R Section 11 — Training Signals
 *
 * REQUIRED FROM ALL AGENTS.
 * Append-only. Immutable.
 *
 * Schema: TRAINING_SIGNAL_SCHEMA@v1.0.0
 *
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React from 'react';
import { TrainingSignalDTO, TrainingSignalsResponseDTO } from '../../types/controlPlane';

interface TrainingSignalPanelProps {
  data: TrainingSignalsResponseDTO | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * Signal type badge configuration.
 */
const SIGNAL_TYPE_CONFIG: Record<string, { label: string; color: string; bgColor: string; icon: string }> = {
  CORRECTION: {
    label: 'Correction',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '🔧',
  },
  LEARNING: {
    label: 'Learning',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    icon: '📚',
  },
  CONSTRAINT: {
    label: 'Constraint',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/50',
    icon: '🔒',
  },
};

/**
 * Individual training signal card.
 */
const SignalCard: React.FC<{ signal: TrainingSignalDTO }> = ({ signal }) => {
  const config = SIGNAL_TYPE_CONFIG[signal.signal_type] || SIGNAL_TYPE_CONFIG.LEARNING;
  
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-mono ${config.bgColor} ${config.color}`}>
            {config.icon} {config.label}
          </span>
          <span className="text-gray-400 text-xs">{signal.agent_gid}</span>
        </div>
        <span className="text-gray-500 text-xs font-mono">
          {new Date(signal.emitted_at).toLocaleString()}
        </span>
      </div>
      
      {/* Agent */}
      <div className="text-sm text-gray-300 mb-2">
        <span className="text-gray-500">Agent:</span>{' '}
        <span className="font-medium">{signal.agent_name}</span>
      </div>
      
      {/* Observation */}
      <div className="mb-2">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Observation</div>
        <div className="text-sm text-gray-200 bg-gray-900/50 rounded p-2">
          {signal.observation}
        </div>
      </div>
      
      {/* Constraint Learned */}
      <div className="mb-2">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Constraint Learned</div>
        <div className="text-sm text-yellow-300 bg-yellow-900/20 rounded p-2 font-mono">
          {signal.constraint_learned}
        </div>
      </div>
      
      {/* Recommended Enforcement */}
      <div className="mb-2">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Recommended Enforcement</div>
        <div className="text-sm text-green-300 bg-green-900/20 rounded p-2">
          {signal.recommended_enforcement}
        </div>
      </div>
      
      {/* Hash */}
      <div className="text-xs text-gray-600 font-mono truncate">
        Hash: {signal.signal_hash.slice(0, 16)}...
      </div>
    </div>
  );
};

/**
 * Training Signal Panel — Displays all training signals for a PAC.
 */
export const TrainingSignalPanel: React.FC<TrainingSignalPanelProps> = ({
  data,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-24 bg-gray-800 rounded mb-3"></div>
          <div className="h-24 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-red-700 rounded-lg p-6">
        <div className="text-red-400">
          <span className="text-xl mr-2">⚠️</span>
          Error loading training signals: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📡</span>
          <h3 className="text-lg font-semibold text-white">Training Signals</h3>
          {data && data.total_signals > 0 && (
            <span className="px-2 py-0.5 bg-blue-900/50 text-blue-400 rounded text-sm">
              {data.total_signals} signal{data.total_signals !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500 font-mono">
          PAC-JEFFREY-P02R §11
        </span>
      </div>

      {/* Schema Info */}
      {data && (
        <div className="text-xs text-gray-500 mb-4 font-mono">
          Schema: {data.schema_version}
        </div>
      )}

      {/* Empty State */}
      {(!data || data.total_signals === 0) && (
        <div className="text-center py-8 text-gray-500">
          <span className="text-4xl mb-3 block">📭</span>
          <p>No training signals emitted yet.</p>
          <p className="text-xs mt-2 text-yellow-500">
            ⚠️ MANDATORY: All agents must emit Training Signals
          </p>
        </div>
      )}

      {/* Signal List */}
      {data && data.signals.length > 0 && (
        <div className="space-y-3">
          {data.signals.map((signal) => (
            <SignalCard key={signal.signal_id} signal={signal} />
          ))}
        </div>
      )}

      {/* Digest */}
      {data && data.digest && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Aggregate Digest
          </div>
          <div className="text-xs text-gray-400 font-mono bg-gray-800 rounded p-2 truncate">
            {data.digest}
          </div>
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

export default TrainingSignalPanel;
