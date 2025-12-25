/**
 * PacTimelineView — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Timeline view showing PAC lifecycle events.
 * Displays corrections, closures, and all ledger entries.
 *
 * UX RULES (FAIL-CLOSED):
 * - corrections_must_show_lineage: Correction nodes show what they fixed
 * - blocked_means_disabled: Blocked states visually distinct
 * - no_green_without_positive_closure: Only positive closure gets green
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import React, { useState } from 'react';
import type { TimelineNode, LedgerEntryType } from '../../types/governanceLedger';
import { PositiveClosureBadge } from './PositiveClosureBadge';

export interface PacTimelineViewProps {
  /** Timeline nodes to display */
  nodes: TimelineNode[];
  /** Title */
  title?: string;
  /** Show filter controls */
  showFilters?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Max items to show (0 = all) */
  maxItems?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get icon for timeline entry type.
 */
function getEntryIcon(type: LedgerEntryType): React.ReactNode {
  const iconClass = "w-4 h-4";
  
  switch (type) {
    case 'PAC_CREATED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
      );
    case 'PAC_STARTED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
          <polygon points="10 8 16 12 10 16 10 8" />
        </svg>
      );
    case 'PAC_BLOCKED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
          <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
        </svg>
      );
    case 'CORRECTION_ISSUED':
    case 'CORRECTION_APPLIED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      );
    case 'WRAP_SUBMITTED':
    case 'WRAP_VALIDATED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      );
    case 'WRAP_REJECTED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <line x1="9" y1="9" x2="15" y2="15" />
          <line x1="15" y1="9" x2="9" y2="15" />
        </svg>
      );
    case 'RATIFICATION_REQUESTED':
    case 'RATIFICATION_APPROVED':
    case 'RATIFICATION_DENIED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case 'POSITIVE_CLOSURE':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case 'NEGATIVE_CLOSURE':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      );
    case 'ESCALATION_RAISED':
    case 'ESCALATION_RESOLVED':
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      );
    default:
      return (
        <svg className={iconClass} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
        </svg>
      );
  }
}

/**
 * Get status colors for timeline node.
 */
function getStatusColors(status: TimelineNode['status']) {
  switch (status) {
    case 'success':
      return {
        bg: 'bg-green-100 dark:bg-green-900/30',
        border: 'border-green-500',
        text: 'text-green-700 dark:text-green-300',
        icon: 'text-green-600 dark:text-green-400',
      };
    case 'warning':
      return {
        bg: 'bg-amber-100 dark:bg-amber-900/30',
        border: 'border-amber-500',
        text: 'text-amber-700 dark:text-amber-300',
        icon: 'text-amber-600 dark:text-amber-400',
      };
    case 'error':
    case 'blocked':
      return {
        bg: 'bg-red-100 dark:bg-red-900/30',
        border: 'border-red-500',
        text: 'text-red-700 dark:text-red-300',
        icon: 'text-red-600 dark:text-red-400',
      };
    case 'info':
    default:
      return {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        border: 'border-blue-500',
        text: 'text-blue-700 dark:text-blue-300',
        icon: 'text-blue-600 dark:text-blue-400',
      };
  }
}

/**
 * Agent badge with color.
 */
function AgentBadge({ agent }: { agent: TimelineNode['agent'] }) {
  const colorMap: Record<string, string> = {
    RED: 'bg-red-500',
    YELLOW: 'bg-yellow-500',
    GREEN: 'bg-green-500',
    BLUE: 'bg-blue-500',
    PURPLE: 'bg-purple-500',
    PINK: 'bg-pink-500',
    ORANGE: 'bg-orange-500',
    GRAY: 'bg-gray-500',
  };

  const bgColor = colorMap[agent.color] || 'bg-gray-500';

  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span className={`w-2 h-2 rounded-full ${bgColor}`} />
      <span className="text-gray-600 dark:text-gray-400">
        {agent.name} ({agent.gid})
      </span>
    </span>
  );
}

