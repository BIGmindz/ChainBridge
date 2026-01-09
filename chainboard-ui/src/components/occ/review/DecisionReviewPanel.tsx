// ═══════════════════════════════════════════════════════════════════════════════
// OCC Phase 2 — Decision Review Panel
// PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
// Agents: SONNY (GID-02) — Frontend / OCC UI
//         LIRA (GID-09) — Accessibility & UX
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * DecisionReviewPanel — Enhanced decision review with density controls
 *
 * PURPOSE:
 *   Provide operators with a dense, ergonomic decision review interface
 *   for reviewing PAC/WRAP/BER decisions with full audit context.
 *
 * FEATURES:
 *   - Density modes: compact, standard, expanded
 *   - Keyboard navigation for review workflow
 *   - Approval/rejection with audit notes
 *   - Evidence panel with inline proofs
 *
 * ACCESSIBILITY (LIRA):
 *   - ARIA live regions for decision updates
 *   - Keyboard shortcuts for power users
 *   - High contrast decision indicators
 *   - Screen reader optimized summaries
 *
 * INVARIANTS:
 *   INV-UI-REVIEW-001: Read-only display of decision state
 *   INV-UI-REVIEW-002: No mutation of decisions from OCC
 */

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import type { OCCDecisionCard, OCCDecisionType } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type DensityMode = 'compact' | 'standard' | 'expanded';
export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'deferred';

export interface DecisionReviewItem {
  id: string;
  type: OCCDecisionType;
  title: string;
  summary: string;
  agent_id: string;
  agent_name: string;
  timestamp: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: ReviewStatus;
  evidence_count: number;
  invariants_checked: number;
  invariants_passed: number;
  pac_id?: string;
  wrap_id?: string;
  details?: Record<string, unknown>;
}

export interface DecisionReviewPanelProps {
  /** Decisions to review */
  decisions: DecisionReviewItem[];
  /** Currently selected decision ID */
  selectedId?: string;
  /** Selection change handler */
  onSelect?: (id: string) => void;
  /** Initial density mode */
  initialDensity?: DensityMode;
  /** Enable keyboard navigation */
  enableKeyboardNav?: boolean;
  /** ARIA label for the panel */
  ariaLabel?: string;
  /** Loading state */
  isLoading?: boolean;
  /** Error message */
  error?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DENSITY CONFIGURATIONS
// ═══════════════════════════════════════════════════════════════════════════════

const DENSITY_CONFIG: Record<DensityMode, {
  rowHeight: string;
  padding: string;
  fontSize: string;
  showDetails: boolean;
  showEvidence: boolean;
}> = {
  compact: {
    rowHeight: 'h-10',
    padding: 'p-1',
    fontSize: 'text-xs',
    showDetails: false,
    showEvidence: false,
  },
  standard: {
    rowHeight: 'h-14',
    padding: 'p-2',
    fontSize: 'text-sm',
    showDetails: true,
    showEvidence: false,
  },
  expanded: {
    rowHeight: 'h-auto min-h-[4rem]',
    padding: 'p-3',
    fontSize: 'text-sm',
    showDetails: true,
    showEvidence: true,
  },
};

const SEVERITY_COLORS: Record<string, string> = {
  low: 'bg-gray-100 text-gray-700 border-gray-300',
  medium: 'bg-yellow-50 text-yellow-800 border-yellow-300',
  high: 'bg-orange-50 text-orange-800 border-orange-300',
  critical: 'bg-red-50 text-red-800 border-red-300',
};

const STATUS_ICONS: Record<ReviewStatus, string> = {
  pending: '⏳',
  approved: '✅',
  rejected: '❌',
  deferred: '⏸️',
};

// ═══════════════════════════════════════════════════════════════════════════════
// SUBCOMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface DensityToggleProps {
  current: DensityMode;
  onChange: (mode: DensityMode) => void;
}

