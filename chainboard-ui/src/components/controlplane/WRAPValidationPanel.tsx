/**
 * WRAP Validation Panel — Control Plane UI
 * PAC-CP-UI-EXEC-001: ORDER 4 — WRAP Ingestion & Validation View
 *
 * Displays WRAP artifact validation status and artifact references.
 *
 * INVARIANTS:
 * - INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
 * - WRAP with missing ACKs must be rejected
 * - All validation errors are visible
 *
 * Author: Benson Execution Orchestrator (GID-00)
 */

import React, { useMemo } from 'react';
import {
  ControlPlaneStateDTO,
  WRAPArtifactDTO,
  WRAPValidationState,
  WRAP_STATE_CONFIG,
  formatTimestamp,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// WRAP STATE BADGE
// ═══════════════════════════════════════════════════════════════════════════════

interface WRAPStateBadgeProps {
  state: WRAPValidationState;
}

export const WRAPStateBadge: React.FC<WRAPStateBadgeProps> = ({ state }) => {
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
// ARTIFACT REFERENCE LIST
// ═══════════════════════════════════════════════════════════════════════════════

interface ArtifactRefListProps {
  refs: string[];
}

export const ArtifactRefList: React.FC<ArtifactRefListProps> = ({ refs }) => {
  if (refs.length === 0) {
    return (
      <span className="text-gray-500 text-xs italic">No artifacts referenced</span>
    );
  }

  return (
    <div className="space-y-1">
      {refs.map((ref, idx) => (
        <div
          key={idx}
          className="flex items-center gap-2 text-xs bg-gray-800 rounded px-2 py-1"
        >
          <span className="text-gray-500">📎</span>
          <span className="font-mono text-gray-300 truncate">{ref}</span>
        </div>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// VALIDATION ERROR LIST
// ═══════════════════════════════════════════════════════════════════════════════

interface ValidationErrorListProps {
  errors: string[];
}

export const ValidationErrorList: React.FC<ValidationErrorListProps> = ({ errors }) => {
  if (errors.length === 0) {
    return null;
  }

  return (
    <div className="bg-red-900/20 border border-red-800 rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-2 text-red-400 text-sm font-medium">
        <span>❌</span>
        <span>Validation Errors ({errors.length})</span>
      </div>
      <ul className="space-y-1">
        {errors.map((error, idx) => (
          <li key={idx} className="text-xs text-red-300 flex items-start gap-2">
            <span className="text-red-500">•</span>
            <span>{error}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SINGLE WRAP CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface WRAPCardProps {
  wrap: WRAPArtifactDTO;
}

export const WRAPCard: React.FC<WRAPCardProps> = ({ wrap }) => {
  const config = WRAP_STATE_CONFIG[wrap.validation_state];
  const isValid = wrap.validation_state === 'VALID';
  const isInvalid = ['INVALID', 'SCHEMA_ERROR', 'MISSING_ACK'].includes(wrap.validation_state);

  return (
    <div
      className={`rounded-lg border p-4 ${
        isValid
          ? 'border-green-800 bg-green-900/10'
          : isInvalid
            ? 'border-red-800 bg-red-900/10'
            : 'border-gray-700 bg-gray-800/50'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">📦</span>
          <span className="font-mono text-sm text-gray-200 truncate max-w-[200px]">
            {wrap.wrap_id}
          </span>
        </div>
        <WRAPStateBadge state={wrap.validation_state} />
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-3 text-xs mb-3">
        <div>
          <span className="text-gray-500">Agent</span>
          <p className="font-mono text-gray-300">{wrap.agent_gid}</p>
        </div>
        <div>
          <span className="text-gray-500">PAC ID</span>
          <p className="font-mono text-gray-300 truncate">{wrap.pac_id}</p>
        </div>
        <div>
          <span className="text-gray-500">Submitted</span>
          <p className="text-gray-300">{formatTimestamp(wrap.submitted_at)}</p>
        </div>
        <div>
          <span className="text-gray-500">Validated</span>
          <p className="text-gray-300">{formatTimestamp(wrap.validated_at)}</p>
        </div>
      </div>

      {/* Artifacts */}
      <div className="mb-3">
        <span className="text-xs text-gray-500 block mb-1">
          Artifact References ({wrap.artifact_refs.length})
        </span>
        <div className="max-h-24 overflow-y-auto">
          <ArtifactRefList refs={wrap.artifact_refs} />
        </div>
      </div>

      {/* Validation Errors */}
      {wrap.validation_errors.length > 0 && (
        <ValidationErrorList errors={wrap.validation_errors} />
      )}

      {/* Missing ACK Warning */}
      {wrap.validation_state === 'MISSING_ACK' && (
        <div className="mt-3 p-2 bg-red-900/30 rounded text-xs text-red-400 flex items-center gap-2">
          <span>🛑</span>
          <span>
            <strong>FAIL_CLOSED:</strong> WRAP rejected due to missing ACK.
            BER generation blocked (INV-CP-005).
          </span>
        </div>
      )}

      {/* Hash for audit */}
      <div className="mt-3 pt-2 border-t border-gray-700">
        <span className="text-[10px] text-gray-600 font-mono break-all">
          Hash: {wrap.wrap_hash.slice(0, 16)}...
        </span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// WRAP VALIDATION PANEL (MAIN COMPONENT)
// ═══════════════════════════════════════════════════════════════════════════════

interface WRAPValidationPanelProps {
  state: ControlPlaneStateDTO | null;
  loading?: boolean;
  error?: string | null;
}

export const WRAPValidationPanel: React.FC<WRAPValidationPanelProps> = ({
  state,
  loading = false,
  error = null,
}) => {
  // Memoized WRAP list
  const wrapList = useMemo(() => {
    if (!state) return [];
    return Object.values(state.wraps).sort((a, b) => 
      new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime()
    );
  }, [state]);

  // Summary stats
  const stats = useMemo(() => {
    const total = wrapList.length;
    const valid = wrapList.filter(w => w.validation_state === 'VALID').length;
    const invalid = wrapList.filter(w => 
      ['INVALID', 'SCHEMA_ERROR', 'MISSING_ACK'].includes(w.validation_state)
    ).length;
    const pending = wrapList.filter(w => 
      ['PENDING', 'SUBMITTED'].includes(w.validation_state)
    ).length;
    
    return { total, valid, invalid, pending };
  }, [wrapList]);

  // Check if BER-eligible
  const isBERReady = stats.total > 0 && stats.valid > 0 && stats.invalid === 0 && stats.pending === 0;

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-800 rounded w-1/3" />
          <div className="h-32 bg-gray-800 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-lg border border-red-800 p-4">
        <div className="flex items-center gap-2 text-red-400">
          <span>🛑</span>
          <span className="font-medium">WRAP Panel Error</span>
        </div>
        <p className="mt-2 text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <div className="text-gray-500 text-center py-8">
          <span className="text-2xl">📦</span>
          <p className="mt-2">No WRAP data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-200">
            📦 WRAP Validation
          </h3>
          <div className="flex items-center gap-2">
            {isBERReady ? (
              <span className="text-xs text-green-400 flex items-center gap-1">
                <span>✅</span> BER Ready
              </span>
            ) : stats.invalid > 0 ? (
              <span className="text-xs text-red-400 flex items-center gap-1">
                <span>🛑</span> BER Blocked
              </span>
            ) : (
              <span className="text-xs text-yellow-400 flex items-center gap-1">
                <span>⏳</span> Pending
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-gray-500" />
            <span className="text-gray-400">Total:</span>
            <span className="font-medium text-gray-200">{stats.total}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-gray-400">Valid:</span>
            <span className="font-medium text-green-400">{stats.valid}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-yellow-500" />
            <span className="text-gray-400">Pending:</span>
            <span className="font-medium text-yellow-400">{stats.pending}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-gray-400">Invalid:</span>
            <span className="font-medium text-red-400">{stats.invalid}</span>
          </div>
        </div>
      </div>

      {/* WRAP Cards */}
      <div className="p-4">
        {wrapList.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            <span className="text-3xl">📭</span>
            <p className="mt-2">No WRAP artifacts submitted yet.</p>
            <p className="text-xs mt-1">
              WRAP submission will be available after execution completes.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {wrapList.map((wrap) => (
              <WRAPCard key={wrap.wrap_id} wrap={wrap} />
            ))}
          </div>
        )}
      </div>

      {/* Governance Footer */}
      <div className="px-4 py-2 border-t border-gray-800 bg-gray-800/30">
        <p className="text-[10px] text-gray-600">
          INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
        </p>
      </div>
    </div>
  );
};

export default WRAPValidationPanel;
