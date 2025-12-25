/**
 * GovernanceVisualLanguage — PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 *
 * Canonical visual language for governance signals that is:
 * - DISTINCT from agent identity (no agent colors)
 * - Terminal-safe (works with emoji/glyphs in CLI)
 * - Accessible (high contrast, color-blind safe)
 * - 1:1 parity between terminal and UI
 *
 * DESIGN PRINCIPLES:
 * - Governance uses SHAPES (shields, checkmarks, X) not agent colors
 * - Status colors are semantic (not agent-specific)
 * - Terminal output maps exactly to UI components
 *
 * @see PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 * @see docs/governance/GOVERNANCE_SIGNAL_SEMANTICS.md
 */

// ============================================================================
// SIGNAL STATUS TYPES (from GOVERNANCE_SIGNAL_SEMANTICS.md)
// ============================================================================

/**
 * Governance signal status — canonical codes from spec.
 */
export type SignalStatus = 'PASS' | 'WARN' | 'FAIL' | 'SKIP';

/**
 * Signal status numeric codes (for sorting/comparison).
 */
export const SIGNAL_STATUS_CODES: Record<SignalStatus, number> = {
  PASS: 0,
  WARN: 1,
  FAIL: 2,
  SKIP: 3,
};

/**
 * Severity levels — canonical from spec.
 */
export type SignalSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';

/**
 * Severity numeric levels (for sorting/comparison).
 */
export const SEVERITY_LEVELS: Record<SignalSeverity, number> = {
  NONE: 0,
  LOW: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4,
};

/**
 * Review state — for review gate visualization.
 */
export type ReviewState = 'PENDING' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'SKIPPED';

// ============================================================================
// TERMINAL GLYPHS — Large, high-contrast symbols
// ============================================================================

/**
 * Terminal-safe glyphs for governance signals.
 * These are large emoji that render well in terminals.
 */
export const TERMINAL_GLYPHS = {
  // Status indicators (NOT agent colors)
  PASS: '✓',           // Checkmark — universal success
  WARN: '⚠',           // Warning triangle — universal caution
  FAIL: '✗',           // X mark — universal failure
  SKIP: '○',           // Empty circle — skipped/not applicable
  
  // Large block variants for banners
  PASS_BLOCK: '🟩',    // Green square — governance success
  WARN_BLOCK: '🟧',    // Orange square — governance warning (NOT yellow/agent)
  FAIL_BLOCK: '🟥',    // Red square — governance failure
  SKIP_BLOCK: '⬜',    // White square — skipped
  
  // Shield variants (distinct from agent circles)
  SHIELD_PASS: '🛡️',   // Shield — protected/compliant
  SHIELD_WARN: '⚠️',    // Warning — needs attention
  SHIELD_FAIL: '🚫',   // Prohibited — blocked
  SHIELD_SKIP: '➖',   // Minus — excluded
  
  // Gate indicators
  GATE_OPEN: '🔓',     // Unlocked — gate passed
  GATE_CLOSED: '🔒',   // Locked — gate blocked
  GATE_PENDING: '⏳',  // Hourglass — awaiting
  
  // Review state
  REVIEW_PENDING: '👁️',   // Eye — under review
  REVIEW_APPROVED: '✅',  // Check mark box
  REVIEW_REJECTED: '❌',  // X mark box
  
  // Severity markers (shapes, not colors)
  CRITICAL: '🔺',      // Red triangle — critical
  HIGH: '◆',           // Diamond — high
  MEDIUM: '●',         // Circle — medium
  LOW: '○',            // Empty circle — low
  
  // Progress
  COMPLETE: '█',       // Filled block
  PARTIAL: '▓',        // Partial block
  EMPTY: '░',          // Empty block
} as const;

/**
 * Terminal banner patterns — 10 glyphs wide to match agent banners.
 */
export const TERMINAL_BANNERS = {
  PASS: '🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩',
  WARN: '🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧',
  FAIL: '🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥',
  SKIP: '⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜',
  PENDING: '⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜',
  IN_REVIEW: '🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦',
} as const;

// ============================================================================
// UI COLOR SYSTEM — Semantic, NOT agent-derived
// ============================================================================