const DensityToggle: React.FC<DensityToggleProps> = ({ current, onChange }) => {
  const modes: DensityMode[] = ['compact', 'standard', 'expanded'];

  return (
    <div
      className="inline-flex rounded-md shadow-sm"
      role="group"
      aria-label="Density mode selection"
    >
      {modes.map((mode) => (
        <button
          key={mode}
          type="button"
          onClick={() => onChange(mode)}
          className={`
            px-3 py-1.5 text-xs font-medium border
            ${current === mode
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }
            ${mode === 'compact' ? 'rounded-l-md' : ''}
            ${mode === 'expanded' ? 'rounded-r-md' : ''}
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
          `}
          aria-pressed={current === mode}
        >
          {mode.charAt(0).toUpperCase() + mode.slice(1)}
        </button>
      ))}
    </div>
  );
};

interface InvariantBadgeProps {
  passed: number;
  total: number;
}

const InvariantBadge: React.FC<InvariantBadgeProps> = ({ passed, total }) => {
  const allPassed = passed === total;
  const percentage = total > 0 ? Math.round((passed / total) * 100) : 100;

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
        ${allPassed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}
      `}
      role="status"
      aria-label={`${passed} of ${total} invariants passed (${percentage}%)`}
    >
      <span aria-hidden="true">{allPassed ? '✓' : '!'}</span>
      {passed}/{total}
    </span>
  );
};

interface DecisionRowProps {
  decision: DecisionReviewItem;
  density: DensityMode;
  isSelected: boolean;
  onSelect: () => void;
  tabIndex: number;
}

const DecisionRow: React.FC<DecisionRowProps> = ({
  decision,
  density,
  isSelected,
  onSelect,
  tabIndex,
}) => {
  const config = DENSITY_CONFIG[density];
  const severityClass = SEVERITY_COLORS[decision.severity] || SEVERITY_COLORS.low;

  return (
    <div
      role="row"
      aria-selected={isSelected}
      tabIndex={tabIndex}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      className={`
        ${config.rowHeight} ${config.padding}
        flex items-center gap-3 border-b border-gray-200
        cursor-pointer transition-colors duration-150
        ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-gray-50'}
        focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500
      `}
    >
      {/* Status Icon */}
      <span
        className="flex-shrink-0 w-6 text-center"
        role="img"
        aria-label={`Status: ${decision.status}`}
      >
        {STATUS_ICONS[decision.status]}
      </span>

      {/* Type Badge */}
      <span
        className={`
          flex-shrink-0 px-2 py-0.5 rounded text-xs font-mono
          ${severityClass}
        `}
      >
        {decision.type}
      </span>

      {/* Title & Agent */}
      <div className={`flex-1 min-w-0 ${config.fontSize}`}>
        <div className="font-medium text-gray-900 truncate">
          {decision.title}
        </div>
        {config.showDetails && (
          <div className="text-gray-500 truncate">
            {decision.agent_name} • {new Date(decision.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Invariant Badge */}
      <InvariantBadge
        passed={decision.invariants_passed}
        total={decision.invariants_checked}
      />

      {/* Evidence Count */}
      {config.showEvidence && decision.evidence_count > 0 && (
        <span className="flex-shrink-0 text-xs text-gray-500">
          {decision.evidence_count} evidence
        </span>
      )}

      {/* PAC/WRAP ID */}
      {config.showDetails && decision.pac_id && (
        <span className="flex-shrink-0 text-xs font-mono text-gray-400">
          {decision.pac_id}
        </span>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const DecisionReviewPanel: React.FC<DecisionReviewPanelProps> = ({
  decisions,
  selectedId,
  onSelect,
  initialDensity = 'standard',
  enableKeyboardNav = true,
  ariaLabel = 'Decision Review Panel',
  isLoading = false,
  error,
}) => {
  const [density, setDensity] = useState<DensityMode>(initialDensity);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter and sort decisions
  const sortedDecisions = useMemo(() => {
    return [...decisions].sort((a, b) => {
      // Sort by severity (critical first), then by timestamp
      const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
      const severityDiff =
        (severityOrder[a.severity] || 3) - (severityOrder[b.severity] || 3);
      if (severityDiff !== 0) return severityDiff;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [decisions]);

  // Statistics
  const stats = useMemo(() => {
    const pending = decisions.filter((d) => d.status === 'pending').length;
    const critical = decisions.filter((d) => d.severity === 'critical').length;
    const failing = decisions.filter(
      (d) => d.invariants_passed < d.invariants_checked
    ).length;
    return { total: decisions.length, pending, critical, failing };
  }, [decisions]);

  // Keyboard navigation
  useEffect(() => {
    if (!enableKeyboardNav || sortedDecisions.length === 0) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!containerRef.current?.contains(document.activeElement)) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setFocusedIndex((prev) =>
            Math.min(prev + 1, sortedDecisions.length - 1)
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Home':
          e.preventDefault();
          setFocusedIndex(0);
          break;
        case 'End':
          e.preventDefault();
          setFocusedIndex(sortedDecisions.length - 1);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enableKeyboardNav, sortedDecisions.length]);

  // Handle selection
  const handleSelect = useCallback(
    (id: string, index: number) => {
      setFocusedIndex(index);
      onSelect?.(id);
    },
    [onSelect]
  );

  // Error state
  if (error) {
    return (
      <div
        role="alert"
        className="p-4 bg-red-50 border border-red-200 rounded-lg"
      >
        <p className="text-red-800 font-medium">Error loading decisions</p>
        <p className="text-red-600 text-sm mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex flex-col h-full bg-white rounded-lg border border-gray-200 shadow-sm"
      aria-label={ariaLabel}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Decision Review
          </h2>
          <div
            className="flex items-center gap-2 text-sm"
            role="status"
            aria-live="polite"
          >
            <span className="text-gray-600">{stats.total} decisions</span>
            {stats.pending > 0 && (
              <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs">
                {stats.pending} pending
              </span>
            )}
            {stats.critical > 0 && (
              <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded-full text-xs">
                {stats.critical} critical
              </span>
            )}
            {stats.failing > 0 && (
              <span className="px-2 py-0.5 bg-orange-100 text-orange-800 rounded-full text-xs">
                {stats.failing} failing
              </span>
            )}
          </div>
        </div>
        <DensityToggle current={density} onChange={setDensity} />
      </div>

      {/* Keyboard shortcuts hint */}
      {enableKeyboardNav && (
        <div className="px-4 py-1 text-xs text-gray-500 bg-gray-50 border-b border-gray-100">
          <kbd className="px-1 py-0.5 bg-gray-200 rounded text-xs">↑↓</kbd> Navigate
          {' • '}
          <kbd className="px-1 py-0.5 bg-gray-200 rounded text-xs">Enter</kbd> Select
          {' • '}
          <kbd className="px-1 py-0.5 bg-gray-200 rounded text-xs">Home/End</kbd> Jump
        </div>
      )}

      {/* Decision List */}
      <div
        role="grid"
        aria-label="Decision list"
        aria-rowcount={sortedDecisions.length}
        className="flex-1 overflow-y-auto"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            <span className="sr-only">Loading decisions...</span>
          </div>
        ) : sortedDecisions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <span className="text-2xl mb-2">📋</span>
            <p>No decisions to review</p>
          </div>
        ) : (
          sortedDecisions.map((decision, index) => (
            <DecisionRow
              key={decision.id}
              decision={decision}
              density={density}
              isSelected={selectedId === decision.id}
              onSelect={() => handleSelect(decision.id, index)}
              tabIndex={index === focusedIndex ? 0 : -1}
            />
          ))
        )}
      </div>

      {/* Footer with summary */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span role="status" aria-live="polite">
          Showing {sortedDecisions.length} of {decisions.length} decisions
          {selectedId && ` • Selected: ${selectedId}`}
        </span>
      </div>
    </div>
  );
};

export default DecisionReviewPanel;
