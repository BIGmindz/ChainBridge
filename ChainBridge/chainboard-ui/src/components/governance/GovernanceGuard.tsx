/**
 * GovernanceGuard — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * HOC and component for governance-aware action disabling.
 * Wraps UI actions to enforce governance state constraints.
 *
 * BEHAVIOR:
 * - When BLOCKED: All wrapped actions disabled, tooltip shows reason
 * - When CORRECTION_REQUIRED: Only RESUBMIT_PAC action allowed
 * - When RATIFIED: Only UNBLOCK_SYSTEM action allowed
 * - When REJECTED: Only ARCHIVE action allowed
 * - When OPEN/UNBLOCKED: All actions enabled
 *
 * CONSTRAINTS:
 * - NO client-side state bypass
 * - Actions MUST check governance state before execution
 * - Disabled actions show clear reason
 * - No optimistic UI — always reflect backend state
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import { Lock, AlertTriangle } from 'lucide-react';
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

import { useGovernanceState, useActionAllowed } from '../../hooks/useGovernanceState';
import type { GovernanceUIState } from '../../types/governanceState';
import { classNames } from '../../utils/classNames';

/**
 * Get disabled reason for a governance state.
 */
function getDisabledReason(state: GovernanceUIState): string {
  switch (state) {
    case 'BLOCKED':
      return 'System is blocked by governance. All actions disabled.';
    case 'CORRECTION_REQUIRED':
      return 'PAC correction required. Resubmit to proceed.';
    case 'RESUBMITTED':
      return 'PAC resubmitted. Awaiting evaluation.';
    case 'RATIFIED':
      return 'Awaiting system unblock after ratification.';
    case 'REJECTED':
      return 'PAC rejected. Archive only.';
    default:
      return '';
  }
}

/**
 * GovernanceGuard Props.
 */
export interface GovernanceGuardProps {
  /** Child content to wrap */
  children: ReactNode;
  /** Action type for permission check (optional) */
  actionType?: string;
  /** Show disabled reason on hover */
  showReason?: boolean;
  /** Additional className when disabled */
  disabledClassName?: string;
}

/**
 * GovernanceGuard Component.
 *
 * Wraps children and disables interaction when governance blocks actions.
 */
export function GovernanceGuard({
  children,
  actionType,
  showReason = true,
  disabledClassName = 'opacity-50 cursor-not-allowed pointer-events-none',
}: GovernanceGuardProps) {
  const { state, actionsEnabled, allowedAction } = useGovernanceState();

  // Check if this specific action is allowed
  const isAllowed = actionsEnabled || (actionType && allowedAction === actionType);
  const reason = getDisabledReason(state);

  if (isAllowed) {
    return <>{children}</>;
  }

  return (
    <div
      className={classNames('relative', disabledClassName)}
      title={showReason ? reason : undefined}
    >
      {children}
      {/* Visual overlay indicator */}
      <div className="absolute inset-0 flex items-center justify-center bg-slate-900/30 rounded">
        <Lock className="h-4 w-4 text-slate-400" />
      </div>
    </div>
  );
}

/**
 * GovernanceButton Props.
 */
export interface GovernanceButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Action type for permission check */
  actionType?: string;
  /** Variant style */
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  /** Size */
  size?: 'sm' | 'md' | 'lg';
  /** Loading state */
  isLoading?: boolean;
  /** Show lock icon when disabled by governance */
  showLockIcon?: boolean;
}

/**
 * Button component with built-in governance enforcement.
 */
