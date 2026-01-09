// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P21-FRICTION — SafeButton Component
// Lane 9 (UX / GID-SONNY) Implementation
// Governance Tier: LAW
// Invariant: SPEED_IS_NEGLIGENCE | VISUAL_COUNTDOWN | CONFIRM_ON_CRITICAL
// ═══════════════════════════════════════════════════════════════════════════════
/**
 * SafeButton: A friction-enforced button component
 * 
 * This button enforces cognitive friction before allowing critical actions.
 * It includes:
 * - Visual countdown timer
 * - Progress indicator
 * - Optional confirmation step
 * - Governance-tier-aware dwell times
 * 
 * Usage:
 * ```tsx
 * <SafeButton
 *   tier="LAW"
 *   onClick={() => terminateSession()}
 *   variant="danger"
 *   requireConfirm
 * >
 *   KILL SESSION
 * </SafeButton>
 * ```
 */

import React, { useState, useCallback } from 'react';
import { useDwellTimer, GovernanceTier, DWELL_TIMES } from '../hooks/useDwellTimer';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'warning' | 'success';

export interface SafeButtonProps {
  /** Button content */
  children: React.ReactNode;
  /** Governance tier (determines dwell time) */
  tier: GovernanceTier;
  /** Click handler (called after dwell satisfied + optional confirm) */
  onClick: () => void | Promise<void>;
  /** Button variant for styling */
  variant?: ButtonVariant;
  /** Require a confirmation click */
  requireConfirm?: boolean;
  /** Confirmation timeout in ms (default: 3000) */
  confirmTimeout?: number;
  /** Custom dwell time override (ms) */
  customDwellMs?: number;
  /** Additional CSS classes */
  className?: string;
  /** Disabled state (independent of dwell timer) */
  disabled?: boolean;
  /** Show the dwell timer countdown */
  showCountdown?: boolean;
  /** Show progress bar */
  showProgress?: boolean;
  /** Icon to display */
  icon?: React.ReactNode;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

// ═══════════════════════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════════════════════

const variantStyles: Record<ButtonVariant, { base: string; hover: string; disabled: string }> = {
  primary: {
    base: 'bg-blue-600 text-white border-blue-700',
    hover: 'hover:bg-blue-700',
    disabled: 'bg-blue-900/50 text-blue-400/50 border-blue-800/50'
  },
  secondary: {
    base: 'bg-gray-700 text-gray-100 border-gray-600',
    hover: 'hover:bg-gray-600',
    disabled: 'bg-gray-800/50 text-gray-500 border-gray-700/50'
  },
  danger: {
    base: 'bg-red-600 text-white border-red-700',
    hover: 'hover:bg-red-700',
    disabled: 'bg-red-900/50 text-red-400/50 border-red-800/50'
  },
  warning: {
    base: 'bg-yellow-600 text-black border-yellow-700',
    hover: 'hover:bg-yellow-700',
    disabled: 'bg-yellow-900/50 text-yellow-400/50 border-yellow-800/50'
  },
  success: {
    base: 'bg-green-600 text-white border-green-700',
    hover: 'hover:bg-green-700',
    disabled: 'bg-green-900/50 text-green-400/50 border-green-800/50'
  }
};

const sizeStyles: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'px-2 py-1 text-xs',
  md: 'px-3 py-1.5 text-sm',
  lg: 'px-4 py-2 text-base'
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const SafeButton: React.FC<SafeButtonProps> = ({
  children,
  tier,
  onClick,
  variant = 'primary',
  requireConfirm = false,
  confirmTimeout = 3000,
  customDwellMs,
  className = '',
  disabled = false,
  showCountdown = true,
  showProgress = true,
  icon,
  size = 'md'
}) => {
  // State
  const [confirming, setConfirming] = useState(false);
  const [executing, setExecuting] = useState(false);

  // Dwell timer
  const dwell = useDwellTimer({
    tier,
    customDwellMs,
    onSatisfied: () => {
      // Optional: Play a subtle sound or haptic feedback
    }
  });

  // Handle confirmation timeout
  const startConfirmTimeout = useCallback(() => {
    setConfirming(true);
    setTimeout(() => {
      setConfirming(false);
    }, confirmTimeout);
  }, [confirmTimeout]);

  // Handle click
  const handleClick = useCallback(async () => {
    // Ignore if disabled, dwell not satisfied, or already executing
    if (disabled || !dwell.satisfied || executing) return;

    // If confirmation required and not confirming, start confirmation
    if (requireConfirm && !confirming) {
      startConfirmTimeout();
      return;
    }

    // Execute action
    try {
      setExecuting(true);
      await onClick();
    } finally {
      setExecuting(false);
      setConfirming(false);
    }
  }, [disabled, dwell.satisfied, executing, requireConfirm, confirming, startConfirmTimeout, onClick]);

  // Compute button state
  const isDisabled = disabled || !dwell.satisfied || executing;
  const styles = variantStyles[variant];

  // Button content
  const renderContent = () => {
    if (executing) {
      return (
        <span className="flex items-center gap-2">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Executing...
        </span>
      );
    }

    if (confirming) {
      return (
        <span className="flex items-center gap-2 animate-pulse">
          ⚠️ Click again to confirm
        </span>
      );
    }

    if (!dwell.satisfied && showCountdown) {
      return (
        <span className="flex items-center gap-2">
          {icon}
          <span className="opacity-50">{children}</span>
          <span className="font-mono text-xs bg-black/30 px-1.5 py-0.5 rounded">
            {dwell.remainingDisplay}
          </span>
        </span>
      );
    }

    return (
      <span className="flex items-center gap-2">
        {icon}
        {children}
      </span>
    );
  };

  return (
    <div className="relative inline-block">
      {/* Progress bar (underneath button) */}
      {showProgress && !dwell.satisfied && (
        <div className="absolute inset-0 overflow-hidden rounded">
          <div
            className="absolute bottom-0 left-0 h-1 bg-white/30 transition-all duration-100"
            style={{ width: `${dwell.progress}%` }}
          />
        </div>
      )}

      {/* Button */}
      <button
        onClick={handleClick}
        disabled={isDisabled}
        className={`
          relative font-semibold rounded border transition-all duration-200
          ${sizeStyles[size]}
          ${isDisabled ? styles.disabled : `${styles.base} ${styles.hover}`}
          ${confirming ? 'ring-2 ring-white ring-opacity-50 animate-pulse' : ''}
          ${className}
        `}
        title={
          !dwell.satisfied 
            ? `Please wait ${dwell.remainingDisplay} (${tier} tier requires ${DWELL_TIMES[tier] / 1000}s review)`
            : undefined
        }
      >
        {renderContent()}
      </button>

      {/* Tier badge */}
      {!dwell.satisfied && (
        <div className="absolute -top-2 -right-2 text-[10px] px-1.5 py-0.5 rounded-full bg-gray-800 text-gray-400 border border-gray-700">
          {tier}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SPECIALIZED VARIANTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * KillButton: A red danger button with LAW-tier dwell time and confirmation.
 * Use for session termination, emergency stops, etc.
 */
export const KillButton: React.FC<Omit<SafeButtonProps, 'tier' | 'variant' | 'requireConfirm'>> = (props) => (
  <SafeButton
    tier="LAW"
    variant="danger"
    requireConfirm
    icon={<span>🛑</span>}
    {...props}
  />
);

/**
 * ApproveButton: A green success button with POLICY-tier dwell time.
 * Use for approvals, confirmations, etc.
 */
export const ApproveButton: React.FC<Omit<SafeButtonProps, 'tier' | 'variant'>> = (props) => (
  <SafeButton
    tier="POLICY"
    variant="success"
    icon={<span>✓</span>}
    {...props}
  />
);

/**
 * DeployButton: A warning button with LAW-tier dwell time and confirmation.
 * Use for deployments, releases, etc.
 */
export const DeployButton: React.FC<Omit<SafeButtonProps, 'tier' | 'variant' | 'requireConfirm'>> = (props) => (
  <SafeButton
    tier="LAW"
    variant="warning"
    requireConfirm
    icon={<span>🚀</span>}
    {...props}
  />
);

export default SafeButton;