/**
 * Governance color palette — DISTINCT from agent colors.
 *
 * Key design decisions:
 * - PASS uses emerald (not any agent's green)
 * - WARN uses orange (not yellow/SONNY)
 * - FAIL uses rose (not red/BENSON)
 * - SKIP uses slate (neutral)
 *
 * This ensures governance state is NEVER confused with agent identity.
 */
export const GOVERNANCE_COLORS = {
  // PASS — Emerald (distinct from agent greens)
  PASS: {
    bg: 'bg-emerald-500',
    bgLight: 'bg-emerald-100 dark:bg-emerald-900/30',
    border: 'border-emerald-500',
    text: 'text-emerald-700 dark:text-emerald-300',
    textBold: 'text-emerald-600 dark:text-emerald-400',
    hex: '#10b981',
    hexLight: '#d1fae5',
  },
  
  // WARN — Orange (NOT yellow, to avoid SONNY confusion)
  WARN: {
    bg: 'bg-orange-500',
    bgLight: 'bg-orange-100 dark:bg-orange-900/30',
    border: 'border-orange-500',
    text: 'text-orange-700 dark:text-orange-300',
    textBold: 'text-orange-600 dark:text-orange-400',
    hex: '#f97316',
    hexLight: '#ffedd5',
  },
  
  // FAIL — Rose (distinct from pure red)
  FAIL: {
    bg: 'bg-rose-500',
    bgLight: 'bg-rose-100 dark:bg-rose-900/30',
    border: 'border-rose-500',
    text: 'text-rose-700 dark:text-rose-300',
    textBold: 'text-rose-600 dark:text-rose-400',
    hex: '#f43f5e',
    hexLight: '#ffe4e6',
  },
  
  // SKIP — Slate (neutral, no agency)
  SKIP: {
    bg: 'bg-slate-400',
    bgLight: 'bg-slate-100 dark:bg-slate-800/50',
    border: 'border-slate-400',
    text: 'text-slate-600 dark:text-slate-400',
    textBold: 'text-slate-500 dark:text-slate-500',
    hex: '#94a3b8',
    hexLight: '#f1f5f9',
  },
  
  // PENDING — Sky blue (review state, not agent)
  PENDING: {
    bg: 'bg-sky-500',
    bgLight: 'bg-sky-100 dark:bg-sky-900/30',
    border: 'border-sky-500',
    text: 'text-sky-700 dark:text-sky-300',
    textBold: 'text-sky-600 dark:text-sky-400',
    hex: '#0ea5e9',
    hexLight: '#e0f2fe',
  },
} as const;

/**
 * Severity color mapping — shape-based visual hierarchy.
 */
export const SEVERITY_COLORS = {
  CRITICAL: {
    bg: 'bg-red-600',
    bgLight: 'bg-red-100 dark:bg-red-900/40',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-600',
  },
  HIGH: {
    bg: 'bg-orange-600',
    bgLight: 'bg-orange-100 dark:bg-orange-900/40',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-600',
  },
  MEDIUM: {
    bg: 'bg-amber-500',
    bgLight: 'bg-amber-100 dark:bg-amber-900/40',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-500',
  },
  LOW: {
    bg: 'bg-sky-500',
    bgLight: 'bg-sky-100 dark:bg-sky-900/40',
    text: 'text-sky-700 dark:text-sky-300',
    border: 'border-sky-500',
  },
  NONE: {
    bg: 'bg-emerald-500',
    bgLight: 'bg-emerald-100 dark:bg-emerald-900/40',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-500',
  },
} as const;

// ============================================================================
// SIGNAL METADATA — Full visual config for each status
// ============================================================================

export interface SignalVisualConfig {
  status: SignalStatus;
  label: string;
  description: string;
  glyph: string;
  glyphBlock: string;
  banner: string;
  terminalLine: string;
  colors: typeof GOVERNANCE_COLORS[keyof typeof GOVERNANCE_COLORS];
  ariaLabel: string;
}

/**
 * Get complete visual configuration for a signal status.
 */
