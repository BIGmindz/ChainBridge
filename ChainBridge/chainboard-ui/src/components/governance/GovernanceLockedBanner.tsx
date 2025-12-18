/**
 * Governance Locked Banner — PAC-DIGGI-05-FE
 *
 * Visual indicator when governance has locked an action or resource.
 * Part of the standardized governance visual language.
 *
 * Visual Language (icons only, no emojis):
 * - ❌ DENY = red, XCircle icon
 * - 🟡 PROPOSE = yellow, read-only
 * - 🔒 GOVERNANCE LOCKED = banner with Lock icon
 *
 * CONSTRAINTS:
 * - Read-only display — no actions
 * - No retry buttons
 * - No free-text inputs
 * - Renders backend-provided data verbatim
 *
 * @see PAC-DIGGI-05-FE — Diggi Operator UX
 */

import { Lock, XCircle, AlertTriangle, Info } from 'lucide-react';

import { classNames } from '../../utils/classNames';

/**
 * Governance lock status types.
 */
export type GovernanceLockStatus = 'LOCKED' | 'DENIED' | 'PROPOSED' | 'INFO';

/**
 * Props for GovernanceLockedBanner.
 */
export interface GovernanceLockedBannerProps {
  /** The lock status to display */
  status: GovernanceLockStatus;
  /** Main message — rendered verbatim */
  message: string;
  /** Optional detail — rendered verbatim */
  detail?: string;
  /** Optional agent GID that caused the lock */
  agentGid?: string;
  /** Optional governance rule that was violated */
  ruleViolated?: string;
  /** Optional timestamp */
  timestamp?: string;
  /** Optional correlation ID for audit */
  correlationId?: string;
  /** Optional additional className */
  className?: string;
}

/**
 * Configuration for each lock status type.
 */
const statusConfig: Record<
  GovernanceLockStatus,
  {
    icon: typeof Lock;
    bgColor: string;
    borderColor: string;
    textColor: string;
    label: string;
  }
> = {
  LOCKED: {
    icon: Lock,
    bgColor: 'bg-slate-500/10',
    borderColor: 'border-slate-500/40',
    textColor: 'text-slate-300',
    label: 'GOVERNANCE LOCKED',
  },
  DENIED: {
    icon: XCircle,
    bgColor: 'bg-rose-500/10',
    borderColor: 'border-rose-500/40',
    textColor: 'text-rose-300',
    label: 'DENY',
  },
  PROPOSED: {
    icon: AlertTriangle,
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/40',
    textColor: 'text-amber-300',
    label: 'PROPOSE',
  },
  INFO: {
    icon: Info,
    bgColor: 'bg-sky-500/10',
    borderColor: 'border-sky-500/40',
    textColor: 'text-sky-300',
    label: 'INFO',
  },
};

/**
 * Governance locked banner component.
 * Displays a prominent banner when governance has locked an action.
 */
export function GovernanceLockedBanner({
  status,
  message,
  detail,
  agentGid,
  ruleViolated,
  timestamp,
  correlationId,
  className,
}: GovernanceLockedBannerProps): JSX.Element {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={classNames(
        'rounded-lg border px-4 py-4',
        config.bgColor,
        config.borderColor,
        className
      )}
      role="alert"
      aria-live="polite"
    >
      {/* Header with icon and label */}
      <div className="flex items-start gap-3">
        <Icon className={classNames('h-6 w-6 flex-shrink-0 mt-0.5', config.textColor)} />
        <div className="flex-1 min-w-0 space-y-2">
          {/* Status label */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={classNames('text-xs font-semibold uppercase tracking-wider', config.textColor)}>
              {config.label}
            </span>
            {agentGid && (
              <span className="text-xs text-slate-500 font-mono">
                Agent: {agentGid}
              </span>
            )}
          </div>

          {/* Main message — verbatim */}
          <p className={classNames('text-sm font-medium leading-relaxed', config.textColor)}>
            {message}
          </p>

          {/* Detail — verbatim */}
          {detail && (
            <p className="text-sm text-slate-400 leading-relaxed">
              {detail}
            </p>
          )}

          {/* Rule violated */}
          {ruleViolated && (
            <p className="text-xs text-slate-500">
              Rule violated:{' '}
              <code className="text-slate-400">{ruleViolated}</code>
            </p>
          )}

          {/* Metadata row */}
          {(timestamp || correlationId) && (
            <div className="flex items-center gap-4 pt-2 text-xs text-slate-600">
              {timestamp && (
                <span>Time: {timestamp}</span>
              )}
              {correlationId && (
                <span>
                  Correlation:{' '}
                  <code className="text-slate-500">{correlationId}</code>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Shorthand component for DENY status.
 */
export function GovernanceDenyBanner(
  props: Omit<GovernanceLockedBannerProps, 'status'>
): JSX.Element {
  return <GovernanceLockedBanner status="DENIED" {...props} />;
}

/**
 * Shorthand component for LOCKED status.
 */
export function GovernanceLockBanner(
  props: Omit<GovernanceLockedBannerProps, 'status'>
): JSX.Element {
  return <GovernanceLockedBanner status="LOCKED" {...props} />;
}

/**
 * Shorthand component for PROPOSE status.
 */
export function GovernanceProposeBanner(
  props: Omit<GovernanceLockedBannerProps, 'status'>
): JSX.Element {
  return <GovernanceLockedBanner status="PROPOSED" {...props} />;
}
