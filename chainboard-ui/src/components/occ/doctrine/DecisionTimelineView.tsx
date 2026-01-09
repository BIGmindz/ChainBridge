/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Decision Timeline View (MANDATORY)
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * DOCTRINE LAW 4, §4.3 — Decision Timeline (MANDATORY)
 * DOCTRINE LAW 1: Flight Recorder Mandate
 * 
 * Displays:
 * - Chronological decision history
 * - State-at-time-T replay capability
 * - Before/after diff view
 * - Filter by: entity, decision type, outcome
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-DOC-005: Deterministic replay possible
 * - INV-DOC-006: Every decision traceable to proof
 * 
 * Author: SONNY (GID-02) — UI Implementation Lead
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback, useMemo } from 'react';
import type { 
  DecisionTimelineEntry, 
  DecisionType, 
  DecisionDiff 
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// DECISION TYPE CONFIG (Visual Invariants - Law 6)
// ═══════════════════════════════════════════════════════════════════════════════

const DECISION_TYPE_CONFIG: Record<DecisionType, { icon: string; color: string; label: string }> = {
  SETTLEMENT: { icon: '💰', color: 'text-green-400', label: 'Settlement' },
  RISK_ASSESSMENT: { icon: '⚖️', color: 'text-yellow-400', label: 'Risk Assessment' },
  APPROVAL: { icon: '✓', color: 'text-green-400', label: 'Approval' },
  REJECTION: { icon: '✗', color: 'text-red-400', label: 'Rejection' },
  OVERRIDE: { icon: '⚡', color: 'text-orange-400', label: 'Override' },
  ESCALATION: { icon: '⬆️', color: 'text-purple-400', label: 'Escalation' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// FILTER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineFiltersProps {
  selectedTypes: DecisionType[];
  onTypesChange: (types: DecisionType[]) => void;
  entityFilter: string;
  onEntityFilterChange: (value: string) => void;
  dateRange: { start: string | null; end: string | null };
  onDateRangeChange: (range: { start: string | null; end: string | null }) => void;
}

const TimelineFilters: React.FC<TimelineFiltersProps> = ({
  selectedTypes,
  onTypesChange,
  entityFilter,
  onEntityFilterChange,
  dateRange,
  onDateRangeChange,
}) => {
  const allTypes: DecisionType[] = ['SETTLEMENT', 'RISK_ASSESSMENT', 'APPROVAL', 'REJECTION', 'OVERRIDE', 'ESCALATION'];

  const handleTypeToggle = useCallback((type: DecisionType) => {
    if (selectedTypes.includes(type)) {
      onTypesChange(selectedTypes.filter(t => t !== type));
    } else {
      onTypesChange([...selectedTypes, type]);
    }
  }, [selectedTypes, onTypesChange]);

  return (
    <div className="flex flex-wrap gap-4 p-4 bg-gray-800 border-b border-gray-700">
      {/* Decision Type Filter */}
      <div className="flex flex-col gap-2">
        <label className="text-xs text-gray-500">Decision Type</label>
        <div className="flex flex-wrap gap-1">
          {allTypes.map((type) => {
            const config = DECISION_TYPE_CONFIG[type];
            const isSelected = selectedTypes.length === 0 || selectedTypes.includes(type);
            return (
              <button
                key={type}
                onClick={() => handleTypeToggle(type)}
                className={`
                  px-2 py-1 text-xs rounded transition-colors
                  ${isSelected 
                    ? `${config.color} bg-gray-700` 
                    : 'text-gray-500 bg-gray-800 hover:bg-gray-700'}
                `}
                aria-pressed={isSelected}
              >
                {config.icon} {config.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Entity Filter */}
      <div className="flex flex-col gap-2">
        <label htmlFor="entity-filter" className="text-xs text-gray-500">Entity ID</label>
        <input
          id="entity-filter"
          type="text"
          value={entityFilter}
          onChange={(e) => onEntityFilterChange(e.target.value)}
          placeholder="Filter by entity..."
          className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Date Range (simplified) */}
      <div className="flex flex-col gap-2">
        <label className="text-xs text-gray-500">Date Range</label>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateRange.start ?? ''}
            onChange={(e) => onDateRangeChange({ ...dateRange, start: e.target.value || null })}
            className="px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-gray-500">to</span>
          <input
            type="date"
            value={dateRange.end ?? ''}
            onChange={(e) => onDateRangeChange({ ...dateRange, end: e.target.value || null })}
            className="px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE ENTRY COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineEntryCardProps {
  entry: DecisionTimelineEntry;
  onSelect: (entry: DecisionTimelineEntry) => void;
  onViewDiff: (entry: DecisionTimelineEntry) => void;
  onReplayTo: (entry: DecisionTimelineEntry) => void;
  isSelected: boolean;
}

const TimelineEntryCard: React.FC<TimelineEntryCardProps> = ({
  entry,
  onSelect,
  onViewDiff,
  onReplayTo,
  isSelected,
}) => {
  const config = DECISION_TYPE_CONFIG[entry.type];
  
  return (
    <div
      className={`
        relative flex gap-4 p-4 border-l-4 
        ${isSelected ? 'bg-blue-900/20 border-l-blue-500' : 'bg-gray-800 border-l-gray-600 hover:bg-gray-750'}
        transition-colors cursor-pointer
      `}
      onClick={() => onSelect(entry)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(entry);
        }
      }}
      aria-selected={isSelected}
    >
      {/* Timeline Dot */}
      <div className="absolute left-[-8px] top-6 w-4 h-4 rounded-full bg-gray-700 border-2 border-gray-600" />

      {/* Content */}
      <div className="flex-1 ml-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={config.color} aria-hidden="true">{config.icon}</span>
            <span className={`font-medium ${config.color}`}>{config.label}</span>
            <span className="text-xs text-gray-500 font-mono">{entry.decisionId}</span>
          </div>
          <span className="text-xs text-gray-500">
            {new Date(entry.timestamp).toLocaleString()}
          </span>
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-2 text-sm mb-3">
          <div>
            <span className="text-gray-500">Agent:</span>
            <span className="ml-2 text-gray-300">{entry.agentName}</span>
            <span className="ml-1 text-gray-500 text-xs">({entry.agentGid})</span>
          </div>
          <div>
            <span className="text-gray-500">Outcome:</span>
            <span className={`ml-2 ${
              entry.outcome === 'APPROVED' ? 'text-green-400' :
              entry.outcome === 'REJECTED' ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {entry.outcome}
            </span>
          </div>
          {entry.entityId && (
            <div>
              <span className="text-gray-500">Entity:</span>
              <span className="ml-2 text-gray-300 font-mono text-xs">{entry.entityId}</span>
            </div>
          )}
          {entry.modelVersion && (
            <div>
              <span className="text-gray-500">Model:</span>
              <span className="ml-2 text-gray-300 font-mono text-xs">{entry.modelVersion}</span>
            </div>
          )}
        </div>

        {/* Human Override Indicator */}
        {entry.humanOverride && (
          <div className="mb-3 px-2 py-1 bg-orange-900/30 border border-orange-700 rounded text-xs text-orange-400 inline-block">
            ⚡ Human Override Applied
          </div>
        )}

        {/* Proof Reference */}
        {entry.proofPackRef && (
          <div className="text-xs text-gray-500">
            ProofPack: <code className="text-gray-400">{entry.proofPackRef}</code>
          </div>
        )}

        {/* Actions */}
        <div className="mt-3 flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onViewDiff(entry);
            }}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
          >
            📊 View Diff
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onReplayTo(entry);
            }}
            className="px-2 py-1 text-xs bg-purple-700 hover:bg-purple-600 text-white rounded transition-colors"
          >
            ⏪ Replay to This Point
          </button>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// DIFF VIEW MODAL
// ═══════════════════════════════════════════════════════════════════════════════

interface DiffViewProps {
  entry: DecisionTimelineEntry | null;
  diff: DecisionDiff | null;
  isLoading: boolean;
  onClose: () => void;
}

const DiffView: React.FC<DiffViewProps> = ({ entry, diff, isLoading, onClose }) => {
  if (!entry) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="diff-title"
    >
      <div className="bg-gray-900 border border-gray-700 rounded-lg w-[800px] max-h-[80vh] overflow-hidden">
        {/* Header */}
        <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
          <h3 id="diff-title" className="text-lg font-semibold text-gray-100">
            State Diff: {entry.decisionId}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close diff view"
          >
            ✕
          </button>
        </header>

        {/* Content */}
        <div className="p-4 overflow-auto max-h-[60vh]">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-400">
              <span className="animate-spin mr-2">⟳</span> Loading diff...
            </div>
          ) : diff ? (
            <div className="grid grid-cols-2 gap-4">
              {/* Before */}
              <div>
                <h4 className="text-sm font-medium text-red-400 mb-2">Before</h4>
                <pre className="p-3 bg-red-900/20 rounded text-xs text-gray-300 font-mono overflow-auto">
                  {JSON.stringify(diff.before, null, 2)}
                </pre>
              </div>
              {/* After */}
              <div>
                <h4 className="text-sm font-medium text-green-400 mb-2">After</h4>
                <pre className="p-3 bg-green-900/20 rounded text-xs text-gray-300 font-mono overflow-auto">
                  {JSON.stringify(diff.after, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500 py-8">
              No diff data available
            </div>
          )}

          {/* Changed Fields */}
          {diff && diff.changedFields.length > 0 && (
            <div className="mt-4 p-3 bg-gray-800 rounded">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Changed Fields</h4>
              <div className="flex flex-wrap gap-2">
                {diff.changedFields.map((field) => (
                  <span key={field} className="px-2 py-1 bg-yellow-900/30 text-yellow-400 text-xs rounded">
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DecisionTimelineViewProps {
  /** Timeline entries from backend */
  entries: DecisionTimelineEntry[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to load diff for entry */
  onLoadDiff: (entry: DecisionTimelineEntry) => Promise<DecisionDiff | null>;
  /** Callback to replay to a specific point */
  onReplayTo: (entry: DecisionTimelineEntry) => void;
  /** Callback to refresh */
  onRefresh: () => void;
  /** Current diff data */
  currentDiff: DecisionDiff | null;
  /** Diff loading state */
  isDiffLoading: boolean;
}

export const DecisionTimelineView: React.FC<DecisionTimelineViewProps> = ({
  entries,
  isLoading,
  error,
  onLoadDiff,
  onReplayTo,
  onRefresh,
  currentDiff,
  isDiffLoading,
}) => {
  const [selectedEntry, setSelectedEntry] = useState<DecisionTimelineEntry | null>(null);
  const [diffEntry, setDiffEntry] = useState<DecisionTimelineEntry | null>(null);
  const [typeFilters, setTypeFilters] = useState<DecisionType[]>([]);
  const [entityFilter, setEntityFilter] = useState('');
  const [dateRange, setDateRange] = useState<{ start: string | null; end: string | null }>({ start: null, end: null });

  // Filter entries
  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      // Type filter
      if (typeFilters.length > 0 && !typeFilters.includes(entry.type)) {
        return false;
      }
      // Entity filter
      if (entityFilter && entry.entityId && !entry.entityId.includes(entityFilter)) {
        return false;
      }
      // Date range filter
      if (dateRange.start && new Date(entry.timestamp) < new Date(dateRange.start)) {
        return false;
      }
      if (dateRange.end && new Date(entry.timestamp) > new Date(dateRange.end + 'T23:59:59')) {
        return false;
      }
      return true;
    });
  }, [entries, typeFilters, entityFilter, dateRange]);

  const handleViewDiff = useCallback(async (entry: DecisionTimelineEntry) => {
    setDiffEntry(entry);
    await onLoadDiff(entry);
  }, [onLoadDiff]);

  const handleCloseDiff = useCallback(() => {
    setDiffEntry(null);
  }, []);

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="timeline-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 id="timeline-title" className="text-lg font-semibold text-gray-100">
            Decision Timeline
          </h2>
          <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
            {filteredEntries.length} / {entries.length} decisions
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className={`
            px-3 py-1.5 text-sm font-medium rounded transition-colors
            ${isLoading
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
            }
          `}
        >
          {isLoading ? '⟳ Loading...' : '⟳ Refresh'}
        </button>
      </header>

      {/* Filters */}
      <TimelineFilters
        selectedTypes={typeFilters}
        onTypesChange={setTypeFilters}
        entityFilter={entityFilter}
        onEntityFilterChange={setEntityFilter}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
      />

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-900/20 border-b border-red-700 text-red-400">
          ✗ {error}
        </div>
      )}

      {/* Timeline */}
      <div className="max-h-[600px] overflow-y-auto">
        {filteredEntries.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {entries.length === 0 
              ? 'No decisions recorded yet.'
              : 'No decisions match the current filters.'}
          </div>
        ) : (
          <div className="relative ml-4 border-l-2 border-gray-700">
            {filteredEntries.map((entry) => (
              <TimelineEntryCard
                key={entry.decisionId}
                entry={entry}
                onSelect={setSelectedEntry}
                onViewDiff={handleViewDiff}
                onReplayTo={onReplayTo}
                isSelected={selectedEntry?.decisionId === entry.decisionId}
              />
            ))}
          </div>
        )}
      </div>

      {/* Diff Modal */}
      <DiffView
        entry={diffEntry}
        diff={currentDiff}
        isLoading={isDiffLoading}
        onClose={handleCloseDiff}
      />
    </section>
  );
};

export default DecisionTimelineView;
