/**
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 * LIRA — GID-09 — EXPERIENCE ENGINEER
 * Proof Status Components — ChainBoard UI
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 *
 * Visual components for displaying proofpack status and audit trail entries
 * in the ChainBoard operator dashboard.
 */

import React from 'react';
import { classNames } from '../../utils/classNames';
import {
  PROOF_STATUS_CONFIG,
  getStatusClasses,
  type ProofStatus as ProofStatusType,
} from './design-tokens';

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export interface ProofEntry {
  /** Unique proof entry ID */
  id: string;
  /** Type of proof (e.g., 'signature', 'timestamp', 'hash') */
  type: string;
  /** Verification status */
  status: ProofStatusType;
  /** Timestamp of proof creation */
  createdAt: string;
  /** Optional verification timestamp */
  verifiedAt?: string;
  /** Hash or reference */
  reference?: string;
}

export interface ProofPack {
  /** Unique proofpack ID */
  id: string;
  /** Proofpack name/label */
  name: string;
  /** Overall status */
  status: ProofStatusType;
  /** Number of entries */
  entryCount: number;
  /** Creation timestamp */
  createdAt: string;
  /** Individual proof entries */
  entries?: ProofEntry[];
}

// =============================================================================
// PROOF STATUS BADGE — Compact status indicator
// =============================================================================

export interface ProofStatusBadgeProps {
  /** Proof status */
  status: ProofStatusType;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show status text */
  showLabel?: boolean;
}

export function ProofStatusBadge({
  status,
  size = 'md',
  showLabel = true,
}: ProofStatusBadgeProps) {
  const config = PROOF_STATUS_CONFIG[status] ?? PROOF_STATUS_CONFIG.unknown;
  const colors = getStatusClasses(config.color);

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
      data-testid="proof-status-badge"
    >
      <span
        className={classNames('h-2 w-2 rounded-full', colors.dot)}
        aria-hidden="true"
      />
      {showLabel && config.label}
    </span>
  );
}

// =============================================================================
// PROOF ENTRY CARD — Individual proof entry display
// =============================================================================

export interface ProofEntryCardProps {
  /** Proof entry data */
  entry: ProofEntry;
  /** Compact display mode */
  compact?: boolean;
}

export function ProofEntryCard({
  entry,
  compact = false,
}: ProofEntryCardProps) {
  const config = PROOF_STATUS_CONFIG[entry.status] ?? PROOF_STATUS_CONFIG.unknown;
  const colors = getStatusClasses(config.color);

  if (compact) {
    return (
      <div
        className="flex items-center justify-between gap-2 rounded border border-gray-200 px-3 py-2"
        data-testid="proof-entry-card"
      >
        <span className="text-sm font-medium text-gray-700">{entry.type}</span>
        <ProofStatusBadge status={entry.status} size="sm" />
      </div>
    );
  }

  return (
    <div
      className={classNames(
        'rounded-lg border p-4',
        colors.border
      )}
      data-testid="proof-entry-card"
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-sm font-medium text-gray-500 uppercase">
            {entry.type}
          </span>
          <p className="text-xs text-gray-400 mt-0.5">ID: {entry.id}</p>
        </div>
        <ProofStatusBadge status={entry.status} size="sm" />
      </div>
      <div className="mt-3 space-y-1 text-xs text-gray-500">
        <p>Created: {entry.createdAt}</p>
        {entry.verifiedAt && <p>Verified: {entry.verifiedAt}</p>}
        {entry.reference && (
          <p className="truncate" title={entry.reference}>
            Ref: {entry.reference}
          </p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// PROOF PACK CARD — Proofpack summary display
// =============================================================================

export interface ProofPackCardProps {
  /** Proofpack data */
  pack: ProofPack;
  /** Show entry list */
  showEntries?: boolean;
  /** Max entries to display */
  maxEntries?: number;
  /** Click handler */
  onClick?: () => void;
}

export function ProofPackCard({
  pack,
  showEntries = false,
  maxEntries = 3,
  onClick,
}: ProofPackCardProps) {
  const config = PROOF_STATUS_CONFIG[pack.status] ?? PROOF_STATUS_CONFIG.unknown;
  const colors = getStatusClasses(config.color);
  const displayEntries = pack.entries?.slice(0, maxEntries) ?? [];

  return (
    <div
      className={classNames(
        'rounded-lg border p-4',
        colors.border,
        onClick && 'cursor-pointer hover:shadow-md transition-shadow'
      )}
      onClick={onClick}
      data-testid="proof-pack-card"
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">{pack.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">ID: {pack.id}</p>
        </div>
        <ProofStatusBadge status={pack.status} />
      </div>

      <div className="mt-3 flex items-center gap-4 text-sm text-gray-600">
        <span>{pack.entryCount} entries</span>
        <span>Created: {pack.createdAt}</span>
      </div>

      {showEntries && displayEntries.length > 0 && (
        <div className="mt-4 space-y-2">
          {displayEntries.map((entry) => (
            <ProofEntryCard key={entry.id} entry={entry} compact />
          ))}
          {pack.entries && pack.entries.length > maxEntries && (
            <p className="text-xs text-gray-400 text-center">
              +{pack.entries.length - maxEntries} more entries
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// PROOF CHAIN INDICATOR — Visual chain/timeline of proofs
// =============================================================================

export interface ProofChainIndicatorProps {
  /** Array of proof statuses in chain order */
  proofs: Array<{
    label: string;
    status: ProofStatusType;
  }>;
  /** Compact mode (dots only) */
  compact?: boolean;
}

export function ProofChainIndicator({
  proofs,
  compact = false,
}: ProofChainIndicatorProps) {
  return (
    <div
      className="flex items-center gap-1"
      data-testid="proof-chain-indicator"
    >
      {proofs.map((proof, index) => {
        const config = PROOF_STATUS_CONFIG[proof.status] ?? PROOF_STATUS_CONFIG.unknown;
        const colors = getStatusClasses(config.color);

        return (
          <React.Fragment key={index}>
            {index > 0 && (
              <div className="h-px w-2 bg-gray-300" aria-hidden="true" />
            )}
            <div
              className={classNames(
                'flex items-center justify-center rounded-full',
                colors.bg,
                colors.border,
                'border',
                compact ? 'h-3 w-3' : 'h-6 w-6'
              )}
              title={`${proof.label}: ${config.label}`}
              aria-label={`${proof.label}: ${config.label}`}
            >
              {!compact && (
                <span className={classNames('text-xs font-medium', colors.text)}>
                  {index + 1}
                </span>
              )}
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// =============================================================================
// COMPACT PROOF BADGE — Minimal proof status for tight spaces
// =============================================================================

export interface CompactProofBadgeProps {
  /** Proof status */
  status: ProofStatusType;
  /** Count of proofs */
  count?: number;
}

export function CompactProofBadge({
  status,
  count,
}: CompactProofBadgeProps) {
  const config = PROOF_STATUS_CONFIG[status] ?? PROOF_STATUS_CONFIG.unknown;
  const colors = getStatusClasses(config.color);

  return (
    <span
      className={classNames(
        'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium',
        colors.bg,
        colors.text
      )}
      data-testid="compact-proof-badge"
    >
      <span
        className={classNames('h-1.5 w-1.5 rounded-full', colors.dot)}
        aria-hidden="true"
      />
      {count !== undefined ? count : config.label}
    </span>
  );
}
