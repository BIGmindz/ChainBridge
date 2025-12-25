/**
 * PositiveClosureBadge — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Visual indicator for positive closure status.
 * Shows locked state with visual lock icon when PAC has positive closure.
 *
 * UX RULES (FAIL-CLOSED):
 * - no_green_without_positive_closure: Only shows green for POSITIVE_CLOSURE
 * - closure_requires_badge: Badge must be visible for any closure
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import React from 'react';
import type { ClosureType, PACLifecycleState } from '../../types/governanceLedger';

export interface PositiveClosureBadgeProps {
  /** Closure type */
  closureType: ClosureType;
  /** PAC lifecycle state (fallback if closureType is NONE) */
  state?: PACLifecycleState;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show text label */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Lock icon SVG component.
 */
function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

/**
 * Unlock icon SVG component.
 */
function UnlockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 9.9-1" />
    </svg>
  );
}

/**
 * Block icon SVG component.
 */
function BlockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
    </svg>
  );
}

/**
 * Check icon SVG component.
 */
function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="20,6 9,17 4,12" />
    </svg>
  );
}

/**
 * Get badge configuration based on closure type.
 */
function getBadgeConfig(closureType: ClosureType, state?: PACLifecycleState) {
  // POSITIVE_CLOSURE — Green with lock
  if (closureType === 'POSITIVE_CLOSURE') {
    return {
      bgColor: 'bg-green-100 dark:bg-green-900/30',
      textColor: 'text-green-800 dark:text-green-200',
      borderColor: 'border-green-300 dark:border-green-700',
      icon: LockIcon,
      label: 'Positive Closure',
      ariaLabel: 'PAC has positive closure - locked and acknowledged',
    };
  }

  // NEGATIVE_CLOSURE — Red with block
  if (closureType === 'NEGATIVE_CLOSURE') {
    return {
      bgColor: 'bg-red-100 dark:bg-red-900/30',
      textColor: 'text-red-800 dark:text-red-200',
      borderColor: 'border-red-300 dark:border-red-700',
      icon: BlockIcon,
      label: 'Negative Closure',
      ariaLabel: 'PAC has negative closure - rejected',
    };
  }

  // CORRECTION_CLOSURE — Amber with check
  if (closureType === 'CORRECTION_CLOSURE') {
    return {
      bgColor: 'bg-amber-100 dark:bg-amber-900/30',
      textColor: 'text-amber-800 dark:text-amber-200',
      borderColor: 'border-amber-300 dark:border-amber-700',
      icon: CheckIcon,
      label: 'Correction Closure',
      ariaLabel: 'PAC correction cycle complete',
    };
  }

  // ARCHIVED — Gray with lock
  if (closureType === 'ARCHIVED') {
    return {
      bgColor: 'bg-gray-100 dark:bg-gray-800',
      textColor: 'text-gray-600 dark:text-gray-400',
      borderColor: 'border-gray-300 dark:border-gray-600',
      icon: LockIcon,
      label: 'Archived',
      ariaLabel: 'PAC is archived',
    };
  }

  // NONE — Check state for blocked
  if (state === 'BLOCKED' || state === 'REJECTED') {
    return {
      bgColor: 'bg-red-100 dark:bg-red-900/30',
      textColor: 'text-red-800 dark:text-red-200',
      borderColor: 'border-red-300 dark:border-red-700',
      icon: BlockIcon,
      label: 'Blocked',
      ariaLabel: 'PAC is blocked',
    };
  }

  // Default — Open state (no closure yet)
  return {
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    textColor: 'text-blue-800 dark:text-blue-200',
    borderColor: 'border-blue-300 dark:border-blue-700',
    icon: UnlockIcon,
    label: 'Open',
    ariaLabel: 'PAC is open',
  };
}

/**
 * Get size classes based on size variant.
 */
function getSizeClasses(size: 'sm' | 'md' | 'lg') {
  switch (size) {
    case 'sm':
      return {
        container: 'px-2 py-0.5 text-xs',
        icon: 'w-3 h-3',
        gap: 'gap-1',
      };
    case 'lg':
      return {
        container: 'px-4 py-2 text-base',
        icon: 'w-5 h-5',
        gap: 'gap-2',
      };
    case 'md':
    default:
      return {
        container: 'px-3 py-1 text-sm',
        icon: 'w-4 h-4',
        gap: 'gap-1.5',
      };
  }
}

/**
 * PositiveClosureBadge component.
 *
 * Displays closure status with appropriate visual indicator.
 * Only shows green for POSITIVE_CLOSURE (no_green_without_positive_closure rule).
 */
export function PositiveClosureBadge({
  closureType,
  state,
  size = 'md',
  showLabel = true,
  className = '',
}: PositiveClosureBadgeProps) {
  const config = getBadgeConfig(closureType, state);
  const sizeClasses = getSizeClasses(size);
  const IconComponent = config.icon;

  return (
    <span
      className={`
        inline-flex items-center ${sizeClasses.gap} ${sizeClasses.container}
        ${config.bgColor} ${config.textColor} ${config.borderColor}
        border rounded-full font-medium
        ${className}
      `}
      role="status"
      aria-label={config.ariaLabel}
    >
      <IconComponent className={sizeClasses.icon} />
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

/**
 * Minimal closure indicator (icon only).
 */
export function ClosureIndicator({
  closureType,
  state,
  className = '',
}: {
  closureType: ClosureType;
  state?: PACLifecycleState;
  className?: string;
}) {
  const config = getBadgeConfig(closureType, state);
  const IconComponent = config.icon;

  return (
    <span
      className={`inline-flex ${config.textColor} ${className}`}
      role="status"
      aria-label={config.ariaLabel}
    >
      <IconComponent className="w-4 h-4" />
    </span>
  );
}

export default PositiveClosureBadge;
