/**
 * TraceTimeline Component
 * PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
 * 
 * Renders chronological timeline of trace events.
 * Click-through from PDO → Agent → Settlement → Ledger.
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-TRACE-004: OC renders full chain without inference
 */

import React from 'react';
import type { OCTraceTimeline, TraceTimelineEvent, TraceDomain } from '../../types/trace';

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN COLORS
// ═══════════════════════════════════════════════════════════════════════════════

const DOMAIN_COLORS: Record<TraceDomain, { bg: string; text: string; border: string }> = {
  DECISION: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-500' },
  EXECUTION: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-500' },
  SETTLEMENT: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-500' },
  LEDGER: { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-500' },
};

const DOMAIN_ICONS: Record<TraceDomain, string> = {
  DECISION: '📋',
  EXECUTION: '⚙️',
  SETTLEMENT: '✅',
  LEDGER: '📒',
};

// ═══════════════════════════════════════════════════════════════════════════════
// PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface TraceTimelineProps {
  timeline: OCTraceTimeline;
  onEventClick?: (event: TraceTimelineEvent) => void;
  compact?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

function formatLinkType(linkType: string): string {
  return linkType.replace(/_/g, ' → ').replace('TO', '');
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE EVENT COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineEventItemProps {
  event: TraceTimelineEvent;
  isLast: boolean;
  onClick?: () => void;
  compact?: boolean;
}

const TimelineEventItem: React.FC<TimelineEventItemProps> = ({
  event,
  isLast,
  onClick,
  compact = false,
}) => {
  const colors = DOMAIN_COLORS[event.target_domain];
  const icon = DOMAIN_ICONS[event.target_domain];

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-4 top-8 bottom-0 w-0.5 bg-gray-200" />
      )}

      {/* Icon */}
      <div
        className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full ${colors.bg} ${colors.border} border-2`}
      >
        <span className="text-sm">{icon}</span>
      </div>

      {/* Content */}
      <div
        className={`flex-1 pb-4 ${onClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
        onClick={onClick}
      >
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}>
            {event.target_domain}
          </span>
          <span className="text-xs text-gray-500">
            {formatTimestamp(event.timestamp)}
          </span>
        </div>

        {!compact && (
          <>
            <p className="mt-1 text-sm text-gray-700">
              {formatLinkType(event.event_type)}
            </p>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500">
              <span>
                From: <code className="bg-gray-100 px-1 rounded">{event.source_id}</code>
              </span>
              <span>→</span>
              <span>
                To: <code className="bg-gray-100 px-1 rounded">{event.target_id}</code>
              </span>
            </div>
            {event.agent_gid && (
              <div className="mt-1 text-xs text-gray-500">
                Agent: <code className="bg-gray-100 px-1 rounded">{event.agent_gid}</code>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const TraceTimeline: React.FC<TraceTimelineProps> = ({
  timeline,
  onEventClick,
  compact = false,
}) => {
  if (timeline.events.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>No trace events found for this PDO</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          Trace Timeline
        </h3>
        <p className="text-xs text-gray-500 mt-0.5">
          PDO: {timeline.pdo_id} • {timeline.event_count} events
        </p>
      </div>

      {/* Timeline */}
      <div className="p-4">
        {timeline.events.map((event, index) => (
          <TimelineEventItem
            key={event.event_id}
            event={event}
            isLast={index === timeline.events.length - 1}
            onClick={onEventClick ? () => onEventClick(event) : undefined}
            compact={compact}
          />
        ))}
      </div>
    </div>
  );
};

export default TraceTimeline;
