/**
 * RiskDisclosurePanel — HAM v1
 *
 * Displays risk factors and constraints from backend metadata.
 * Read-only, no modification, verbatim rendering.
 *
 * @see PAC-DIGGI-04 — Human Approval Modal
 */

import { AlertTriangle, ShieldAlert } from 'lucide-react';

interface Props {
  /** Risk factors from backend */
  risks: readonly string[];
  /** Optional denial reason that triggered escalation */
  denialReason?: string;
  /** Optional denial detail */
  denialDetail?: string;
}

/**
 * Displays risk factors and constraints that led to requiring human approval.
 * All content is rendered verbatim from backend — no filtering or modification.
 */
export function RiskDisclosurePanel({
  risks,
  denialReason,
  denialDetail,
}: Props): JSX.Element {
  const hasRisks = risks.length > 0;
  const hasDenialInfo = denialReason || denialDetail;

  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-950/20">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-amber-500/30 px-4 py-3">
        <ShieldAlert className="h-5 w-5 text-amber-400" />
        <span className="text-sm font-semibold text-amber-300">
          Risk & Constraints
        </span>
      </div>

      <div className="p-4 space-y-4">
        {/* Denial context if present */}
        {hasDenialInfo && (
          <div className="rounded-md bg-amber-900/30 p-3">
            {denialReason && (
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" />
                <div>
                  <p className="text-sm font-medium text-amber-200">
                    {denialReason}
                  </p>
                  {denialDetail && (
                    <p className="mt-1 text-xs text-amber-300/80">
                      {denialDetail}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Risk factors list */}
        {hasRisks ? (
          <ul className="space-y-2">
            {risks.map((risk, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-400" />
                <span className="text-sm text-amber-100">{risk}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-amber-200/60">
            No additional risk factors reported.
          </p>
        )}

        {/* Warning footer */}
        <div className="rounded-md bg-amber-900/20 p-3 border border-amber-500/20">
          <p className="text-xs text-amber-300/80">
            Review all risk factors carefully before authorizing this action.
            You are personally responsible for this approval.
          </p>
        </div>
      </div>
    </div>
  );
}
