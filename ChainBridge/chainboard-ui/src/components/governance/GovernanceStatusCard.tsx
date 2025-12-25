/**
 * GovernanceStatusCard — PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 *
 * Status card component that mirrors terminal glyph semantics.
 * Provides comprehensive governance state visualization with terminal parity.
 *
 * Terminal Glyph Mappings:
 * - 🟩🟩🟩 = GOLD_STANDARD_COMPLIANT (all green)
 * - 🟡🟡🟡 = CORRECTION_IN_PROGRESS (corrections pending)
 * - 🔴🔴🔴 = BLOCKED / VIOLATION (action required)
 * - ⬜⬜⬜ = PENDING (awaiting evaluation)
 *
 * GUARANTEES:
 * - read_only: No business logic, display only
 * - terminal_parity: Glyphs map 1:1 to terminal output
 * - situational_awareness: Visual hierarchy for quick comprehension
 *
 * @see PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 */

import { useMemo } from 'react';

import type { GovernanceSummary } from '../../types/governanceLedger';

import { GovernanceShield } from './GovernanceShield';
import { LastEvaluatedBadge, LastEvaluatedCompact } from './LastEvaluatedBadge';

/**
 * Terminal glyph pattern — canonical representation.
 */
export type TerminalGlyphPattern =
  | 'GOLD_STANDARD_COMPLIANT'
  | 'CORRECTION_IN_PROGRESS'
  | 'BLOCKED'
  | 'PENDING';

/**
 * Derive terminal glyph pattern from summary.
 */
export function deriveGlyphPattern(summary: GovernanceSummary | null): TerminalGlyphPattern {
  if (!summary) {
    return 'PENDING';
  }

  if (summary.blocked_pacs > 0 || !summary.system_healthy) {
    return 'BLOCKED';
  }

  if (summary.correction_cycles > 0 || summary.pending_ratifications > 0) {
    return 'CORRECTION_IN_PROGRESS';
  }

  return 'GOLD_STANDARD_COMPLIANT';
}

/**
 * Glyph pattern metadata.
 */
interface GlyphPatternMeta {
  pattern: TerminalGlyphPattern;
  glyphs: string;
  terminalOutput: string;
  label: string;
  description: string;
  colorClasses: {
    bg: string;
    border: string;
    text: string;
    glyphBg: string;
  };
}

/**
 * Get metadata for glyph pattern.
 */
function getGlyphPatternMeta(pattern: TerminalGlyphPattern): GlyphPatternMeta {
  switch (pattern) {
    case 'GOLD_STANDARD_COMPLIANT':
      return {
        pattern: 'GOLD_STANDARD_COMPLIANT',
        glyphs: '🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩',
        terminalOutput: 'STATUS: 🟩 GOLD_STANDARD_COMPLIANT',
        label: 'GOLD STANDARD COMPLIANT',
        description: 'All governance checks passed',
        colorClasses: {
          bg: 'bg-green-50 dark:bg-green-900/20',
          border: 'border-green-300 dark:border-green-700',
          text: 'text-green-700 dark:text-green-300',
          glyphBg: 'bg-green-100 dark:bg-green-900/40',
        },
      };
    case 'CORRECTION_IN_PROGRESS':
      return {
        pattern: 'CORRECTION_IN_PROGRESS',
        glyphs: '🟡🟡🟡🟡🟡🟡🟡🟡🟡🟡',
        terminalOutput: 'STATUS: 🟡 CORRECTION_IN_PROGRESS',
        label: 'CORRECTION IN PROGRESS',
        description: 'Corrections or ratifications pending',
        colorClasses: {
          bg: 'bg-amber-50 dark:bg-amber-900/20',
          border: 'border-amber-300 dark:border-amber-700',
          text: 'text-amber-700 dark:text-amber-300',
          glyphBg: 'bg-amber-100 dark:bg-amber-900/40',
        },
      };
    case 'BLOCKED':
      return {
        pattern: 'BLOCKED',
        glyphs: '🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴',
        terminalOutput: 'STATUS: 🔴 BLOCKED — ACTION REQUIRED',
        label: 'BLOCKED',
        description: 'Action required, governance violations active',
        colorClasses: {
          bg: 'bg-red-50 dark:bg-red-900/20',
          border: 'border-red-300 dark:border-red-700',
          text: 'text-red-700 dark:text-red-300',
          glyphBg: 'bg-red-100 dark:bg-red-900/40',
        },
      };
    case 'PENDING':
    default:
      return {
        pattern: 'PENDING',
        glyphs: '⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜',
        terminalOutput: 'STATUS: ⬜ PENDING — AWAITING EVALUATION',
        label: 'PENDING',
        description: 'Awaiting governance evaluation',
        colorClasses: {
          bg: 'bg-gray-50 dark:bg-gray-800/50',
          border: 'border-gray-300 dark:border-gray-600',
          text: 'text-gray-600 dark:text-gray-400',
          glyphBg: 'bg-gray-100 dark:bg-gray-800',
        },
      };
  }
}

