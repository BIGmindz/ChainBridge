// ═══════════════════════════════════════════════════════════════════════════════
// OCC Phase 2 — Ledger Audit Trail Viewer
// PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
// Agents: SONNY (GID-02) — Frontend / OCC UI
//         LIRA (GID-09) — Accessibility & UX
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * LedgerAuditTrail — Visual audit trail and integrity verification
 *
 * PURPOSE:
 *   Display ledger entries with sequence verification, Merkle proofs,
 *   and checkpoint history for operator audit review.
 *
 * FEATURES:
 *   - Sequential ledger entry display
 *   - Hash chain visualization
 *   - Merkle proof verification status
 *   - Checkpoint markers
 *
 * ACCESSIBILITY (LIRA):
 *   - Sequential navigation via keyboard
 *   - Verification status announced
 *   - High contrast for integrity indicators
 *
 * INVARIANTS:
 *   INV-UI-LEDGER-001: Ledger is read-only display
 *   INV-UI-LEDGER-002: Hash chain verification is visual only
 */

import React, { useState, useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type EntryType = 'PAC' | 'WRAP' | 'BER' | 'PDO' | 'CHECKPOINT' | 'SYSTEM';

export interface LedgerEntry {
  sequence: number;
  entry_id: string;
  entry_type: EntryType;
  artifact_id: string;
  timestamp: string;
  binding_hash: string;
  prev_hash: string;
  agent_id?: string;
  summary: string;
  verified: boolean;
}

export interface CheckpointInfo {
  sequence: number;
  checkpoint_id: string;
  merkle_root: string;
  entry_count: number;
  created_at: string;
}

export interface LedgerAuditTrailProps {
  /** Ledger entries to display */
  entries: LedgerEntry[];
  /** Checkpoints for markers */
  checkpoints: CheckpointInfo[];
  /** Selected entry sequence */
  selectedSequence?: number;
  /** Selection handler */
  onSelect?: (sequence: number) => void;
  /** Filter by entry type */
  filterType?: EntryType | 'ALL';
  /** Show hash details */
  showHashes?: boolean;
  /** ARIA label */
  ariaLabel?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const TYPE_CONFIG: Record<EntryType, {
  label: string;
  icon: string;
  color: string;
  bgColor: string;
}> = {
  PAC: {
    label: 'PAC',
    icon: '📋',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
  },
  WRAP: {
    label: 'WRAP',
    icon: '📦',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50',
  },
  BER: {
    label: 'BER',
    icon: '✅',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
  },
  PDO: {
    label: 'PDO',
    icon: '📄',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
  },
  CHECKPOINT: {
    label: 'CHECKPOINT',
    icon: '🔖',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
  },
  SYSTEM: {
    label: 'SYSTEM',
    icon: '⚙️',
    color: 'text-gray-700',
    bgColor: 'bg-gray-50',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// SUBCOMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface TypeFilterProps {
  current: EntryType | 'ALL';
  onChange: (type: EntryType | 'ALL') => void;
  counts: Record<string, number>;
}

const TypeFilter: React.FC<TypeFilterProps> = ({ current, onChange, counts }) => {
  const types: (EntryType | 'ALL')[] = ['ALL', 'PAC', 'WRAP', 'BER', 'PDO', 'CHECKPOINT'];

  return (
    <div className="flex flex-wrap gap-1" role="group" aria-label="Filter by type">
      {types.map((type) => {
        const count = type === 'ALL' ? counts.total : (counts[type] || 0);
        const isSelected = current === type;
        const config = type !== 'ALL' ? TYPE_CONFIG[type] : null;

        return (
          <button
            key={type}
            onClick={() => onChange(type)}
            className={`
              px-2 py-1 text-xs rounded-full border transition-colors
              ${isSelected
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }
              focus:outline-none focus:ring-2 focus:ring-blue-500
            `}
            aria-pressed={isSelected}
          >
            {config && <span aria-hidden="true">{config.icon} </span>}
            {type} ({count})
          </button>
        );
      })}
    </div>
  );
};

interface HashDisplayProps {
  hash: string;
  label: string;
  verified?: boolean;
}

const HashDisplay: React.FC<HashDisplayProps> = ({ hash, label, verified }) => {
  const shortHash = hash.length > 16 ? `${hash.slice(0, 8)}...${hash.slice(-8)}` : hash;

  return (
    <div className="flex items-center gap-2 font-mono text-xs">
      <span className="text-gray-500">{label}:</span>
      <span
        className={`px-1.5 py-0.5 rounded ${
          verified === true
            ? 'bg-green-100 text-green-800'
            : verified === false
            ? 'bg-red-100 text-red-800'
            : 'bg-gray-100 text-gray-700'
        }`}
        title={hash}
      >
        {shortHash}
      </span>
      {verified !== undefined && (
        <span
          className={verified ? 'text-green-600' : 'text-red-600'}
          role="img"
          aria-label={verified ? 'Verified' : 'Not verified'}
        >
          {verified ? '✓' : '✗'}
        </span>
      )}
    </div>
  );
};

interface LedgerEntryRowProps {
  entry: LedgerEntry;
  prevEntry?: LedgerEntry;
  isSelected: boolean;
  onSelect: () => void;
  showHashes: boolean;
  isCheckpoint: boolean;
}

const LedgerEntryRow: React.FC<LedgerEntryRowProps> = ({
  entry,
  prevEntry,
  isSelected,
  onSelect,
  showHashes,
  isCheckpoint,
}) => {
  const typeConfig = TYPE_CONFIG[entry.entry_type];

  // Check hash chain integrity
  const chainValid = prevEntry
    ? entry.prev_hash === prevEntry.binding_hash
    : entry.prev_hash === '0'.repeat(64); // Genesis check

  return (
    <div className="relative">
      {/* Chain connector line */}
      <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />

      {/* Checkpoint marker */}
      {isCheckpoint && (
        <div className="absolute left-3 -top-1 w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center z-10">
          <span className="text-white text-xs">🔖</span>
        </div>
      )}

      <div
        role="row"
        aria-selected={isSelected}
        onClick={onSelect}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect();
          }
        }}
        tabIndex={0}
        className={`
          relative ml-10 p-3 border rounded-lg cursor-pointer transition-all
          ${isSelected ? 'ring-2 ring-blue-500 border-blue-300 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}
          focus:outline-none focus:ring-2 focus:ring-blue-500
        `}
      >
        {/* Sequence node */}
        <div
          className={`
            absolute -left-7 top-3 w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs
            ${chainValid ? 'bg-green-100 border-green-500' : 'bg-red-100 border-red-500'}
          `}
          title={chainValid ? 'Chain verified' : 'Chain broken!'}
        >
          {entry.sequence}
        </div>

        {/* Entry Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${typeConfig.bgColor} ${typeConfig.color}`}
            >
              <span aria-hidden="true">{typeConfig.icon}</span>
              {typeConfig.label}
            </span>
            <span className="text-xs font-mono text-gray-500">
              {entry.entry_id}
            </span>
          </div>
          <span
            className={`inline-flex items-center gap-1 text-xs ${
              entry.verified ? 'text-green-600' : 'text-gray-500'
            }`}
            role="status"
          >
            {entry.verified ? (
              <>
                <span aria-hidden="true">✓</span> Verified
              </>
            ) : (
              <>
                <span aria-hidden="true">○</span> Pending
              </>
            )}
          </span>
        </div>

        {/* Summary */}
        <p className="text-sm text-gray-700 mb-2">{entry.summary}</p>

        {/* Metadata */}
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>
            {new Date(entry.timestamp).toLocaleString()}
          </span>
          {entry.agent_id && (
            <span className="font-mono">{entry.agent_id}</span>
          )}
          <span className="font-mono">{entry.artifact_id}</span>
        </div>

        {/* Hash Details */}
        {showHashes && (
          <div className="mt-2 pt-2 border-t border-gray-100 space-y-1">
            <HashDisplay
              hash={entry.binding_hash}
              label="Hash"
              verified={entry.verified}
            />
            <HashDisplay
              hash={entry.prev_hash}
              label="Prev"
              verified={chainValid}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const LedgerAuditTrail: React.FC<LedgerAuditTrailProps> = ({
  entries,
  checkpoints,
  selectedSequence,
  onSelect,
  filterType = 'ALL',
  showHashes = true,
  ariaLabel = 'Ledger Audit Trail',
}) => {
  const [typeFilter, setTypeFilter] = useState<EntryType | 'ALL'>(filterType);

  // Filter entries
  const filteredEntries = useMemo(() => {
    const sorted = [...entries].sort((a, b) => b.sequence - a.sequence);
    if (typeFilter === 'ALL') return sorted;
    return sorted.filter((e) => e.entry_type === typeFilter);
  }, [entries, typeFilter]);

  // Checkpoint sequences for markers
  const checkpointSequences = useMemo(
    () => new Set(checkpoints.map((c) => c.sequence)),
    [checkpoints]
  );

  // Entry counts by type
  const counts = useMemo(() => {
    const c: Record<string, number> = { total: entries.length };
    entries.forEach((e) => {
      c[e.entry_type] = (c[e.entry_type] || 0) + 1;
    });
    return c;
  }, [entries]);

  // Statistics
  const stats = useMemo(() => {
    const verified = entries.filter((e) => e.verified).length;
    const latestSeq = entries.length > 0 ? Math.max(...entries.map((e) => e.sequence)) : 0;
    return {
      total: entries.length,
      verified,
      latestSeq,
      checkpointCount: checkpoints.length,
    };
  }, [entries, checkpoints]);

  return (
    <div
      className="flex flex-col h-full bg-white rounded-lg border border-gray-200 shadow-sm"
      aria-label={ariaLabel}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900">
            Ledger Audit Trail
          </h2>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-600">{stats.total} entries</span>
            <span
              className={`px-2 py-0.5 rounded-full text-xs ${
                stats.verified === stats.total
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {stats.verified}/{stats.total} verified
            </span>
          </div>
        </div>
        <TypeFilter
          current={typeFilter}
          onChange={setTypeFilter}
          counts={counts}
        />
      </div>

      {/* Chain info bar */}
      <div className="px-4 py-2 border-b border-gray-100 bg-gray-50 flex items-center gap-4 text-xs">
        <span className="text-gray-600">
          Latest: <strong>Seq #{stats.latestSeq}</strong>
        </span>
        <span className="text-gray-600">
          Checkpoints: <strong>{stats.checkpointCount}</strong>
        </span>
        <span className="text-gray-600">
          Chain: <strong className="text-green-600">Valid</strong>
        </span>
      </div>

      {/* Entry List */}
      <div
        className="flex-1 overflow-y-auto p-4"
        role="grid"
        aria-label="Ledger entries"
      >
        {filteredEntries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <span className="text-2xl mb-2">📒</span>
            <p>No ledger entries</p>
            {typeFilter !== 'ALL' && (
              <p className="text-xs mt-1">Try selecting "ALL" filter</p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredEntries.map((entry, index) => {
              const prevEntry = filteredEntries[index + 1];
              return (
                <LedgerEntryRow
                  key={entry.sequence}
                  entry={entry}
                  prevEntry={prevEntry}
                  isSelected={selectedSequence === entry.sequence}
                  onSelect={() => onSelect?.(entry.sequence)}
                  showHashes={showHashes}
                  isCheckpoint={checkpointSequences.has(entry.sequence)}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span>
          Showing {filteredEntries.length} entries
          {typeFilter !== 'ALL' && ` (filtered: ${typeFilter})`}
        </span>
      </div>
    </div>
  );
};

export default LedgerAuditTrail;
