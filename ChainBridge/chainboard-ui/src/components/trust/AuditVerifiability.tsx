/**
 * Audit Verifiability — PAC-TRUST-CENTER-UI-01
 *
 * Explains how verification works (not how governance works).
 * Includes copy button for bundle hash ONLY.
 *
 * CONSTRAINTS:
 * - Read-only display
 * - Copy button for hash only (single allowed interaction)
 * - No other controls
 * - Customer-safe language
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { useState } from 'react';
import { Archive, Copy, Check } from 'lucide-react';

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';
import type { AuditBundleMetadata } from '../../types/trust';

export interface AuditVerifiabilityProps {
  /** Audit bundle from GET /trust/audit/latest */
  auditBundle?: AuditBundleMetadata;
  /** Schema version */
  schemaVersion?: string;
  /** Optional additional className */
  className?: string;
}

/**
 * Audit Verifiability section.
 * Customer-facing explanation of verification capability.
 */
export function AuditVerifiability({
  auditBundle,
  schemaVersion = '1.0.0',
  className,
}: AuditVerifiabilityProps): JSX.Element {
  const [copied, setCopied] = useState(false);

  // Copy bundle hash to clipboard — ONLY allowed interaction
  const handleCopyHash = async () => {
    if (!auditBundle?.bundle_hash) return;

    try {
      await navigator.clipboard.writeText(auditBundle.bundle_hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Silently fail — no error states
    }
  };

  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <Archive className="h-5 w-5 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Audit Verifiability
          </h3>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Bundle Hash with copy button */}
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
            Bundle Hash
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-sm text-slate-300 font-mono bg-slate-900/50 rounded px-3 py-2 truncate">
              {auditBundle?.bundle_hash ?? 'Unavailable'}
            </code>
            {auditBundle?.bundle_hash && (
              <button
                type="button"
                onClick={handleCopyHash}
                className="flex items-center gap-1.5 px-3 py-2 text-xs text-slate-400 bg-slate-800/50 border border-slate-700/50 rounded hover:bg-slate-800 transition-colors"
                aria-label="Copy bundle hash"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Verification fields */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Offline Verification
            </p>
            <p className="text-sm text-slate-300">
              {auditBundle?.status === 'offline-verifiable' ? 'YES' : 'Unavailable'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
              Schema Version
            </p>
            <p className="text-sm text-slate-300 font-mono">
              {schemaVersion}
            </p>
          </div>
        </div>

        {/* Customer-safe explanation */}
        <p className="text-xs text-slate-500 italic border-t border-slate-800/50 pt-3">
          Audit bundles can be independently verified using standard cryptographic tools.
        </p>
      </CardContent>
    </Card>
  );
}
