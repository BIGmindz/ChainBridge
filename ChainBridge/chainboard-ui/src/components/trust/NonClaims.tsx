/**
 * Non-Claims — PAC-SONNY-TRUST-HARDEN-01
 *
 * MANDATORY: Permanently visible. Non-dismissible.
 * Verbatim from TRUST_NON_CLAIMS.md.
 * No interpretation. No conditional rendering.
 *
 * LEGAL HARD STOP — This is not UX polish.
 *
 * @see PAC-SONNY-TRUST-HARDEN-01 — Trust Center Evidence-Only Hardening
 * @see docs/trust/TRUST_NON_CLAIMS.md
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface NonClaimsProps {
  className?: string;
}

/**
 * Non-Claims section.
 * MUST be permanently visible. MUST NOT be dismissible.
 * No conditional logic. No role-based hiding.
 */
export function NonClaims({
  className,
}: NonClaimsProps): JSX.Element {
  return (
    <Card
      className={classNames('overflow-hidden', className)}
      data-testid="non-claims-panel"
      data-permanent="true"
      data-dismissible="false"
    >
      <CardContent className="space-y-3">
        {/* Legal disclaimer — always visible */}
        <div className="border-b border-slate-800/50 pb-2 bg-slate-900/50 -mx-4 -mt-4 px-4 pt-4 mb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
            Explicit Non-Claims
          </p>
          <p className="text-xs text-slate-600 mt-1">
            No guarantees are made. No compliance is asserted. Evidence is presented as recorded.
          </p>
        </div>

        <div className="border-b border-slate-800/50 pb-2">
          <p className="text-xs text-slate-600 uppercase tracking-wider">
            Source
          </p>
          <p className="text-xs text-slate-600 font-mono mt-1">
            docs/trust/TRUST_NON_CLAIMS.md
          </p>
        </div>

        <ul className="space-y-2 text-sm text-slate-400">
          <li>
            <span className="text-slate-600 text-xs">TNC-SEC-01:</span>{' '}
            ChainBridge does not secure infrastructure.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-SEC-02:</span>{' '}
            ChainBridge does not harden or secure operating systems.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-SEC-03:</span>{' '}
            ChainBridge does not manage, store, or rotate credentials.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-SEC-04:</span>{' '}
            ChainBridge does not provide network-level security.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-COMP-01:</span>{' '}
            ChainBridge does not claim complete coverage of all attack vectors.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-COMP-02:</span>{' '}
            ChainBridge does not protect against unknown vulnerabilities.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-CORR-01:</span>{' '}
            ChainBridge does not guarantee code correctness.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-CORR-02:</span>{' '}
            ChainBridge does not validate data correctness.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-CERT-01:</span>{' '}
            ChainBridge governance is not externally certified.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-CERT-02:</span>{' '}
            ChainBridge does not guarantee regulatory compliance.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-AVAIL-01:</span>{' '}
            ChainBridge does not guarantee availability.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-ATK-01:</span>{' '}
            ChainBridge does not prevent supply chain attacks.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-ATK-02:</span>{' '}
            ChainBridge does not prevent social engineering.
          </li>
          <li>
            <span className="text-slate-600 text-xs">TNC-ATK-03:</span>{' '}
            ChainBridge does not provide physical security.
          </li>
        </ul>
      </CardContent>
    </Card>
  );
}