export interface GovernanceStatusCardProps {
  /** Governance summary data */
  summary: GovernanceSummary | null;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: Error | null;
  /** Show terminal-style glyph banner */
  showGlyphBanner?: boolean;
  /** Show shield indicator */
  showShield?: boolean;
  /** Show timestamp */
  showTimestamp?: boolean;
  /** Show stats breakdown */
  showStats?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Stat pill component for metrics display.
 */
function StatPill({
  label,
  value,
  variant = 'default',
}: {
  label: string;
  value: number;
  variant?: 'default' | 'success' | 'warning' | 'error';
}) {
  const variantClasses = {
    default: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300',
    success: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
    warning: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
    error: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
  };

  return (
    <div
      className={`
        flex items-center gap-2 px-3 py-1.5 rounded-lg
        ${variantClasses[variant]}
      `}
    >
      <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      <span className="text-lg font-bold">{value}</span>
    </div>
  );
}

/**
 * Loading skeleton for the status card.
 */
function StatusCardSkeleton() {
  return (
    <div className="animate-pulse p-4 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
      <div className="flex gap-2 mb-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-6 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
        ))}
      </div>
      <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
    </div>
  );
}

/**
 * Error state display.
 */
function ErrorDisplay({ error }: { error: Error }) {
  return (
    <div
      className="p-4 rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20"
      role="alert"
    >
      <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
        <span role="img" aria-label="Error">🔴</span>
        <span className="font-semibold">Governance Status Unavailable</span>
      </div>
      <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error.message}</p>
    </div>
  );
}

/**
 * GovernanceStatusCard — Main status card component.
 */
export function GovernanceStatusCard({
  summary,
  loading = false,
  error = null,
  showGlyphBanner = true,
  showShield = true,
  showTimestamp = true,
  showStats = true,
  compact = false,
  className = '',
}: GovernanceStatusCardProps) {
  const pattern = useMemo(() => deriveGlyphPattern(summary), [summary]);
  const meta = useMemo(() => getGlyphPatternMeta(pattern), [pattern]);

  if (loading) {
    return <StatusCardSkeleton />;
  }

  if (error) {
    return <ErrorDisplay error={error} />;
  }

  return (
    <div
      className={`
        rounded-lg border-2
        ${meta.colorClasses.border}
        ${meta.colorClasses.bg}
        overflow-hidden
        ${className}
      `}
      role="region"
      aria-label="Governance Status"
      data-testid="governance-status-card"
      data-pattern={pattern}
    >
      {/* Glyph Banner — Terminal Parity */}
      {showGlyphBanner && (
        <div
          className={`
            ${meta.colorClasses.glyphBg}
            px-4 py-2 text-center
            font-mono text-lg tracking-widest
            border-b ${meta.colorClasses.border}
          `}
          data-testid="glyph-banner"
          aria-hidden="true"
        >
          {meta.glyphs}
        </div>
      )}

      {/* Main Content */}
      <div className={compact ? 'p-3' : 'p-4'}>
        {/* Header Row */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            {showShield && (
              <GovernanceShield
                summary={summary}
                size={compact ? 'sm' : 'md'}
                showLabel={!compact}
              />
            )}
            {compact && (
              <span className={`font-bold text-sm uppercase ${meta.colorClasses.text}`}>
                {meta.label}
              </span>
            )}
          </div>

          {showTimestamp && summary && (
            compact ? (
              <LastEvaluatedCompact timestamp={summary.last_activity} />
            ) : (
              <LastEvaluatedBadge timestamp={summary.last_activity} size="sm" />
            )
          )}
        </div>

        {/* Terminal Output Line */}
        {!compact && (
          <div
            className={`
              font-mono text-sm px-3 py-2 rounded
              ${meta.colorClasses.glyphBg}
              ${meta.colorClasses.text}
              mb-3
            `}
            data-testid="terminal-output"
          >
            {meta.terminalOutput}
          </div>
        )}

        {/* Stats Row */}
        {showStats && summary && (
          <div className={`flex flex-wrap gap-2 ${compact ? '' : 'mt-3'}`}>
            <StatPill
              label="Total"
              value={summary.total_pacs}
              variant="default"
            />
            <StatPill
              label="Active"
              value={summary.active_pacs}
              variant="success"
            />
            {summary.correction_cycles > 0 && (
              <StatPill
                label="Corrections"
                value={summary.correction_cycles}
                variant="warning"
              />
            )}
            {summary.blocked_pacs > 0 && (
              <StatPill
                label="Blocked"
                value={summary.blocked_pacs}
                variant="error"
              />
            )}
            <StatPill
              label="Closures"
              value={summary.positive_closures}
              variant="success"
            />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * GovernanceStatusStrip — Minimal horizontal strip variant.
 */
export function GovernanceStatusStrip({
  summary,
  className = '',
}: Pick<GovernanceStatusCardProps, 'summary' | 'className'>) {
  const pattern = deriveGlyphPattern(summary);
  const meta = getGlyphPatternMeta(pattern);

  return (
    <div
      className={`
        flex items-center justify-between
        px-4 py-2 rounded-lg
        ${meta.colorClasses.bg}
        border ${meta.colorClasses.border}
        ${className}
      `}
      role="status"
      aria-label={`Governance: ${meta.label}`}
      data-testid="governance-status-strip"
      data-pattern={pattern}
    >
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm" aria-hidden="true">
          {meta.glyphs.slice(0, 5)}
        </span>
        <span className={`font-semibold text-sm ${meta.colorClasses.text}`}>
          {meta.label}
        </span>
      </div>

      {summary && (
        <LastEvaluatedCompact timestamp={summary.last_activity} />
      )}
    </div>
  );
}

export default GovernanceStatusCard;
