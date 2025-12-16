/**
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 * LIRA — GID-09 — EXPERIENCE ENGINEER
 * Trust Status Components — ChainBoard UI
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 *
 * Visual indicators for trust and risk status in the ChainBoard operator dashboard.
 * Implements RAG (Red/Amber/Green) patterns with Calm UX principles.
 */

import React from 'react';
import { classNames } from '../../utils/classNames';
import {
  getStatusClasses,
  getRiskTierConfig,
  getGuardrailConfig,
  type StatusColor,
  type RiskTier,
  type GuardrailStatus,
} from './design-tokens';

// =============================================================================
// STATUS DOT — Minimal Status Indicator
// =============================================================================

export interface StatusDotProps {
  /** Status color */
  status: StatusColor;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to pulse/animate */
  pulse?: boolean;
  /** Accessible label */
  label?: string;
}

export function StatusDot({
  status,
  size = 'md',
  pulse = false,
  label,
}: StatusDotProps) {
  const colors = getStatusClasses(status);
  const sizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-3 w-3',
    lg: 'h-4 w-4',
  };

  return (
    <span
      className={classNames(
        'inline-block rounded-full',
        colors.dot,
        sizeClasses[size],
        pulse && 'animate-pulse'
      )}
      role="status"
      aria-label={label ?? `Status: ${status}`}
      data-testid="status-dot"
    />
  );
}

// =============================================================================
// RAG BADGE — Red/Amber/Green Status Badge
// =============================================================================

export interface RAGBadgeProps {
  /** Status color */
  status: StatusColor;
  /** Badge label text */
  children: React.ReactNode;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show status dot */
  showDot?: boolean;
}

export function RAGBadge({
  status,
  children,
  size = 'md',
  showDot = true,
}: RAGBadgeProps) {
  const colors = getStatusClasses(status);
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  return (
    <span
      className={classNames(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        colors.bg,
        colors.text,
        colors.border,
        'border',
        sizeClasses[size]
      )}
      data-testid="rag-badge"
    >
      {showDot && <StatusDot status={status} size="sm" />}
      {children}
    </span>
  );
}

// =============================================================================
// RISK TIER BADGE — Displays risk tier with color coding
// =============================================================================

export interface RiskTierBadgeProps {
  /** Risk tier level */
  tier: RiskTier;
  /** Numeric score (0-100) */
  score?: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show score value */
  showScore?: boolean;
}

export function RiskTierBadge({
  tier,
  score,
  size = 'md',
  showScore = false,
}: RiskTierBadgeProps) {
  const config = getRiskTierConfig(tier);

  return (
    <RAGBadge status={config.color} size={size}>
      {config.label}
      {showScore && score !== undefined && (
        <span className="ml-1 opacity-75">({score})</span>
      )}
    </RAGBadge>
  );
}

// =============================================================================
// GUARDRAIL STATUS CARD — Displays guardrail status with description
// =============================================================================

export interface GuardrailStatusCardProps {
  /** Guardrail name */
  name: string;
  /** Current status */
  status: GuardrailStatus;
  /** Optional description override */
  description?: string;
  /** Optional last triggered timestamp */
  lastTriggered?: string;
}

export function GuardrailStatusCard({
  name,
  status,
  description,
  lastTriggered,
}: GuardrailStatusCardProps) {
  const config = getGuardrailConfig(status);
  const colors = getStatusClasses(config.color);

  return (
    <div
      className={classNames(
        'rounded-lg border p-4',
        colors.border,
        colors.bg
      )}
      data-testid="guardrail-status-card"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusDot status={config.color} />
          <span className="font-medium">{name}</span>
        </div>
        <RAGBadge status={config.color} size="sm" showDot={false}>
          {config.label}
        </RAGBadge>
      </div>
      <p className={classNames('mt-2 text-sm', colors.text)}>
        {description ?? config.description}
      </p>
      {lastTriggered && (
        <p className="mt-1 text-xs text-gray-500">
          Last triggered: {lastTriggered}
        </p>
      )}
    </div>
  );
}

// =============================================================================
// GUARDRAIL STRIP — Compact horizontal guardrail status display
// =============================================================================

export interface GuardrailStripProps {
  /** Array of guardrail statuses */
  guardrails: Array<{
    name: string;
    status: GuardrailStatus;
  }>;
  /** Compact mode (icons only) */
  compact?: boolean;
}

export function GuardrailStrip({
  guardrails,
  compact = false,
}: GuardrailStripProps) {
  return (
    <div
      className="flex flex-wrap gap-2"
      data-testid="guardrail-strip"
    >
      {guardrails.map((guardrail, index) => {
        const config = getGuardrailConfig(guardrail.status);
        return compact ? (
          <StatusDot
            key={index}
            status={config.color}
            label={`${guardrail.name}: ${config.label}`}
          />
        ) : (
          <RAGBadge key={index} status={config.color} size="sm">
            {guardrail.name}
          </RAGBadge>
        );
      })}
    </div>
  );
}

// =============================================================================
// PHASE GATE STATUS — Shows pipeline phase gate status
// =============================================================================

export interface PhaseGateStatusProps {
  /** Current phase name */
  phase: string;
  /** Gate status */
  status: 'passed' | 'blocked' | 'pending' | 'skipped';
  /** Optional reason for status */
  reason?: string;
}

export function PhaseGateStatus({
  phase,
  status,
  reason,
}: PhaseGateStatusProps) {
  const statusMap: Record<string, StatusColor> = {
    passed: 'green',
    blocked: 'red',
    pending: 'yellow',
    skipped: 'gray',
  };

  const statusColor = statusMap[status] ?? 'gray';
  const colors = getStatusClasses(statusColor);

  return (
    <div
      className={classNames(
        'flex items-center gap-3 rounded-md border px-3 py-2',
        colors.border
      )}
      data-testid="phase-gate-status"
    >
      <StatusDot status={statusColor} />
      <div className="flex-1">
        <span className="font-medium">{phase}</span>
        {reason && (
          <p className="text-xs text-gray-500">{reason}</p>
        )}
      </div>
      <span
        className={classNames(
          'text-xs font-medium uppercase',
          colors.text
        )}
      >
        {status}
      </span>
    </div>
  );
}
