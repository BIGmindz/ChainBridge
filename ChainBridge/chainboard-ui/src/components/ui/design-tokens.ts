/**
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 * LIRA — GID-09 — EXPERIENCE ENGINEER
 * Design Tokens — ChainBoard UI System
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 *
 * Centralized design tokens for consistent styling across ChainBoard components.
 * These tokens are type-safe and support the Calm UX design language.
 */

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export type StatusColor = 'green' | 'yellow' | 'red' | 'gray' | 'blue';
export type RiskTier = 'low' | 'medium' | 'high' | 'critical';
export type GuardrailStatus = 'active' | 'triggered' | 'disabled' | 'pending';
export type SettlementProvider = 'stripe' | 'wise' | 'paypal' | 'manual' | 'unknown';
export type ProofStatus = 'verified' | 'pending' | 'failed' | 'unknown';

// =============================================================================
// STATUS COLORS (RAG + Extended)
// =============================================================================

export const STATUS_COLORS = {
  green: {
    bg: 'bg-green-100',
    bgSolid: 'bg-green-500',
    text: 'text-green-800',
    border: 'border-green-300',
    dot: 'bg-green-500',
    ring: 'ring-green-500/20',
  },
  yellow: {
    bg: 'bg-yellow-100',
    bgSolid: 'bg-yellow-500',
    text: 'text-yellow-800',
    border: 'border-yellow-300',
    dot: 'bg-yellow-500',
    ring: 'ring-yellow-500/20',
  },
  red: {
    bg: 'bg-red-100',
    bgSolid: 'bg-red-500',
    text: 'text-red-800',
    border: 'border-red-300',
    dot: 'bg-red-500',
    ring: 'ring-red-500/20',
  },
  gray: {
    bg: 'bg-gray-100',
    bgSolid: 'bg-gray-500',
    text: 'text-gray-800',
    border: 'border-gray-300',
    dot: 'bg-gray-500',
    ring: 'ring-gray-500/20',
  },
  blue: {
    bg: 'bg-blue-100',
    bgSolid: 'bg-blue-500',
    text: 'text-blue-800',
    border: 'border-blue-300',
    dot: 'bg-blue-500',
    ring: 'ring-blue-500/20',
  },
  // Alias for yellow (RAG amber)
  amber: {
    bg: 'bg-yellow-100',
    bgSolid: 'bg-yellow-500',
    text: 'text-yellow-800',
    border: 'border-yellow-300',
    dot: 'bg-yellow-500',
    ring: 'ring-yellow-500/20',
  },
} as const;

// =============================================================================
// RISK TIER CONFIGURATION
// =============================================================================

export const RISK_TIER_CONFIG = {
  low: {
    label: 'Low Risk',
    color: 'green' as StatusColor,
    threshold: { min: 0, max: 30 },
    icon: 'shield-check',
  },
  medium: {
    label: 'Medium Risk',
    color: 'yellow' as StatusColor,
    threshold: { min: 31, max: 60 },
    icon: 'shield',
  },
  high: {
    label: 'High Risk',
    color: 'red' as StatusColor,
    threshold: { min: 61, max: 85 },
    icon: 'shield-alert',
  },
  critical: {
    label: 'Critical Risk',
    color: 'red' as StatusColor,
    threshold: { min: 86, max: 100 },
    icon: 'shield-x',
  },
} as const;

// =============================================================================
// GUARDRAIL STATUS CONFIGURATION
// =============================================================================

export const GUARDRAIL_STATUS_CONFIG = {
  active: {
    label: 'Active',
    color: 'green' as StatusColor,
    description: 'Guardrail is actively monitoring',
  },
  triggered: {
    label: 'Triggered',
    color: 'red' as StatusColor,
    description: 'Guardrail has been triggered',
  },
  disabled: {
    label: 'Disabled',
    color: 'gray' as StatusColor,
    description: 'Guardrail is currently disabled',
  },
  pending: {
    label: 'Pending',
    color: 'yellow' as StatusColor,
    description: 'Guardrail activation pending',
  },
} as const;

// =============================================================================
// SETTLEMENT PROVIDER CONFIGURATION
// =============================================================================

export const SETTLEMENT_PROVIDER_CONFIG = {
  stripe: {
    label: 'Stripe',
    color: 'blue' as StatusColor,
    icon: 'credit-card',
  },
  wise: {
    label: 'Wise',
    color: 'green' as StatusColor,
    icon: 'globe',
  },
  paypal: {
    label: 'PayPal',
    color: 'blue' as StatusColor,
    icon: 'wallet',
  },
  manual: {
    label: 'Manual',
    color: 'gray' as StatusColor,
    icon: 'hand',
  },
  unknown: {
    label: 'Unknown',
    color: 'gray' as StatusColor,
    icon: 'help-circle',
  },
} as const;

// =============================================================================
// PROOF STATUS CONFIGURATION
// =============================================================================

export const PROOF_STATUS_CONFIG = {
  verified: {
    label: 'Verified',
    color: 'green' as StatusColor,
    icon: 'check-circle',
  },
  pending: {
    label: 'Pending',
    color: 'yellow' as StatusColor,
    icon: 'clock',
  },
  failed: {
    label: 'Failed',
    color: 'red' as StatusColor,
    icon: 'x-circle',
  },
  unknown: {
    label: 'Unknown',
    color: 'gray' as StatusColor,
    icon: 'help-circle',
  },
} as const;

// =============================================================================
// SPACING SCALE
// =============================================================================

export const SPACING = {
  xs: '0.25rem', // 4px
  sm: '0.5rem', // 8px
  md: '1rem', // 16px
  lg: '1.5rem', // 24px
  xl: '2rem', // 32px
  '2xl': '3rem', // 48px
} as const;

// =============================================================================
// TEXT SCALE
// =============================================================================

export const TEXT_SCALES = {
  xs: 'text-xs', // 12px
  sm: 'text-sm', // 14px
  base: 'text-base', // 16px
  lg: 'text-lg', // 18px
  xl: 'text-xl', // 20px
  '2xl': 'text-2xl', // 24px
} as const;

// =============================================================================
// TRANSITIONS (Calm UX)
// =============================================================================

export const TRANSITIONS = {
  fast: 'transition-all duration-150 ease-out',
  normal: 'transition-all duration-300 ease-out',
  slow: 'transition-all duration-500 ease-out',
  calm: 'transition-all duration-700 ease-in-out',
} as const;

// =============================================================================
// FOCUS STYLES
// =============================================================================

export const FOCUS_STYLES = {
  default: 'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
  subtle: 'focus:outline-none focus:ring-1 focus:ring-blue-400/50',
  none: 'focus:outline-none',
} as const;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get Tailwind classes for a given status color
 */
export function getStatusClasses(status: StatusColor) {
  return STATUS_COLORS[status] ?? STATUS_COLORS.gray;
}

/**
 * Get configuration for a given risk tier
 */
export function getRiskTierConfig(tier: RiskTier) {
  return RISK_TIER_CONFIG[tier] ?? RISK_TIER_CONFIG.medium;
}

/**
 * Get configuration for a given guardrail status
 */
export function getGuardrailConfig(status: GuardrailStatus) {
  return GUARDRAIL_STATUS_CONFIG[status] ?? GUARDRAIL_STATUS_CONFIG.pending;
}

/**
 * Convert a numeric score (0-100) to a risk tier
 */
export function scoreToRiskTier(score: number): RiskTier {
  if (score <= 30) return 'low';
  if (score <= 60) return 'medium';
  if (score <= 85) return 'high';
  return 'critical';
}
