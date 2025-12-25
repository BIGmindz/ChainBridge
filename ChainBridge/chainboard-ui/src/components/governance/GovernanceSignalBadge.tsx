/**
 * GovernanceSignalBadge — PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 *
 * UI component for rendering governance signal status.
 * Maps 1:1 to terminal PASS/WARN/FAIL/SKIP output.
 *
 * DESIGN PRINCIPLES:
 * - Uses governance colors (NOT agent colors)
 * - Shape-based visual language (shields, checkmarks)
 * - Terminal-safe glyphs embedded
 * - Accessible with ARIA labels
 *
 * @see PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 */

import { useMemo } from 'react';

import {
  type SignalStatus,
  type SignalSeverity,
  getSignalVisualConfig,
  getSeverityVisualConfig,
  TERMINAL_GLYPHS,
} from './GovernanceVisualLanguage';

// ============================================================================
// SIGNAL STATUS BADGE
// ============================================================================

export interface GovernanceSignalBadgeProps {
  /** Signal status */
  status: SignalStatus;
  /** Optional severity */
  severity?: SignalSeverity;
  /** Show glyph */
  showGlyph?: boolean;
  /** Show label */
  showLabel?: boolean;
  /** Size variant */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

/**
 * GovernanceSignalBadge — Inline status badge.
 */
export function GovernanceSignalBadge({
  status,
  severity: _severity,
  showGlyph = true,
  showLabel = true,
  size = 'md',
  className = '',
}: GovernanceSignalBadgeProps) {
  // _severity reserved for future severity-aware badge variants
  const config = useMemo(() => getSignalVisualConfig(status), [status]);

  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-xs gap-0.5',
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
    lg: 'px-3 py-1.5 text-base gap-2',
  };

