/**
 * Governance Risk Empty State — PAC-SONNY-03
 *
 * Explicit empty/error states for risk annotation display.
 * Fails closed — never infers risk data.
 *
 * States:
 * - "No risk annotation available" — normal, no risk data
 * - "Risk engine unavailable" — system error state
 *
 * CONSTRAINTS:
 * - No buttons
 * - No retry affordance
 * - Exact text only
 * - Fail closed
 *
 * @see PAC-SONNY-03 — Risk Annotation (Read-Only)
 */

import { Info, AlertTriangle } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import type { RiskAnnotationStatus } from '../../types/governance';

export interface GovernanceRiskEmptyStateProps {
  /** The status that determines which message to show */
  status: RiskAnnotationStatus;
  /** Optional additional className */
  className?: string;
}

/**
 * Configuration for each risk annotation status.
 */
const statusConfig: Record<
  Exclude<RiskAnnotationStatus, 'present'>,
  {
    icon: typeof Info;
    message: string;
    iconColor: string;
    textColor: string;
  }
> = {
  none: {
    icon: Info,
    message: 'No risk annotation available',
    iconColor: 'text-slate-600',
    textColor: 'text-slate-600',
  },
  unavailable: {
    icon: AlertTriangle,
    message: 'Risk engine unavailable',
    iconColor: 'text-slate-500',
    textColor: 'text-slate-500',
  },
};

/**
 * Empty/error state for risk annotations.
 * Renders explicit message based on status.
 */
export function GovernanceRiskEmptyState({
  status,
  className,
}: GovernanceRiskEmptyStateProps): JSX.Element | null {
  // 'present' status means risk data exists — don't render empty state
  if (status === 'present') {
    return null;
  }

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={classNames(
        'flex items-center gap-2 py-1',
        className
      )}
    >
      <Icon
        className={classNames('h-3.5 w-3.5 flex-shrink-0', config.iconColor)}
        aria-hidden="true"
      />
      {/* Exact text — no variation */}
      <span className={classNames('text-xs italic', config.textColor)}>
        {config.message}
      </span>
    </div>
  );
}
