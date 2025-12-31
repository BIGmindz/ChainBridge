/**
 * EscalationTimeline — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * Timeline view of governance escalations.
 * Shows escalation history with status, timestamps, and resolution.
 *
 * Visual Language:
 * - L1_AGENT = Blue
 * - L2_GUARDIAN = Yellow/Amber
 * - L3_HUMAN = Red
 *
 * CONSTRAINTS:
 * - Read-only display
 * - All data from backend — verbatim
 * - Timestamps always visible
 * - Status always visible
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Clock,
  User,
  Shield,
  XCircle,
} from 'lucide-react';

import type {
  GovernanceEscalation,
  EscalationLevel,
} from '../../types/governanceState';
import { classNames } from '../../utils/classNames';

/**
 * Escalation level configuration.
 */
const LEVEL_CONFIG: Record<EscalationLevel, {
  icon: typeof Shield;
  color: string;
  bgColor: string;
  borderColor: string;
  label: string;
}> = {
  NONE: {
    icon: Shield,
    color: 'text-slate-400',
    bgColor: 'bg-slate-500/10',
    borderColor: 'border-slate-500/30',
    label: 'None',
  },
  L1_AGENT: {
    icon: Shield,
    color: 'text-sky-400',
    bgColor: 'bg-sky-500/10',
    borderColor: 'border-sky-500/30',
    label: 'L1 Agent',
  },
  L2_GUARDIAN: {
    icon: AlertTriangle,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    label: 'L2 Guardian',
  },
  L3_HUMAN: {
    icon: User,
    color: 'text-rose-400',
    bgColor: 'bg-rose-500/10',
    borderColor: 'border-rose-500/30',
    label: 'L3 Human',
  },
};

/**
 * Status configuration.
 */
const STATUS_CONFIG: Record<GovernanceEscalation['status'], {
  icon: typeof Clock;
  color: string;
  label: string;
}> = {
  PENDING: {
    icon: Clock,
    color: 'text-amber-400',
    label: 'Pending',
  },
  ACKNOWLEDGED: {
    icon: CheckCircle,
    color: 'text-sky-400',
    label: 'Acknowledged',
  },
  RESOLVED: {
    icon: CheckCircle,
    color: 'text-emerald-400',
    label: 'Resolved',
  },
  REJECTED: {
    icon: XCircle,
    color: 'text-rose-400',
    label: 'Rejected',
  },
};

/**
 * Single escalation event in timeline.
 */
