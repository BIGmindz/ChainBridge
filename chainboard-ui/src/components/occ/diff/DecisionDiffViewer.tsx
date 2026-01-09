/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Decision Diff Viewer — Structured Proof Comparison
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Displays side-by-side or unified diffs of:
 * - PDO comparisons
 * - BER comparisons
 * - Evidence artifact comparisons
 * - Configuration changes
 * 
 * INVARIANTS:
 * - INV-OCC-005: Evidence immutability (hashes shown)
 * - INV-OCC-006: No hidden transitions (all changes visible)
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useMemo, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type DiffViewMode = 'side-by-side' | 'unified' | 'inline';

export type ChangeType = 'added' | 'removed' | 'modified' | 'unchanged';

export interface DiffLine {
  lineNumber: number;
  content: string;
  changeType: ChangeType;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export interface DiffSection {
  sectionId: string;
  title: string;
  leftValue: unknown;
  rightValue: unknown;
  changeType: ChangeType;
  path: string;
}

export interface DiffContext {
  leftLabel: string;
  rightLabel: string;
  leftTimestamp: string;
  rightTimestamp: string;
  leftHash?: string;
  rightHash?: string;
}

export interface DecisionDiff {
  diffId: string;
  entityType: 'pdo' | 'ber' | 'artifact' | 'config' | 'pac';
  entityId: string;
  context: DiffContext;
  sections: DiffSection[];
  summary: {
    totalChanges: number;
    additions: number;
    removals: number;
    modifications: number;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatValue(value: unknown): string {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function truncateHash(hash: string, len = 8): string {
  if (!hash || hash.length <= len * 2) return hash;
  return `${hash.slice(0, len)}...${hash.slice(-len)}`;
}

function getChangeColor(type: ChangeType): { text: string; bg: string; border: string } {
  switch (type) {
    case 'added':
      return { text: 'text-green-400', bg: 'bg-green-900/30', border: 'border-green-600' };
    case 'removed':
      return { text: 'text-red-400', bg: 'bg-red-900/30', border: 'border-red-600' };
    case 'modified':
      return { text: 'text-yellow-400', bg: 'bg-yellow-900/30', border: 'border-yellow-600' };
    default:
      return { text: 'text-gray-400', bg: 'bg-gray-800', border: 'border-gray-700' };
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// DIFF SECTION COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DiffSectionDisplayProps {
  section: DiffSection;
  viewMode: DiffViewMode;
  showPath?: boolean;
}

const DiffSectionDisplay: React.FC<DiffSectionDisplayProps> = ({
  section,
  viewMode,
  showPath = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const colors = getChangeColor(section.changeType);

  const leftFormatted = formatValue(section.leftValue);
  const rightFormatted = formatValue(section.rightValue);

  const changeIcon = {
    added: '+',
    removed: '-',
    modified: '~',
    unchanged: ' ',
  }[section.changeType];

  return (
    <div className={`rounded-lg border ${colors.border} overflow-hidden`}>
      {/* Section header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full px-3 py-2 flex items-center justify-between ${colors.bg} hover:opacity-90 transition-opacity`}
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-2">
          <span className={`font-mono font-bold ${colors.text}`}>{changeIcon}</span>
          <span className="font-medium text-gray-200">{section.title}</span>
          {showPath && (
            <span className="text-xs text-gray-500 font-mono">{section.path}</span>
          )}
        </div>
        <span className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
      </button>

      {/* Section content */}
      {isExpanded && (
        <div className="p-3">
          {viewMode === 'side-by-side' ? (
            <div className="grid grid-cols-2 gap-4">
              {/* Left (old) value */}
              <div>
                <div className="text-xs text-gray-500 mb-1">Previous</div>
                <pre className={`
                  text-sm font-mono p-2 rounded overflow-x-auto
                  ${section.changeType === 'removed' || section.changeType === 'modified'
                    ? 'bg-red-900/20 text-red-300'
                    : 'bg-gray-800 text-gray-400'
                  }
                `}>
                  {leftFormatted}
                </pre>
              </div>

              {/* Right (new) value */}
              <div>
                <div className="text-xs text-gray-500 mb-1">Current</div>
                <pre className={`
                  text-sm font-mono p-2 rounded overflow-x-auto
                  ${section.changeType === 'added' || section.changeType === 'modified'
                    ? 'bg-green-900/20 text-green-300'
                    : 'bg-gray-800 text-gray-400'
                  }
                `}>
                  {rightFormatted}
                </pre>
              </div>
            </div>
          ) : (
            /* Unified view */
            <div className="space-y-2">
              {section.changeType !== 'added' && (
                <pre className="text-sm font-mono p-2 rounded bg-red-900/20 text-red-300 overflow-x-auto">
                  <span className="text-red-500">- </span>{leftFormatted}
                </pre>
              )}
              {section.changeType !== 'removed' && (
                <pre className="text-sm font-mono p-2 rounded bg-green-900/20 text-green-300 overflow-x-auto">
                  <span className="text-green-500">+ </span>{rightFormatted}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// DIFF HEADER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DiffHeaderProps {
  context: DiffContext;
  entityType: string;
  entityId: string;
}

const DiffHeader: React.FC<DiffHeaderProps> = ({ context, entityType, entityId }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold text-gray-100">
            {entityType.toUpperCase()} Comparison
          </h3>
          <span className="text-sm font-mono text-blue-400">{entityId}</span>
        </div>
      </div>

      {/* Comparison labels */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="bg-red-900/20 rounded p-2">
          <div className="text-red-400 font-medium">{context.leftLabel}</div>
          <div className="text-xs text-gray-500">
            {new Date(context.leftTimestamp).toLocaleString()}
          </div>
          {context.leftHash && (
            <div className="text-xs font-mono text-teal-400 mt-1">
              {truncateHash(context.leftHash)}
            </div>
          )}
        </div>

        <div className="bg-green-900/20 rounded p-2">
          <div className="text-green-400 font-medium">{context.rightLabel}</div>
          <div className="text-xs text-gray-500">
            {new Date(context.rightTimestamp).toLocaleString()}
          </div>
          {context.rightHash && (
            <div className="text-xs font-mono text-teal-400 mt-1">
              {truncateHash(context.rightHash)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// DIFF SUMMARY COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DiffSummaryProps {
  summary: DecisionDiff['summary'];
}

const DiffSummary: React.FC<DiffSummaryProps> = ({ summary }) => {
  return (
    <div className="flex items-center gap-4 text-sm mb-4">
      <span className="text-gray-400">
        {summary.totalChanges} changes:
      </span>
      {summary.additions > 0 && (
        <span className="text-green-400">+{summary.additions} added</span>
      )}
      {summary.removals > 0 && (
        <span className="text-red-400">-{summary.removals} removed</span>
      )}
      {summary.modifications > 0 && (
        <span className="text-yellow-400">~{summary.modifications} modified</span>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN DECISION DIFF VIEWER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface DecisionDiffViewerProps {
  diff: DecisionDiff | null;
  loading?: boolean;
  error?: string | null;
  onClose?: () => void;
}

export const DecisionDiffViewer: React.FC<DecisionDiffViewerProps> = ({
  diff,
  loading = false,
  error = null,
  onClose,
}) => {
  const [viewMode, setViewMode] = useState<DiffViewMode>('side-by-side');
  const [filterType, setFilterType] = useState<ChangeType | 'all'>('all');

  // Filter sections
  const filteredSections = useMemo(() => {
    if (!diff) return [];
    if (filterType === 'all') return diff.sections;
    return diff.sections.filter(s => s.changeType === filterType);
  }, [diff, filterType]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose?.();
    }
  }, [onClose]);

  // Error state
  if (error) {
    return (
      <div className="bg-gray-800 border border-red-700 rounded-lg p-4" role="alert">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span>🛑</span>
          <span className="font-medium">Diff Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  // Loading state
  if (loading && !diff) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
          <p className="mt-2 text-sm text-gray-400">Loading diff...</p>
        </div>
      </div>
    );
  }

  if (!diff) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center">
        <p className="text-gray-400">Select two items to compare</p>
      </div>
    );
  }

  return (
    <div
      className="bg-gray-900 rounded-lg flex flex-col h-full"
      role="dialog"
      aria-label="Decision diff viewer"
      onKeyDown={handleKeyDown}
    >
      {/* Header with controls */}
      <header className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <span>📊</span>
            Decision Diff Viewer
          </h2>
          <div className="flex items-center gap-2">
            {/* View mode toggle */}
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value as DiffViewMode)}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="View mode"
            >
              <option value="side-by-side">Side by Side</option>
              <option value="unified">Unified</option>
            </select>

            {/* Filter toggle */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as ChangeType | 'all')}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="Filter changes"
            >
              <option value="all">All changes</option>
              <option value="added">Added only</option>
              <option value="removed">Removed only</option>
              <option value="modified">Modified only</option>
            </select>

            {onClose && (
              <button
                onClick={onClose}
                className="p-2 text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
                aria-label="Close diff viewer"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Diff header */}
        <DiffHeader
          context={diff.context}
          entityType={diff.entityType}
          entityId={diff.entityId}
        />

        {/* Summary */}
        <DiffSummary summary={diff.summary} />
      </header>

      {/* Diff sections */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredSections.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {filterType === 'all'
              ? 'No differences found'
              : `No ${filterType} changes`
            }
          </div>
        ) : (
          filteredSections.map((section) => (
            <DiffSectionDisplay
              key={section.sectionId}
              section={section}
              viewMode={viewMode}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <footer className="p-3 border-t border-gray-700 text-xs text-gray-500">
        <div className="flex items-center justify-between">
          <span>
            Showing {filteredSections.length} of {diff.sections.length} sections
          </span>
          <span>
            INV-OCC-005: Evidence hashes visible for immutability verification
          </span>
        </div>
      </footer>
    </div>
  );
};

export default DecisionDiffViewer;
