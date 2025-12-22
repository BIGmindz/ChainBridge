/**
 * Governance Timeline Panel — PAC-SONNY-02
 *
 * Renders an ordered list of governance events.
 * Read-only — no actions, no buttons, no mutations.
 *
 * CONSTRAINTS:
 * - Sorted by timestamp (descending)
 * - No pagination logic (backend responsibility)
 * - No conditional hiding
 * - No summarization
 * - No filters that alter data
 * - No interactive elements
 *
 * This is a viewer, not a controller.
 *
 * @see PAC-SONNY-02 — Governance Timeline (Read-Only) UI
 */

import { useMemo } from 'react';
import { ScrollText, AlertTriangle } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import { GovernanceEventRow } from './GovernanceEventRow';
import { GovernanceTimelineEmptyState } from './GovernanceTimelineEmptyState';
import type { GovernanceEvent } from '../../types/governance';

export interface GovernanceTimelinePanelProps {
  /** Array of governance events to display */
  events: GovernanceEvent[];
  /** Optional additional className */
  className?: string;
}

/**
 * Error boundary fallback for malformed events.
 * Fails closed — displays error, no partial render.
 */
function TimelineErrorState({
  message,
}: {
  message: string;
}): JSX.Element {
  return (
    <Card className="border-rose-500/40 bg-rose-500/5">
      <CardContent className="py-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-6 w-6 text-rose-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-rose-300">
              Timeline Render Failed
            </p>
            <p className="text-xs text-rose-400/80">{message}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Validates an event has required fields.
 * Returns error message if invalid, null if valid.
 */
function validateEvent(event: GovernanceEvent, index: number): string | null {
  if (!event) {
    return `Event at index ${index} is null or undefined`;
  }
  if (!event.event_id) {
    return `Event at index ${index} missing event_id`;
  }
  if (!event.timestamp) {
    return `Event ${event.event_id} missing timestamp`;
  }
  if (!event.event_type) {
    return `Event ${event.event_id} missing event_type`;
  }
  if (!event.agent_gid) {
    return `Event ${event.event_id} missing agent_gid`;
  }
  return null;
}

/**
 * Main governance timeline panel.
 * Renders events sorted by timestamp (descending).
 */
export function GovernanceTimelinePanel({
  events,
  className,
}: GovernanceTimelinePanelProps): JSX.Element {
  // Validate all events and collect errors
  const validationError = useMemo(() => {
    if (!Array.isArray(events)) {
      return 'Events must be an array';
    }
    for (let i = 0; i < events.length; i++) {
      const error = validateEvent(events[i], i);
      if (error) return error;
    }
    return null;
  }, [events]);

  // Fail closed on validation error
  if (validationError) {
    return <TimelineErrorState message={validationError} />;
  }

  // Sort events by timestamp (descending) — no mutation
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [events]);

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <ScrollText className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Governance Timeline
          </h3>
          <span className="text-xs text-slate-500">
            ({events.length} event{events.length !== 1 ? 's' : ''})
          </span>
        </div>
      </CardHeader>

      <CardContent className="py-4">
        {sortedEvents.length === 0 ? (
          <GovernanceTimelineEmptyState />
        ) : (
          <div
            role="list"
            aria-label="Governance events"
            className="space-y-3"
          >
            {sortedEvents.map((event) => (
              <GovernanceEventRow
                key={event.event_id}
                event={event}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
