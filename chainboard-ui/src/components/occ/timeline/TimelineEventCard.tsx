/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Timeline Event Card — Individual Event Display
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Displays a single timeline event with:
 * - Category icon and color coding
 * - Timestamp and duration
 * - Agent attribution
 * - Evidence hash (immutability proof)
 * - Expandable details
 * 
 * INVARIANTS:
 * - INV-OCC-004: Timeline completeness
 * - INV-OCC-005: Evidence immutability visible
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type { TimelineEvent, TimelineEventCategory, TimelineEventSeverity } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const CATEGORY_CONFIG: Record<TimelineEventCategory, {
  icon: string;
  color: string;
  bgColor: string;
  label: string;
}> = {
  pac_lifecycle: {
    icon: '📋',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    label: 'PAC Lifecycle',
  },
  agent_activation: {
    icon: '🤖',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30',
    label: 'Agent Activation',
  },
  execution: {
    icon: '⚙️',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/30',
    label: 'Execution',
  },
  decision: {
    icon: '✅',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    label: 'Decision',
  },
  wrap: {
    icon: '📦',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
    label: 'WRAP',
  },
  review_gate: {
    icon: '🚦',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/30',
    label: 'Review Gate',
  },
  ber: {
    icon: '📄',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-900/30',
    label: 'BER',
  },
  governance: {
    icon: '⚖️',
    color: 'text-teal-400',
    bgColor: 'bg-teal-900/30',
    label: 'Governance',
  },
  error: {
    icon: '❌',
    color: 'text-red-400',
    bgColor: 'bg-red-900/30',
    label: 'Error',
  },
};

const SEVERITY_CONFIG: Record<TimelineEventSeverity, {
  borderColor: string;
  dotColor: string;
}> = {
  info: { borderColor: 'border-gray-600', dotColor: 'bg-gray-400' },
  success: { borderColor: 'border-green-600', dotColor: 'bg-green-400' },
  warning: { borderColor: 'border-yellow-600', dotColor: 'bg-yellow-400' },
  error: { borderColor: 'border-red-600', dotColor: 'bg-red-400' },
  critical: { borderColor: 'border-red-700', dotColor: 'bg-red-500 animate-pulse' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function truncateHash(hash: string, length: number = 8): string {
  if (!hash || hash.length <= length * 2) return hash;
  return `${hash.slice(0, length)}...${hash.slice(-length)}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE EVENT CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineEventCardProps {
  event: TimelineEvent;
  isSelected?: boolean;
  showEvidenceHash?: boolean;
  showArtifactLinks?: boolean;
  density?: 'compact' | 'normal' | 'expanded';
  onSelect?: (event: TimelineEvent) => void;
}

export const TimelineEventCard: React.FC<TimelineEventCardProps> = ({
  event,
  isSelected = false,
  showEvidenceHash = true,
  showArtifactLinks = true,
  density = 'normal',
  onSelect,
}) => {
  const [isExpanded, setIsExpanded] = useState(density === 'expanded');

  const categoryConfig = CATEGORY_CONFIG[event.category];
  const severityConfig = SEVERITY_CONFIG[event.severity];

  const handleClick = useCallback(() => {
    onSelect?.(event);
  }, [event, onSelect]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect?.(event);
    }
    if (e.key === 'ArrowRight' && !isExpanded) {
      setIsExpanded(true);
    }
    if (e.key === 'ArrowLeft' && isExpanded) {
      setIsExpanded(false);
    }
  }, [event, isExpanded, onSelect]);

  const toggleExpand = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(prev => !prev);
  }, []);

  if (density === 'compact') {
    return (
      <div
        className={`
          flex items-center gap-2 px-2 py-1 rounded text-xs
          ${categoryConfig.bgColor} ${severityConfig.borderColor}
          border-l-2 cursor-pointer hover:bg-gray-700/50
          ${isSelected ? 'ring-1 ring-blue-500' : ''}
        `}
        role="listitem"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        aria-label={`${event.title} at ${formatTimestamp(event.timestamp)}`}
      >
        <span className="text-gray-500">{formatTimestamp(event.timestamp)}</span>
        <span aria-hidden="true">{categoryConfig.icon}</span>
        <span className={`${categoryConfig.color} truncate`}>{event.title}</span>
        {event.agentName && (
          <span className="text-gray-500 ml-auto">{event.agentName}</span>
        )}
      </div>
    );
  }

  return (
    <article
      className={`
        relative bg-gray-800 rounded-lg border-l-4
        ${severityConfig.borderColor}
        ${isSelected ? 'ring-2 ring-blue-500' : ''}
        transition-all duration-200
      `}
      role="listitem"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-expanded={isExpanded}
      aria-label={`${categoryConfig.label}: ${event.title}`}
    >
      {/* Timeline dot */}
      <div
        className={`absolute -left-[9px] top-4 w-4 h-4 rounded-full ${severityConfig.dotColor}`}
        aria-hidden="true"
      />

      {/* Header */}
      <div className="px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg" aria-hidden="true">{categoryConfig.icon}</span>
            <div className="min-w-0">
              <h4 className={`font-medium ${categoryConfig.color} truncate`}>
                {event.title}
              </h4>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <time dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time>
                {event.durationMs && (
                  <>
                    <span>•</span>
                    <span>{formatDuration(event.durationMs)}</span>
                  </>
                )}
                {event.agentName && (
                  <>
                    <span>•</span>
                    <span className="text-purple-400">{event.agentName}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={toggleExpand}
            className="p-1 text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500 rounded"
            aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
          >
            <span className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
              ▶
            </span>
          </button>
        </div>

        {/* Description (always visible in normal mode) */}
        {density !== 'compact' && (
          <p className="mt-2 text-sm text-gray-400">{event.description}</p>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-3 pt-0 border-t border-gray-700 mt-2">
          {/* Evidence hash */}
          {showEvidenceHash && event.evidenceHash && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">Evidence Hash:</span>
              <code className="ml-2 text-xs font-mono text-teal-400 bg-gray-900 px-2 py-0.5 rounded">
                {truncateHash(event.evidenceHash, 12)}
              </code>
            </div>
          )}

          {/* Artifact links */}
          {showArtifactLinks && event.artifactIds && event.artifactIds.length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">Artifacts:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {event.artifactIds.map((artifactId) => (
                  <span
                    key={artifactId}
                    className="text-xs font-mono bg-gray-900 text-blue-400 px-2 py-0.5 rounded"
                  >
                    {artifactId}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">Metadata:</span>
              <pre className="mt-1 text-xs font-mono bg-gray-900 p-2 rounded overflow-x-auto">
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </article>
  );
};

export default TimelineEventCard;
