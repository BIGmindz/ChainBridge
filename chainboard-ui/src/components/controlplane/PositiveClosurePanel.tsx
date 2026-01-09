/**
 * Positive Closure Panel Component
 * PAC-JEFFREY-P02R Section 12 — Positive Closure
 *
 * REQUIRED FROM ALL AGENTS.
 * No Positive Closure → PAC INCOMPLETE.
 *
 * Schema: POSITIVE_CLOSURE_SCHEMA@v1.0.0
 *
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React from 'react';
import { PositiveClosureDTO, PositiveClosuresResponseDTO } from '../../types/controlPlane';

interface PositiveClosurePanelProps {
  data: PositiveClosuresResponseDTO | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * Closure status badge.
 */
const ClosureStatusBadge: React.FC<{ isValid: boolean }> = ({ isValid }) => {
  if (isValid) {
    return (
      <span className="px-2 py-1 bg-green-900/50 text-green-400 rounded text-xs font-mono">
        ✅ VALID
      </span>
    );
  }
  return (
    <span className="px-2 py-1 bg-red-900/50 text-red-400 rounded text-xs font-mono">
      ❌ INVALID
    </span>
  );
};

/**
 * Condition check indicator.
 */
const ConditionCheck: React.FC<{ label: string; passed: boolean }> = ({ label, passed }) => (
  <div className="flex items-center gap-2 text-sm">
    <span className={passed ? 'text-green-400' : 'text-red-400'}>
      {passed ? '✓' : '✗'}
    </span>
    <span className={passed ? 'text-gray-300' : 'text-gray-500'}>{label}</span>
  </div>
);

/**
 * Individual closure card.
 */
const ClosureCard: React.FC<{ closure: PositiveClosureDTO }> = ({ closure }) => {
  return (
    <div className={`bg-gray-800 border rounded-lg p-4 mb-3 ${
      closure.is_valid ? 'border-green-700' : 'border-red-700'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-xs font-mono">{closure.agent_gid}</span>
          <span className="text-gray-300 font-medium">{closure.agent_name}</span>
        </div>
        <ClosureStatusBadge isValid={closure.is_valid} />
      </div>
      
      {/* Conditions */}
      <div className="grid grid-cols-3 gap-4 mb-3">
        <ConditionCheck label="Scope Complete" passed={closure.scope_complete} />
        <ConditionCheck label="No Violations" passed={closure.no_violations} />
        <ConditionCheck label="Ready for Next Stage" passed={closure.ready_for_next_stage} />
      </div>
      
      {/* Timestamp */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">
          Emitted: {new Date(closure.emitted_at).toLocaleString()}
        </span>
        <span className="text-gray-600 font-mono truncate max-w-[200px]">
          {closure.closure_hash.slice(0, 16)}...
        </span>
      </div>
    </div>
  );
};

/**
 * Positive Closure Panel — Displays all positive closures for a PAC.
 */
export const PositiveClosurePanel: React.FC<PositiveClosurePanelProps> = ({
  data,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="h-20 bg-gray-800 rounded mb-3"></div>
          <div className="h-20 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-red-700 rounded-lg p-6">
        <div className="text-red-400">
          <span className="text-xl mr-2">⚠️</span>
          Error loading positive closures: {error}
        </div>
      </div>
    );
  }

  const allValid = data?.all_valid ?? false;

  return (
    <div className={`bg-gray-900 border rounded-lg p-6 ${
      data && data.total_closures > 0
        ? allValid ? 'border-green-700' : 'border-yellow-700'
        : 'border-gray-700'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✅</span>
          <h3 className="text-lg font-semibold text-white">Positive Closures</h3>
          {data && data.total_closures > 0 && (
            <span className={`px-2 py-0.5 rounded text-sm ${
              allValid
                ? 'bg-green-900/50 text-green-400'
                : 'bg-yellow-900/50 text-yellow-400'
            }`}>
              {data.total_closures} closure{data.total_closures !== 1 ? 's' : ''}
              {allValid && ' — All Valid'}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500 font-mono">
          PAC-JEFFREY-P02R §12
        </span>
      </div>

      {/* Schema Info */}
      {data && (
        <div className="text-xs text-gray-500 mb-4 font-mono">
          Schema: {data.schema_version}
        </div>
      )}

      {/* Empty State */}
      {(!data || data.total_closures === 0) && (
        <div className="text-center py-8 text-gray-500">
          <span className="text-4xl mb-3 block">📭</span>
          <p>No positive closures emitted yet.</p>
          <p className="text-xs mt-2 text-red-500 font-bold">
            ⚠️ PAC INCOMPLETE: No Positive Closure → PAC cannot complete
          </p>
        </div>
      )}

      {/* Closure List */}
      {data && data.closures.length > 0 && (
        <div className="space-y-3">
          {data.closures.map((closure) => (
            <ClosureCard key={closure.closure_id} closure={closure} />
          ))}
        </div>
      )}

      {/* Summary */}
      {data && data.total_closures > 0 && (
        <div className={`mt-4 p-3 rounded ${
          allValid ? 'bg-green-900/30' : 'bg-yellow-900/30'
        }`}>
          <div className="flex items-center gap-2">
            <span className={allValid ? 'text-green-400' : 'text-yellow-400'}>
              {allValid ? '✅' : '⚠️'}
            </span>
            <span className={allValid ? 'text-green-300' : 'text-yellow-300'}>
              {allValid
                ? 'All agents have valid positive closures'
                : 'Some closures are invalid or missing'
              }
            </span>
          </div>
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

export default PositiveClosurePanel;
