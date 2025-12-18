/**
 * Governance Event Row — PAC-SONNY-02 + PAC-SONNY-03
 *
 * Displays one governance event with all required fields.
 * Read-only — no actions, no buttons, no interactive elements.
 *
 * Styling rules:
 * - DENY / VIOLATION → red accent
 * - ALLOW / VERIFIED → neutral
 * - ESCALATE / DRCP → amber
 * - No icons that imply action
 * - Risk annotations shown as informational only (PAC-SONNY-03)
 *
 * CONSTRAINTS:
 * - Renders fields exactly as emitted
 * - No reinterpretation
 * - No summarization
 * - No conditional hiding
 * - Risk is informational — does not affect decision
 *
 * @see PAC-SONNY-02 — Governance Timeline (Read-Only) UI
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 */

import { classNames } from '../../utils/classNames';
import type { GovernanceEvent } from '../../types/governance';
import { GovernanceRiskBadge, GovernanceRiskDisclaimer } from './GovernanceRiskBadge';
import { GovernanceRiskEmptyState } from './GovernanceRiskEmptyState';

export interface GovernanceEventRowProps {
  /** The governance event to display */
  event: GovernanceEvent;
  /** Optional additional className */
  className?: string;
}

/**
 * Determines accent color based on decision/event_type.
 * No frontend reinterpretation — just visual styling.
 */
function getAccentStyle(event: GovernanceEvent): {
  borderColor: string;
  dotColor: string;
} {
  const decision = event.decision?.toUpperCase() ?? '';
  const eventType = event.event_type?.toUpperCase() ?? '';

  // DENY / VIOLATION → red accent
  if (
    decision === 'DENY' ||
    decision === 'VIOLATION' ||
    eventType.includes('DENY') ||
    eventType.includes('VIOLATION')
  ) {
    return {
      borderColor: 'border-l-rose-500',
      dotColor: 'bg-rose-500',
    };
  }

  // ESCALATE / DRCP → amber accent
  if (
    decision === 'ESCALATE' ||
    eventType.includes('ESCALATE') ||
    eventType.includes('DRCP')
  ) {
    return {
      borderColor: 'border-l-amber-500',
      dotColor: 'bg-amber-500',
    };
  }

  // ALLOW / VERIFIED → neutral (slate)
  // Default for all other events
  return {
    borderColor: 'border-l-slate-600',
    dotColor: 'bg-slate-500',
  };
}

/**
 * Single governance event row.
 * Read-only display of all event fields.
 */