function EscalationEvent({
  escalation,
  isLast,
}: {
  escalation: GovernanceEscalation;
  isLast: boolean;
}) {
  const levelConfig = LEVEL_CONFIG[escalation.level];
  const statusConfig = STATUS_CONFIG[escalation.status];
  const LevelIcon = levelConfig.icon;
  const StatusIcon = statusConfig.icon;

  return (
    <div className="relative flex gap-4">
      {/* Timeline connector */}
      {!isLast && (
        <div className="absolute left-[19px] top-10 bottom-0 w-0.5 bg-slate-700/50" />
      )}

      {/* Level indicator */}
      <div className={classNames(
        'relative z-10 flex items-center justify-center w-10 h-10 rounded-full border-2',
        levelConfig.bgColor,
        levelConfig.borderColor
      )}>
        <LevelIcon className={classNames('h-5 w-5', levelConfig.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 pb-6 min-w-0">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={classNames('font-semibold text-sm', levelConfig.color)}>
                {levelConfig.label}
              </span>
              <span className="text-slate-500">
                <ArrowRight className="h-3 w-3 inline" />
              </span>
              <span className="text-sm text-slate-300">
                {escalation.from_gid} → {escalation.to_gid}
              </span>
            </div>
            <p className="text-sm text-slate-300">{escalation.reason}</p>
          </div>

          {/* Status badge */}
          <div className={classNames(
            'flex items-center gap-1.5 px-2 py-1 rounded text-xs',
            escalation.status === 'PENDING' && 'bg-amber-500/20 text-amber-300',
            escalation.status === 'ACKNOWLEDGED' && 'bg-sky-500/20 text-sky-300',
            escalation.status === 'RESOLVED' && 'bg-emerald-500/20 text-emerald-300',
            escalation.status === 'REJECTED' && 'bg-rose-500/20 text-rose-300',
          )}>
            <StatusIcon className="h-3 w-3" />
            {statusConfig.label}
          </div>
        </div>

        {/* Timestamps */}
        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
          <span>
            Escalated: {new Date(escalation.escalated_at).toLocaleString()}
          </span>
          {escalation.resolved_at && (
            <span>
              Resolved: {new Date(escalation.resolved_at).toLocaleString()}
            </span>
          )}
        </div>

        {/* Resolution notes */}
        {escalation.resolution_notes && (
          <div className="mt-2 p-2 rounded bg-slate-800/50 border border-slate-700/50">
            <p className="text-xs text-slate-400">{escalation.resolution_notes}</p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Empty state for no escalations.
 */
function NoEscalations() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <Shield className="h-12 w-12 text-slate-600 mb-3" />
      <p className="text-sm font-medium text-slate-400">No Active Escalations</p>
      <p className="text-xs text-slate-500 mt-1">
        System is operating within governance parameters
      </p>
    </div>
  );
}

/**
 * EscalationTimeline Props.
 */
export interface EscalationTimelineProps {
  /** Escalations to display */
  escalations: GovernanceEscalation[];
  /** Show only pending escalations */
  pendingOnly?: boolean;
  /** Maximum number to show */
  maxItems?: number;
  /** Additional className */
  className?: string;
}

/**
 * Escalation Timeline Component.
 */
export function EscalationTimeline({
  escalations,
  pendingOnly = false,
  maxItems,
  className,
}: EscalationTimelineProps) {
  // Filter if needed
  let filtered = pendingOnly
    ? escalations.filter(e => e.status === 'PENDING')
    : escalations;

  // Sort by timestamp (newest first)
  filtered = [...filtered].sort(
    (a, b) => new Date(b.escalated_at).getTime() - new Date(a.escalated_at).getTime()
  );

  // Limit if needed
  if (maxItems && filtered.length > maxItems) {
    filtered = filtered.slice(0, maxItems);
  }

  if (filtered.length === 0) {
    return (
      <div className={className}>
        <NoEscalations />
      </div>
    );
  }

  return (
    <div className={classNames('space-y-0', className)}>
      {filtered.map((escalation, idx) => (
        <EscalationEvent
          key={escalation.escalation_id}
          escalation={escalation}
          isLast={idx === filtered.length - 1}
        />
      ))}
    </div>
  );
}

/**
 * Escalation summary badge for compact views.
 */
export function EscalationSummaryBadge({
  escalations,
  className,
}: {
  escalations: GovernanceEscalation[];
  className?: string;
}) {
  const pending = escalations.filter(e => e.status === 'PENDING');

  if (pending.length === 0) {
    return null;
  }

  // Get highest level
  const levels: EscalationLevel[] = ['NONE', 'L1_AGENT', 'L2_GUARDIAN', 'L3_HUMAN'];
  let highestIdx = 0;
  for (const esc of pending) {
    const idx = levels.indexOf(esc.level);
    if (idx > highestIdx) highestIdx = idx;
  }
  const highestLevel = levels[highestIdx];
  const config = LEVEL_CONFIG[highestLevel];
  const Icon = config.icon;

  return (
    <div className={classNames(
      'flex items-center gap-1.5 px-2 py-1 rounded border',
      config.bgColor,
      config.borderColor,
      className
    )}>
      <Icon className={classNames('h-3.5 w-3.5', config.color)} />
      <span className={classNames('text-xs font-medium', config.color)}>
        {pending.length} Escalation{pending.length > 1 ? 's' : ''}
      </span>
    </div>
  );
}