/**
 * Single timeline node.
 */
function TimelineNodeItem({
  node,
  isFirst,
  isLast,
  compact,
}: {
  node: TimelineNode;
  isFirst: boolean;
  isLast: boolean;
  compact: boolean;
}) {
  const colors = getStatusColors(node.status);

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        {/* Top connector */}
        {!isFirst && (
          <div className="w-0.5 h-4 bg-gray-300 dark:bg-gray-600" />
        )}
        
        {/* Node icon */}
        <div className={`
          w-8 h-8 rounded-full flex items-center justify-center
          ${colors.bg} ${colors.icon} border-2 ${colors.border}
        `}>
          {getEntryIcon(node.type)}
        </div>

        {/* Bottom connector */}
        {!isLast && (
          <div className="w-0.5 flex-1 min-h-[24px] bg-gray-300 dark:bg-gray-600" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 pb-4 ${compact ? 'pb-2' : ''}`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <p className={`text-sm font-medium ${colors.text}`}>
              {node.label}
            </p>
            {!compact && (
              <div className="flex items-center gap-2 mt-1">
                <AgentBadge agent={node.agent} />
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {formatTimestamp(node.timestamp)}
                </span>
              </div>
            )}
          </div>

          {/* Closure badge */}
          {node.is_closure && node.closure_type && (
            <PositiveClosureBadge
              closureType={node.closure_type}
              size="sm"
              showLabel={!compact}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Filter chip.
 */
function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-3 py-1 text-xs font-medium rounded-full
        ${active
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
        }
        hover:opacity-80 transition-opacity
      `}
    >
      {label}
    </button>
  );
}

/**
 * Format timestamp for display.
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString();
  } catch {
    return timestamp;
  }
}

type FilterType = 'all' | 'corrections' | 'closures' | 'blocks';

/**
 * PacTimelineView component.
 *
 * Displays PAC lifecycle as a visual timeline.
 */
export function PacTimelineView({
  nodes,
  title = 'PAC Timeline',
  showFilters = true,
  compact = false,
  maxItems = 0,
  className = '',
}: PacTimelineViewProps) {
  const [filter, setFilter] = useState<FilterType>('all');

  // Filter nodes
  const filteredNodes = nodes.filter((node) => {
    if (filter === 'all') return true;
    if (filter === 'corrections') return node.is_correction;
    if (filter === 'closures') return node.is_closure;
    if (filter === 'blocks') return node.status === 'blocked';
    return true;
  });

  // Limit items if maxItems > 0
  const displayNodes = maxItems > 0 ? filteredNodes.slice(-maxItems) : filteredNodes;

  // Empty state
  if (nodes.length === 0) {
    return (
      <div className={`p-4 text-center text-gray-500 dark:text-gray-400 ${className}`}>
        No timeline events
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {filteredNodes.length} events
        </span>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
          <FilterChip
            label="All"
            active={filter === 'all'}
            onClick={() => setFilter('all')}
          />
          <FilterChip
            label="Corrections"
            active={filter === 'corrections'}
            onClick={() => setFilter('corrections')}
          />
          <FilterChip
            label="Closures"
            active={filter === 'closures'}
            onClick={() => setFilter('closures')}
          />
          <FilterChip
            label="Blocks"
            active={filter === 'blocks'}
            onClick={() => setFilter('blocks')}
          />
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {displayNodes.map((node, index) => (
          <TimelineNodeItem
            key={node.id}
            node={node}
            isFirst={index === 0}
            isLast={index === displayNodes.length - 1}
            compact={compact}
          />
        ))}
      </div>

      {/* Truncation notice */}
      {maxItems > 0 && filteredNodes.length > maxItems && (
        <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-2">
          Showing last {maxItems} of {filteredNodes.length} events
        </div>
      )}
    </div>
  );
}

export default PacTimelineView;