export function GovernanceEventRow({
  event,
  className,
}: GovernanceEventRowProps): JSX.Element {
  const accent = getAccentStyle(event);

  return (
    <div
      className={classNames(
        'border-l-4 bg-slate-800/30 rounded-r-lg px-4 py-3',
        accent.borderColor,
        className
      )}
      role="listitem"
    >
      {/* Top row: Timestamp + Event Type */}
      <div className="flex items-center justify-between gap-4 mb-2">
        <div className="flex items-center gap-2">
          {/* Timeline dot */}
          <span
            className={classNames('h-2 w-2 rounded-full flex-shrink-0', accent.dotColor)}
            aria-hidden="true"
          />
          {/* Event type — verbatim */}
          <span className="text-sm font-semibold text-slate-200">
            {event.event_type}
          </span>
        </div>
        {/* Timestamp — UTC, ISO */}
        <time
          dateTime={event.timestamp}
          className="text-xs text-slate-500 font-mono flex-shrink-0"
        >
          {event.timestamp}
        </time>
      </div>

      {/* Event details grid */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
        {/* Agent GID — always present */}
        <div>
          <span className="text-slate-500">Agent:</span>{' '}
          <span className="text-slate-300 font-mono">{event.agent_gid}</span>
        </div>

        {/* Verb — if present */}
        {event.verb && (
          <div>
            <span className="text-slate-500">Verb:</span>{' '}
            <span className="text-slate-300 font-mono">{event.verb}</span>
          </div>
        )}

        {/* Target — if present */}
        {event.target && (
          <div>
            <span className="text-slate-500">Target:</span>{' '}
            <span className="text-slate-300 font-mono">{event.target}</span>
          </div>
        )}

        {/* Decision — if present */}
        {event.decision && (
          <div>
            <span className="text-slate-500">Decision:</span>{' '}
            <span
              className={classNames(
                'font-mono font-semibold',
                event.decision.toUpperCase() === 'DENY'
                  ? 'text-rose-400'
                  : event.decision.toUpperCase() === 'ESCALATE'
                  ? 'text-amber-400'
                  : 'text-slate-300'
              )}
            >
              {event.decision}
            </span>
          </div>
        )}

        {/* Reason Code — if present */}
        {event.reason_code && (
          <div>
            <span className="text-slate-500">Reason:</span>{' '}
            <span className="text-slate-300 font-mono">{event.reason_code}</span>
          </div>
        )}

        {/* Audit Ref — always visible if present */}
        {event.audit_ref && (
          <div className="col-span-2">
            <span className="text-slate-500">Audit Ref:</span>{' '}
            <span className="text-slate-400 font-mono">{event.audit_ref}</span>
          </div>
        )}
      </div>

      {/* Risk Annotation Section — PAC-SONNY-03 */}
      {/* Informational only — does not affect decision */}
      <RiskAnnotationSection event={event} />
    </div>
  );
}

/**
 * Risk annotation section — PAC-SONNY-03
 *
 * Displays risk annotation if present.
 * Explicitly handles missing/unavailable states.
 * Never renders alone — always secondary to governance decision.
 *
 * CONSTRAINTS:
 * - No charts
 * - No aggregation
 * - No color dominance over DENY / ESCALATE
 * - Informational only
 */
function RiskAnnotationSection({
  event,
}: {
  event: GovernanceEvent;
}): JSX.Element | null {
  const status = event.risk_annotation_status ?? 'none';
  const annotation = event.risk_annotation;

  // If status indicates no risk or unavailable, show explicit state
  if (status === 'none' || status === 'unavailable') {
    return (
      <div className="mt-3 pt-3 border-t border-slate-700/30">
        <GovernanceRiskEmptyState status={status} />
      </div>
    );
  }

  // If status is 'present' but no annotation data, fail closed
  if (!annotation) {
    return (
      <div className="mt-3 pt-3 border-t border-slate-700/30">
        <GovernanceRiskEmptyState status="unavailable" />
      </div>
    );
  }

  // Render risk annotation — informational only
  return (
    <div className="mt-3 pt-3 border-t border-slate-700/30 space-y-2">
      {/* Risk badge with category */}
      <div className="flex items-center justify-between gap-2">
        <GovernanceRiskBadge category={annotation.category} />
        <GovernanceRiskDisclaimer />
      </div>

      {/* Risk details — verbatim, no reinterpretation */}
      <div className="text-xs space-y-1 pl-1">
        {/* Rationale — short, verbatim */}
        <div>
          <span className="text-slate-500">Rationale:</span>{' '}
          <span className="text-slate-400">{annotation.rationale}</span>
        </div>

        {/* Confidence interval — if present */}
        {annotation.confidence_interval && (
          <div>
            <span className="text-slate-500">Confidence:</span>{' '}
            <span className="text-slate-400 font-mono">
              {annotation.confidence_interval}
            </span>
          </div>
        )}

        {/* Source — if present */}
        {annotation.source && (
          <div>
            <span className="text-slate-500">Source:</span>{' '}
            <span className="text-slate-400 font-mono">{annotation.source}</span>
          </div>
        )}

        {/* Assessed at — if present */}
        {annotation.assessed_at && (
          <div>
            <span className="text-slate-500">Assessed:</span>{' '}
            <time
              dateTime={annotation.assessed_at}
              className="text-slate-500 font-mono"
            >
              {annotation.assessed_at}
            </time>
          </div>
        )}
      </div>
    </div>
  );
}
