/**
 * Trust Non-Claims — PAC-TRUST-CENTER-01
 *
 * Mandatory non-claims section.
 * Explicitly states what the Trust Center does NOT represent.
 *
 * CONSTRAINTS:
 * - This section MUST exist
 * - Text is exact — no modification
 * - No buttons or controls
 *
 * @see PAC-TRUST-CENTER-01 — Public Trust Center (Read-Only)
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent, CardHeader } from '../ui/Card';

export interface TrustNonClaimsProps {
  /** Optional additional className */
  className?: string;
}

/**
 * Non-claims section.
 * Mandatory — explicitly states limitations.
 */
export function TrustNonClaims({
  className,
}: TrustNonClaimsProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden border-slate-700/50', className)}>
      <CardHeader className="border-b border-slate-800/50">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-400">
            Non-Claims
          </h3>
        </div>
      </CardHeader>

      <CardContent>
        {/* Exact text — mandatory, no modification */}
        <ul className="space-y-2">
          <li className="flex items-start gap-2 text-sm text-slate-500">
            <span className="mt-1.5 h-1 w-1 rounded-full bg-slate-600 flex-shrink-0" />
            This does not guarantee correctness
          </li>
          <li className="flex items-start gap-2 text-sm text-slate-500">
            <span className="mt-1.5 h-1 w-1 rounded-full bg-slate-600 flex-shrink-0" />
            This does not imply coverage completeness
          </li>
          <li className="flex items-start gap-2 text-sm text-slate-500">
            <span className="mt-1.5 h-1 w-1 rounded-full bg-slate-600 flex-shrink-0" />
            This is not external certification
          </li>
        </ul>
      </CardContent>
    </Card>
  );
}
