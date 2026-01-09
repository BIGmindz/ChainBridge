/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Public Audit Timeline
 * PAC-BENSON-P34: Trust Center (Public Audit Interface)
 * 
 * Displays public-safe audit timeline for external verification.
 * 
 * DOCTRINE REFERENCES:
 * - Law 4, §4.3: Decision history with filtering
 * - Law 6: Visual Invariants
 * 
 * CONSTRAINTS:
 * - READ-ONLY display
 * - Public-safe data only (MAGGIE redaction applied)
 * - No private/sensitive information
 * 
 * Author: SONNY (GID-02) — Trust Center UI
 * UX: LIRA (GID-09) — Public UX & Accessibility
 * Redaction: MAGGIE (GID-10) — Explainability redaction
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type { 
  PublicAuditTimeline as PublicAuditTimelineData,
  PublicTimelineEntry 
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// ENTRY TYPE CONFIGURATION (Law 6, §6.1)
// ═══════════════════════════════════════════════════════════════════════════════

const ENTRY_TYPE_CONFIG: Record<PublicTimelineEntry['entryType'], {
  icon: string;
  color: string;
  bgColor: string;
  label: string;
}> = {
  DECISION: {
    icon: '⚖',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    label: 'Decision',
  },
  VERIFICATION: {
    icon: '✓',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'Verification',
  },
  EXPORT: {
    icon: '⬇',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    label: 'Export',
  },
  SYSTEM: {
    icon: '⚙',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/20',
    label: 'System',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE ENTRY COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineEntryProps {
  entry: PublicTimelineEntry;
  isLast: boolean;
  onProofPackClick?: (proofpackId: string) => void;
}

const TimelineEntry: React.FC<TimelineEntryProps> = ({ 
  entry, 
  isLast,
  onProofPackClick,
}) => {
  const config = ENTRY_TYPE_CONFIG[entry.entryType];

  return (
    <div className="flex gap-3">
      {/* Timeline Line */}
      <div className="flex flex-col items-center">
        {/* Icon */}
        <div 
          className={`
            w-8 h-8 rounded-full flex items-center justify-center
            ${config.bgColor} ${config.color}
          `}
          aria-hidden="true"
        >
          {config.icon}
        </div>
        {/* Connecting Line */}
        {!isLast && (
          <div className="w-0.5 flex-1 bg-gray-700 my-1" aria-hidden="true" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 pb-4 ${isLast ? '' : 'border-b border-gray-700 mb-4'}`}>
        <div className="flex items-start justify-between">
          <div>
            <span className={`text-xs px-2 py-0.5 rounded ${config.bgColor} ${config.color}`}>
              {config.label}
            </span>
            <p className="text-sm text-gray-200 mt-1">{entry.description}</p>
          </div>
          <time 
            className="text-xs text-gray-500 whitespace-nowrap ml-2"
            dateTime={entry.timestamp}
          >
            {new Date(entry.timestamp).toLocaleString()}
          </time>
        </div>

        {/* ProofPack Link */}
        {entry.proofpackId && (
          <button
            onClick={() => onProofPackClick?.(entry.proofpackId!)}
            className="mt-2 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
          >
            <span>📄</span>
            <span>View ProofPack</span>
          </button>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// FILTER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineFiltersProps {
  selectedType: PublicTimelineEntry['entryType'] | 'ALL';
  onTypeChange: (type: PublicTimelineEntry['entryType'] | 'ALL') => void;
}

const TimelineFilters: React.FC<TimelineFiltersProps> = ({
  selectedType,
  onTypeChange,
}) => {
  const types: Array<PublicTimelineEntry['entryType'] | 'ALL'> = [
    'ALL',
    'DECISION',
    'VERIFICATION',
    'EXPORT',
    'SYSTEM',
  ];

  return (
    <div className="flex gap-2 flex-wrap" role="group" aria-label="Filter timeline entries">
      {types.map((type) => (
        <button
          key={type}
          onClick={() => onTypeChange(type)}
          className={`
            px-3 py-1 text-xs rounded-full transition-colors
            ${selectedType === type
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }
          `}
          aria-pressed={selectedType === type}
        >
          {type === 'ALL' ? 'All' : ENTRY_TYPE_CONFIG[type].label}
        </button>
      ))}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface PublicAuditTimelineProps {
  /** Timeline data */
  timeline: PublicAuditTimelineData | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback to load more entries */
  onLoadMore: () => void;
  /** Callback to refresh timeline */
  onRefresh: () => void;
  /** Callback when ProofPack is clicked */
  onProofPackClick?: (proofpackId: string) => void;
}

export const PublicAuditTimeline: React.FC<PublicAuditTimelineProps> = ({
  timeline,
  isLoading,
  error,
  onLoadMore,
  onRefresh,
  onProofPackClick,
}) => {
  const [filterType, setFilterType] = useState<PublicTimelineEntry['entryType'] | 'ALL'>('ALL');

  // Filter entries
  const filteredEntries = timeline?.entries.filter(
    (entry) => filterType === 'ALL' || entry.entryType === filterType
  ) || [];

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && !timeline) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-6"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <span className="animate-spin">⟳</span>
          <span>Loading audit timeline...</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Error State
  // ═══════════════════════════════════════════════════════════════════════════
  if (error && !timeline) {
    return (
      <div 
        className="bg-red-900/20 border border-red-700 rounded-lg p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <span>✗</span>
            <span>Timeline unavailable: {error}</span>
          </div>
          <button
            onClick={onRefresh}
            className="px-3 py-1 bg-red-700 hover:bg-red-600 text-white text-sm rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="timeline-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 id="timeline-title" className="text-lg font-semibold text-gray-100">
              📜 Public Audit Timeline
            </h2>
            <p className="text-xs text-gray-400">
              {timeline?.totalCount || 0} total entries
            </p>
          </div>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded"
            aria-label="Refresh timeline"
          >
            {isLoading ? '⟳' : '↻'}
          </button>
        </div>

        {/* Filters */}
        <TimelineFilters
          selectedType={filterType}
          onTypeChange={setFilterType}
        />
      </header>

      {/* Timeline Entries */}
      <div className="p-4 max-h-[600px] overflow-y-auto">
        {filteredEntries.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-3xl mb-2">📭</div>
            <p>No entries match the selected filter</p>
          </div>
        ) : (
          <div role="list" aria-label="Audit timeline entries">
            {filteredEntries.map((entry, index) => (
              <TimelineEntry
                key={entry.entryId}
                entry={entry}
                isLast={index === filteredEntries.length - 1}
                onProofPackClick={onProofPackClick}
              />
            ))}
          </div>
        )}

        {/* Load More */}
        {timeline?.hasMore && (
          <div className="mt-4 text-center">
            <button
              onClick={onLoadMore}
              disabled={isLoading}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded"
            >
              {isLoading ? '⟳ Loading...' : 'Load More'}
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-gray-850 px-4 py-2 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          This timeline contains public-safe information only. Sensitive data is redacted.
        </p>
      </footer>
    </section>
  );
};

export default PublicAuditTimeline;
