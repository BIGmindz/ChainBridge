/**
 * GovernanceShield — PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 *
 * Visual shield indicator component that mirrors terminal governance semantics.
 * Provides 1:1 parity with terminal glyph output for situational awareness.
 *
 * Shield States:
 * - 🟢 GREEN: System healthy, no blocks, governance compliant
 * - 🟡 YELLOW: Corrections in progress, pending actions
 * - 🔴 RED: System blocked, violations active, requires attention
 *
 * GUARANTEES:
 * - read_only: No business logic, display only
 * - terminal_parity: States map exactly to terminal glyphs
 * - fail_closed: Unknown states render as RED (blocked)
 *
 * @see PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 */

import { useMemo } from 'react';

import type { GovernanceSummary } from '../../types/governanceLedger';

/**
 * Shield status — canonical states matching terminal output.
 */
export type ShieldStatus = 'GREEN' | 'YELLOW' | 'RED';

/**
 * Derive shield status from governance summary.
 * This logic mirrors terminal glyph semantics exactly.
 */
export function deriveShieldStatus(summary: GovernanceSummary | null): ShieldStatus {
  // FAIL_CLOSED: No data = RED
  if (!summary) {
    return 'RED';
  }

  // RED: Any blocked PACs or system unhealthy
  if (summary.blocked_pacs > 0 || !summary.system_healthy) {
    return 'RED';
  }

  // YELLOW: Correction cycles in progress or pending ratifications
  if (summary.correction_cycles > 0 || summary.pending_ratifications > 0) {
    return 'YELLOW';
  }

  // GREEN: All clear
  return 'GREEN';
}

/**
 * Shield status metadata for rendering.
 */
interface ShieldMeta {
  status: ShieldStatus;
  glyph: string;
  label: string;
  description: string;
  colorClasses: {
    bg: string;
    border: string;
    text: string;
    glow: string;
  };
}

/**
 * Get metadata for shield status.
 */
function getShieldMeta(status: ShieldStatus): ShieldMeta {
  switch (status) {
    case 'GREEN':
      return {
        status: 'GREEN',
        glyph: '🟢',
        label: 'COMPLIANT',
        description: 'System healthy, governance compliant',
        colorClasses: {
          bg: 'bg-green-500',
          border: 'border-green-500',
          text: 'text-green-600 dark:text-green-400',
          glow: 'shadow-green-500/50',
        },
      };
    case 'YELLOW':
      return {
        status: 'YELLOW',
        glyph: '🟡',
        label: 'IN PROGRESS',
        description: 'Corrections or ratifications pending',
        colorClasses: {
          bg: 'bg-amber-500',
          border: 'border-amber-500',
          text: 'text-amber-600 dark:text-amber-400',
          glow: 'shadow-amber-500/50',
        },
      };
    case 'RED':
    default:
      return {
        status: 'RED',
        glyph: '🔴',
        label: 'BLOCKED',
        description: 'Action required, system blocked',
        colorClasses: {
          bg: 'bg-red-500',
          border: 'border-red-500',
          text: 'text-red-600 dark:text-red-400',
          glow: 'shadow-red-500/50',
        },
      };
  }
}

export interface GovernanceShieldProps {
  /** Governance summary data */
  summary: GovernanceSummary | null;
  /** Override status (for testing/demo) */
  overrideStatus?: ShieldStatus;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show label text */
  showLabel?: boolean;
  /** Show glyph */
  showGlyph?: boolean;
  /** Animate pulse effect */
  animate?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * GovernanceShield — Primary shield indicator component.
 */
export function GovernanceShield({
  summary,
  overrideStatus,
  size = 'md',
  showLabel = true,
  showGlyph = true,
  animate = true,
  className = '',
}: GovernanceShieldProps) {
  const status = overrideStatus ?? deriveShieldStatus(summary);
  const meta = useMemo(() => getShieldMeta(status), [status]);

  const sizeClasses = {
    sm: {
      shield: 'w-8 h-8',
      glyph: 'text-sm',
      label: 'text-xs',
    },
    md: {
      shield: 'w-12 h-12',
      glyph: 'text-xl',
      label: 'text-sm',
    },
    lg: {
      shield: 'w-16 h-16',
      glyph: 'text-3xl',
      label: 'text-base',
    },
  };

  const sizes = sizeClasses[size];

  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      role="status"
      aria-label={`Governance status: ${meta.label}`}
      data-testid="governance-shield"
      data-status={status}
    >
      {/* Shield indicator */}
      <div
        className={`
          ${sizes.shield}
          rounded-full
          ${meta.colorClasses.bg}
          ${animate && status !== 'GREEN' ? 'animate-pulse' : ''}
          shadow-lg ${meta.colorClasses.glow}
          flex items-center justify-center
        `}
        data-testid="governance-shield-indicator"
      >
        {showGlyph && (
          <span className={sizes.glyph} role="img" aria-hidden="true">
            {meta.glyph}
          </span>
        )}
      </div>

      {/* Label */}
      {showLabel && (
        <div className="flex flex-col">
          <span
            className={`font-bold uppercase tracking-wider ${sizes.label} ${meta.colorClasses.text}`}
            data-testid="governance-shield-label"
          >
            {meta.label}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {meta.description}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * GovernanceShieldBadge — Compact badge variant for headers/navbars.
 */
export function GovernanceShieldBadge({
  summary,
  overrideStatus,
  className = '',
}: Pick<GovernanceShieldProps, 'summary' | 'overrideStatus' | 'className'>) {
  const status = overrideStatus ?? deriveShieldStatus(summary);
  const meta = getShieldMeta(status);

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full
        ${meta.colorClasses.bg} bg-opacity-20
        border ${meta.colorClasses.border} border-opacity-50
        ${meta.colorClasses.text} font-semibold text-xs uppercase tracking-wider
        ${className}
      `}
      role="status"
      aria-label={`Governance: ${meta.label}`}
      data-testid="governance-shield-badge"
      data-status={status}
    >
      <span role="img" aria-hidden="true">{meta.glyph}</span>
      {meta.label}
    </span>
  );
}

/**
 * GovernanceShieldIcon — Minimal icon-only variant.
 */
export function GovernanceShieldIcon({
  summary,
  overrideStatus,
  size = 'md',
  animate = true,
  className = '',
}: Pick<GovernanceShieldProps, 'summary' | 'overrideStatus' | 'size' | 'animate' | 'className'>) {
  const status = overrideStatus ?? deriveShieldStatus(summary);
  const meta = getShieldMeta(status);

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <span
      className={`
        inline-block rounded-full
        ${sizeClasses[size]}
        ${meta.colorClasses.bg}
        ${animate && status !== 'GREEN' ? 'animate-pulse' : ''}
        ${className}
      `}
      role="status"
      aria-label={`Governance: ${meta.label}`}
      data-testid="governance-shield-icon"
      data-status={status}
    />
  );
}

export default GovernanceShield;