  return (
    <span
      className={`
        inline-flex items-center font-semibold rounded-md
        ${config.colors.bgLight}
        border ${config.colors.border}
        ${config.colors.textBold}
        ${sizeClasses[size]}
        ${className}
      `}
      role="status"
      aria-label={config.ariaLabel}
      data-testid="governance-signal-badge"
      data-status={status}
    >
      {showGlyph && (
        <span aria-hidden="true" className="font-mono">
          {config.glyph}
        </span>
      )}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

// ============================================================================
// SEVERITY BADGE
// ============================================================================

export interface SeverityBadgeProps {
  /** Severity level */
  severity: SignalSeverity;
  /** Show glyph */
  showGlyph?: boolean;
  /** Size variant */
  size?: 'xs' | 'sm' | 'md';
  /** Additional CSS classes */
  className?: string;
}

/**
 * SeverityBadge — Inline severity indicator.
 */
export function SeverityBadge({
  severity,
  showGlyph = true,
  size = 'sm',
  className = '',
}: SeverityBadgeProps) {
  const config = useMemo(() => getSeverityVisualConfig(severity), [severity]);

  const sizeClasses = {
    xs: 'px-1 py-0.5 text-xs gap-0.5',
    sm: 'px-1.5 py-0.5 text-xs gap-1',
    md: 'px-2 py-0.5 text-sm gap-1',
  };

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded
        ${config.colors.bgLight}
        ${config.colors.text}
        ${sizeClasses[size]}
        ${className}
      `}
      role="status"
      aria-label={`Severity: ${severity}`}
      data-testid="severity-badge"
      data-severity={severity}
    >
      {showGlyph && (
        <span aria-hidden="true" className="font-mono">
          {config.glyph}
        </span>
      )}
      <span>{config.label}</span>
    </span>
  );
}

// ============================================================================
// SIGNAL ROW — Terminal-style output
// ============================================================================

export interface GovernanceSignalRowProps {
  /** Signal status */
  status: SignalStatus;
  /** Severity level */
  severity: SignalSeverity;
  /** Signal code (e.g., PAG_001) */
  code: string;
  /** Title/description */
  title: string;
  /** Optional expanded description */
  description?: string;
  /** Optional evidence */
  evidence?: string;
  /** Optional resolution */
  resolution?: string;
  /** Expanded state */
  expanded?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * GovernanceSignalRow — Terminal-parity signal display row.
 */
export function GovernanceSignalRow({
  status,
  severity,
  code,
  title,
  description,
  evidence,
  resolution,
  expanded = false,
  onClick,
  className = '',
}: GovernanceSignalRowProps) {
  const config = useMemo(() => getSignalVisualConfig(status), [status]);

  return (
    <div
      className={`
        rounded-lg border-2 overflow-hidden
        ${config.colors.border}
        ${className}
      `}
      role="article"
      aria-label={`${status}: ${title}`}
      data-testid="governance-signal-row"
      data-status={status}
    >
      {/* Header — matches terminal box format */}
      <div
        className={`
          flex items-center justify-between px-4 py-2
          ${config.colors.bgLight}
          cursor-pointer
        `}
        onClick={onClick}
        role={onClick ? 'button' : undefined}
        tabIndex={onClick ? 0 : undefined}
      >
        <div className="flex items-center gap-3">
          {/* Status glyph */}
          <span
            className={`
              w-8 h-8 flex items-center justify-center rounded-lg
              ${config.colors.bg} text-white text-lg font-bold
            `}
            aria-hidden="true"
          >
            {config.glyph}
          </span>

          {/* Status + Severity + Code */}
          <div className="flex items-center gap-2">
            <GovernanceSignalBadge status={status} size="sm" />
            <SeverityBadge severity={severity} size="xs" />
            <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">
              {code}
            </code>
          </div>
        </div>

        {/* Expand indicator */}
        {(description || evidence || resolution) && (
          <span className="text-gray-400" aria-hidden="true">
            {expanded ? '▼' : '▶'}
          </span>
        )}
      </div>

      {/* Title */}
      <div className={`px-4 py-2 font-medium ${config.colors.text}`}>
        {title}
      </div>

      {/* Expanded content */}
      {expanded && (description || evidence || resolution) && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
          {description && (
            <div>
              <span className="text-xs font-semibold text-gray-500 uppercase">
                Description
              </span>
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                {description}
              </p>
            </div>
          )}

          {evidence && (
            <div>
              <span className="text-xs font-semibold text-gray-500 uppercase">
                Evidence
              </span>
              <pre className="text-xs font-mono bg-gray-100 dark:bg-gray-800 rounded p-2 mt-1 overflow-x-auto">
                {evidence}
              </pre>
            </div>
          )}

          {resolution && (
            <div>
              <span className="text-xs font-semibold text-gray-500 uppercase">
                Resolution
              </span>
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                {resolution}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// VALIDATION SUMMARY — Terminal-style summary
// ============================================================================

export interface ValidationSummaryProps {
  /** Count of PASS signals */
  passCount: number;
  /** Count of WARN signals */
  warnCount: number;
  /** Count of FAIL signals */
  failCount: number;
  /** Count of SKIP signals */
  skipCount: number;
  /** Overall status */
  status: 'VALID' | 'INVALID' | 'PENDING';
  /** Additional CSS classes */
  className?: string;
}

/**
 * ValidationSummary — Terminal-parity summary display.
 */
export function ValidationSummary({
  passCount,
  warnCount,
  failCount,
  skipCount,
  status,
  className = '',
}: ValidationSummaryProps) {
  const statusConfig = useMemo(() => {
    switch (status) {
      case 'VALID':
        return {
          glyph: TERMINAL_GLYPHS.PASS,
          label: 'VALID',
          colorClasses: 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-500 text-emerald-700 dark:text-emerald-300',
        };
      case 'INVALID':
        return {
          glyph: TERMINAL_GLYPHS.FAIL,
          label: 'INVALID',
          colorClasses: 'bg-rose-100 dark:bg-rose-900/30 border-rose-500 text-rose-700 dark:text-rose-300',
        };
      case 'PENDING':
        return {
          glyph: TERMINAL_GLYPHS.SKIP,
          label: 'PENDING',
          colorClasses: 'bg-sky-100 dark:bg-sky-900/30 border-sky-500 text-sky-700 dark:text-sky-300',
        };
    }
  }, [status]);

  return (
    <div
      className={`rounded-lg border-2 ${statusConfig.colorClasses} p-4 ${className}`}
      role="status"
      aria-label={`Validation result: ${status}`}
      data-testid="validation-summary"
      data-status={status}
    >
      {/* Summary counts */}
      <div className="flex flex-wrap items-center gap-4 mb-3">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-rose-600 dark:text-rose-400">
            {failCount}
          </span>
          <span className="text-sm text-gray-600 dark:text-gray-400">FAIL</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-orange-600 dark:text-orange-400">
            {warnCount}
          </span>
          <span className="text-sm text-gray-600 dark:text-gray-400">WARN</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-emerald-600 dark:text-emerald-400">
            {passCount}
          </span>
          <span className="text-sm text-gray-600 dark:text-gray-400">PASS</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-slate-500">
            {skipCount}
          </span>
          <span className="text-sm text-gray-600 dark:text-gray-400">SKIP</span>
        </div>
      </div>

      {/* Status line */}
      <div className="flex items-center gap-2 font-bold text-lg">
        <span>STATUS:</span>
        <span className="font-mono">{statusConfig.glyph}</span>
        <span>{statusConfig.label}</span>
      </div>
    </div>
  );
}

// ============================================================================
// GATE INDICATOR — Visual gate state
// ============================================================================

export interface GateIndicatorProps {
  /** Gate name */
  gateName: string;
  /** Gate ID */
  gateId: string;
  /** Gate state */
  state: 'PASS' | 'FAIL' | 'PENDING' | 'SKIPPED';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

/**
 * GateIndicator — Visual gate pass/fail indicator.
 */
export function GateIndicator({
  gateName,
  gateId,
  state,
  size = 'md',
  className = '',
}: GateIndicatorProps) {
  const stateConfig = useMemo(() => {
    switch (state) {
      case 'PASS':
        return {
          glyph: TERMINAL_GLYPHS.GATE_OPEN,
          label: 'OPEN',
          colors: 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-500 text-emerald-700 dark:text-emerald-300',
        };
      case 'FAIL':
        return {
          glyph: TERMINAL_GLYPHS.GATE_CLOSED,
          label: 'CLOSED',
          colors: 'bg-rose-100 dark:bg-rose-900/30 border-rose-500 text-rose-700 dark:text-rose-300',
        };
      case 'PENDING':
        return {
          glyph: TERMINAL_GLYPHS.GATE_PENDING,
          label: 'PENDING',
          colors: 'bg-sky-100 dark:bg-sky-900/30 border-sky-500 text-sky-700 dark:text-sky-300',
        };
      case 'SKIPPED':
        return {
          glyph: TERMINAL_GLYPHS.SKIP,
          label: 'SKIPPED',
          colors: 'bg-slate-100 dark:bg-slate-800/50 border-slate-400 text-slate-600 dark:text-slate-400',
        };
    }
  }, [state]);

  const sizeClasses = {
    sm: 'p-2 text-sm',
    md: 'p-3',
    lg: 'p-4 text-lg',
  };

  return (
    <div
      className={`
        rounded-lg border-2 ${stateConfig.colors}
        ${sizeClasses[size]}
        ${className}
      `}
      role="status"
      aria-label={`${gateName}: ${state}`}
      data-testid="gate-indicator"
      data-state={state}
    >
      <div className="flex items-center gap-2">
        <span className="text-xl" aria-hidden="true">
          {stateConfig.glyph}
        </span>
        <div>
          <div className="font-semibold">{gateName}</div>
          <div className="text-xs opacity-75">{gateId}</div>
        </div>
        <span className="ml-auto font-bold">{stateConfig.label}</span>
      </div>
    </div>
  );
}

export default GovernanceSignalBadge;