export const GovernanceButton = forwardRef<HTMLButtonElement, GovernanceButtonProps>(
  function GovernanceButton(
    {
      children,
      actionType,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      showLockIcon = true,
      disabled,
      className,
      onClick,
      ...props
    },
    ref
  ) {
    const { state, actionsEnabled, allowedAction, isBlocked } = useGovernanceState();

    // Check if this action is allowed
    const isAllowed = actionsEnabled || (actionType && allowedAction === actionType);
    const isGovernanceDisabled = !isAllowed;
    const isDisabled = disabled || isGovernanceDisabled || isLoading;
    const reason = getDisabledReason(state);

    // Style variants
    const variantStyles = {
      primary: 'bg-sky-600 hover:bg-sky-500 text-white border-sky-500',
      secondary: 'bg-slate-700 hover:bg-slate-600 text-slate-200 border-slate-600',
      danger: 'bg-rose-600 hover:bg-rose-500 text-white border-rose-500',
      ghost: 'bg-transparent hover:bg-slate-800 text-slate-300 border-transparent',
    };

    const sizeStyles = {
      sm: 'px-2 py-1 text-xs',
      md: 'px-3 py-1.5 text-sm',
      lg: 'px-4 py-2 text-base',
    };

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      // Double-check governance state before allowing action
      if (isGovernanceDisabled) {
        e.preventDefault();
        console.warn(`[GovernanceButton] Action blocked by governance: ${state}`);
        return;
      }
      onClick?.(e);
    };

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        onClick={handleClick}
        title={isGovernanceDisabled ? reason : undefined}
        className={classNames(
          'inline-flex items-center justify-center gap-2 rounded-lg border font-medium transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-sky-500/40',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantStyles[variant],
          sizeStyles[size],
          isGovernanceDisabled && 'border-slate-600 bg-slate-800 text-slate-500',
          className
        )}
        {...props}
      >
        {isLoading ? (
          <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : isGovernanceDisabled && showLockIcon ? (
          <Lock className="h-3.5 w-3.5" />
        ) : null}
        {children}
      </button>
    );
  }
);

/**
 * GovernanceBlockedOverlay Props.
 */
export interface GovernanceBlockedOverlayProps {
  /** Additional className */
  className?: string;
}

/**
 * Full-screen overlay when system is blocked.
 * Prevents any interaction until unblocked.
 */
export function GovernanceBlockedOverlay({ className }: GovernanceBlockedOverlayProps) {
  const { isBlocked, state, context } = useGovernanceState();

  if (!isBlocked) {
    return null;
  }

  const primaryBlock = context?.active_blocks[0];

  return (
    <div className={classNames(
      'fixed inset-0 z-50 flex items-center justify-center bg-slate-950/90 backdrop-blur-sm',
      className
    )}>
      <div className="max-w-lg p-8 rounded-xl border border-rose-500/40 bg-rose-500/10 text-center space-y-4">
        <div className="flex justify-center">
          <div className="p-4 rounded-full bg-rose-500/20">
            <AlertTriangle className="h-12 w-12 text-rose-400" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-rose-300">System Blocked</h2>
        <p className="text-slate-300">
          Governance has blocked system operations. All actions are disabled.
        </p>
        {primaryBlock && (
          <div className="mt-4 p-4 rounded-lg bg-slate-900/50 border border-slate-700/50 text-left space-y-2">
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono text-rose-300 bg-rose-500/20 px-1.5 py-0.5 rounded">
                {primaryBlock.rule_code}
              </code>
              <span className="text-xs text-slate-500">
                by {primaryBlock.triggered_by_gid}
              </span>
            </div>
            <p className="text-sm text-slate-300">{primaryBlock.reason}</p>
            <p className="text-xs text-slate-500">
              Correlation: {primaryBlock.correlation_id}
            </p>
          </div>
        )}
        <p className="text-xs text-slate-500 pt-4">
          Contact your Guardian or Administrator to resolve this block.
        </p>
      </div>
    </div>
  );
}

/**
 * Hook for wrapping action handlers with governance checks.
 */
export function useGovernanceAction<T extends (...args: unknown[]) => unknown>(
  handler: T,
  actionType?: string
): T {
  const isAllowed = useActionAllowed(actionType ?? '');
  const { state } = useGovernanceState();

  return ((...args: unknown[]) => {
    if (!isAllowed && !actionType) {
      console.warn(`[useGovernanceAction] Action blocked by governance: ${state}`);
      return;
    }
    return handler(...args);
  }) as T;
}