export function getSignalVisualConfig(status: SignalStatus): SignalVisualConfig {
  switch (status) {
    case 'PASS':
      return {
        status: 'PASS',
        label: 'PASS',
        description: 'All checks satisfied',
        glyph: TERMINAL_GLYPHS.PASS,
        glyphBlock: TERMINAL_GLYPHS.PASS_BLOCK,
        banner: TERMINAL_BANNERS.PASS,
        terminalLine: `${TERMINAL_GLYPHS.PASS} PASS`,
        colors: GOVERNANCE_COLORS.PASS,
        ariaLabel: 'Check passed',
      };
    case 'WARN':
      return {
        status: 'WARN',
        label: 'WARN',
        description: 'Advisory condition detected',
        glyph: TERMINAL_GLYPHS.WARN,
        glyphBlock: TERMINAL_GLYPHS.WARN_BLOCK,
        banner: TERMINAL_BANNERS.WARN,
        terminalLine: `${TERMINAL_GLYPHS.WARN} WARN`,
        colors: GOVERNANCE_COLORS.WARN,
        ariaLabel: 'Warning detected',
      };
    case 'FAIL':
      return {
        status: 'FAIL',
        label: 'FAIL',
        description: 'Blocking condition detected',
        glyph: TERMINAL_GLYPHS.FAIL,
        glyphBlock: TERMINAL_GLYPHS.FAIL_BLOCK,
        banner: TERMINAL_BANNERS.FAIL,
        terminalLine: `${TERMINAL_GLYPHS.FAIL} FAIL`,
        colors: GOVERNANCE_COLORS.FAIL,
        ariaLabel: 'Check failed',
      };
    case 'SKIP':
      return {
        status: 'SKIP',
        label: 'SKIP',
        description: 'Check not applicable',
        glyph: TERMINAL_GLYPHS.SKIP,
        glyphBlock: TERMINAL_GLYPHS.SKIP_BLOCK,
        banner: TERMINAL_BANNERS.SKIP,
        terminalLine: `${TERMINAL_GLYPHS.SKIP} SKIP`,
        colors: GOVERNANCE_COLORS.SKIP,
        ariaLabel: 'Check skipped',
      };
  }
}

/** Severity glyph mapping */
const SEVERITY_GLYPHS: Record<SignalSeverity, string> = {
  NONE: TERMINAL_GLYPHS.SKIP,
  LOW: TERMINAL_GLYPHS.PASS,
  MEDIUM: TERMINAL_GLYPHS.WARN,
  HIGH: TERMINAL_GLYPHS.FAIL,
  CRITICAL: TERMINAL_GLYPHS.FAIL,
} as const;

/**
 * Get severity visual configuration.
 */
export function getSeverityVisualConfig(severity: SignalSeverity) {
  return {
    severity,
    level: SEVERITY_LEVELS[severity],
    glyph: SEVERITY_GLYPHS[severity],
    colors: SEVERITY_COLORS[severity],
    label: severity,
  };
}

// ============================================================================
// TERMINAL OUTPUT HELPERS
// ============================================================================

/**
 * Format a signal for terminal output.
 */
export function formatTerminalSignal(
  status: SignalStatus,
  severity: SignalSeverity,
  code: string,
  title: string
): string {
  const config = getSignalVisualConfig(status);
  return `│ ${config.glyph} ${status} | ${severity} | ${code.padEnd(10)} │\n│ ${title.padEnd(75)} │`;
}

/**
 * Format terminal summary line.
 */
export function formatTerminalSummary(counts: {
  pass: number;
  warn: number;
  fail: number;
  skip: number;
}): string {
  const status = counts.fail > 0 ? 'INVALID' : 'VALID';
  const glyph = counts.fail > 0 ? TERMINAL_GLYPHS.FAIL : TERMINAL_GLYPHS.PASS;
  
  return `SUMMARY: ${counts.fail} FAIL | ${counts.warn} WARN | ${counts.pass} PASS | ${counts.skip} SKIP\nSTATUS: ${glyph} ${status}`;
}

/**
 * Generate terminal banner for validation result.
 */
export function generateTerminalBanner(status: 'VALID' | 'INVALID' | 'PENDING'): string {
  const banner = status === 'VALID' 
    ? TERMINAL_BANNERS.PASS 
    : status === 'INVALID' 
      ? TERMINAL_BANNERS.FAIL 
      : TERMINAL_BANNERS.PENDING;
  
  return `
══════════════════════════════════════════════════════════════════════════════
${banner}
GOVERNANCE VALIDATION RESULT
${banner}
══════════════════════════════════════════════════════════════════════════════`;
}

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type GovernanceColorKey = keyof typeof GOVERNANCE_COLORS;
export type SeverityColorKey = keyof typeof SEVERITY_COLORS;
