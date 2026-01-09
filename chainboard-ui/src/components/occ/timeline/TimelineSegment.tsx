/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Timeline Segment — PAC Lifecycle Phase Visualization
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Displays a segment of the PAC lifecycle:
 * - Phase header with progress indicator
 * - Contained events
 * - Duration and status
 * 
 * INVARIANTS:
 * - INV-OCC-004: Timeline completeness
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import type { TimelineSegment as SegmentType, TimelineEvent } from './types';
import { TimelineEventCard } from './TimelineEventCard';

// ═══════════════════════════════════════════════════════════════════════════════
// SEGMENT STATUS CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_CONFIG = {
  pending: {
    color: 'text-gray-500',
    bgColor: 'bg-gray-800',
    borderColor: 'border-gray-700',
    progressColor: 'bg-gray-600',
    icon: '○',
  },
  active: {
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/20',
    borderColor: 'border-blue-700',
    progressColor: 'bg-blue-500',
    icon: '●',
  },
  complete: {
    color: 'text-green-400',
    bgColor: 'bg-green-900/20',
    borderColor: 'border-green-700',
    progressColor: 'bg-green-500',
    icon: '✓',
  },
  failed: {
    color: 'text-red-400',
    bgColor: 'bg-red-900/20',
    borderColor: 'border-red-700',
    progressColor: 'bg-red-500',
    icon: '✗',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function formatDuration(start: string, end?: string): string {
  const startDate = new Date(start);
  const endDate = end ? new Date(end) : new Date();
  const durationMs = endDate.getTime() - startDate.getTime();

  if (durationMs < 1000) return `${durationMs}ms`;
  if (durationMs < 60000) return `${(durationMs / 1000).toFixed(1)}s`;
  if (durationMs < 3600000) return `${(durationMs / 60000).toFixed(1)}m`;
  return `${(durationMs / 3600000).toFixed(1)}h`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE SEGMENT COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineSegmentProps {
  segment: SegmentType;
  isLast?: boolean;
  density?: 'compact' | 'normal' | 'expanded';
  showEvidenceHashes?: boolean;
  showArtifactLinks?: boolean;
  onEventSelect?: (event: TimelineEvent) => void;
  selectedEventId?: string;
}

export const TimelineSegment: React.FC<TimelineSegmentProps> = ({
  segment,
  isLast = false,
  density = 'normal',
  showEvidenceHashes = true,
  showArtifactLinks = true,
  onEventSelect,
  selectedEventId,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const statusConfig = STATUS_CONFIG[segment.status];

  const toggleCollapse = useCallback(() => {
    setIsCollapsed(prev => !prev);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleCollapse();
    }
  }, [toggleCollapse]);

  return (
    <section
      className={`relative ${isLast ? '' : 'pb-6'}`}
      aria-label={`${segment.label} phase`}
    >
      {/* Connecting line (if not last) */}
      {!isLast && (
        <div
          className="absolute left-[7px] top-8 bottom-0 w-0.5 bg-gray-700"
          aria-hidden="true"
        />
      )}

      {/* Segment header */}
      <div
        className={`
          flex items-center gap-3 p-3 rounded-lg cursor-pointer
          ${statusConfig.bgColor} border ${statusConfig.borderColor}
          hover:bg-opacity-80 transition-colors
        `}
        role="button"
        tabIndex={0}
        onClick={toggleCollapse}
        onKeyDown={handleKeyDown}
        aria-expanded={!isCollapsed}
        aria-controls={`segment-events-${segment.segmentId}`}
      >
        {/* Status indicator */}
        <div
          className={`
            w-4 h-4 rounded-full flex items-center justify-center text-xs font-bold
            ${statusConfig.progressColor} text-white
          `}
          aria-hidden="true"
        >
          {statusConfig.icon}
        </div>

        {/* Label and info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className={`font-medium ${statusConfig.color}`}>
              {segment.label}
            </h3>
            <span className="text-xs text-gray-500">
              ({segment.events.length} events)
            </span>
          </div>

          {/* Progress bar */}
          {segment.status === 'active' && (
            <div className="mt-1 w-full bg-gray-700 rounded-full h-1.5">
              <div
                className={`${statusConfig.progressColor} h-1.5 rounded-full transition-all`}
                style={{ width: `${segment.progress}%` }}
                role="progressbar"
                aria-valuenow={segment.progress}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          )}
        </div>

        {/* Duration */}
        <div className="text-xs text-gray-500">
          {formatDuration(segment.startTime, segment.endTime)}
          {segment.status === 'active' && ' (ongoing)'}
        </div>

        {/* Collapse indicator */}
        <span
          className={`text-gray-500 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
          aria-hidden="true"
        >
          ▶
        </span>
      </div>

      {/* Events list */}
      {!isCollapsed && segment.events.length > 0 && (
        <div
          id={`segment-events-${segment.segmentId}`}
          className="ml-6 mt-3 space-y-2"
          role="list"
          aria-label={`Events in ${segment.label}`}
        >
          {segment.events.map((event) => (
            <TimelineEventCard
              key={event.eventId}
              event={event}
              density={density}
              showEvidenceHash={showEvidenceHashes}
              showArtifactLinks={showArtifactLinks}
              onSelect={onEventSelect}
              isSelected={event.eventId === selectedEventId}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isCollapsed && segment.events.length === 0 && segment.status === 'pending' && (
        <div className="ml-6 mt-3 text-sm text-gray-500 italic">
          Awaiting events...
        </div>
      )}
    </section>
  );
};

export default TimelineSegment;
