/**
 * Trust Disclaimer — PAC-TRUST-CENTER-UI-01
 *
 * Explicit boundaries section.
 * CRITICAL for legal safety — prevents misinterpretation.
 *
 * CONSTRAINTS:
 * - Exact text block as specified
 * - No controls
 * - Must always be rendered
 *
 * @see PAC-TRUST-CENTER-UI-01 — Customer Trust Center (Read-Only)
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface TrustDisclaimerProps {
  /** Optional additional className */
  className?: string;
}

/**
 * Trust Disclaimer section.
 * Explicit boundaries to prevent legal blowback.
 */
export function TrustDisclaimer({
  className,
}: TrustDisclaimerProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden border-slate-700/30', className)}>
      <CardContent className="py-4">
        <p className="text-xs text-slate-600 uppercase tracking-wider mb-2">
          disclosure
        </p>
        <p className="text-xs text-slate-500 leading-relaxed font-mono">
          This Trust Center does not grant access, modify decisions, or perform enforcement.
          All data shown is read-only and informational.
        </p>
      </CardContent>
    </Card>
  );
}
