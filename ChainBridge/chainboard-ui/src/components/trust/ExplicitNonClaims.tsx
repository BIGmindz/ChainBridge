/**
 * Explicit Non-Claims — PAC-SONNY-TRUST-UI-REDUCTION-01
 *
 * Verbatim from canonical TRUST_NON_CLAIMS.md.
 * No paraphrasing, no interpretation.
 *
 * CONSTRAINTS:
 * - Exact text from canonical source
 * - No icons
 * - No paraphrasing
 * - Link to source document
 *
 * @see PAC-SONNY-TRUST-UI-REDUCTION-01
 * @see docs/trust/TRUST_NON_CLAIMS.md
 */

import { classNames } from '../../utils/classNames';
import { Card, CardContent } from '../ui/Card';

export interface ExplicitNonClaimsProps {
  /** Optional className */
  className?: string;
}

/**
 * Explicit Non-Claims section.
 * Verbatim from canonical source.
 */
export function ExplicitNonClaims({
  className,
}: ExplicitNonClaimsProps): JSX.Element {
  return (
    <Card className={classNames('overflow-hidden', className)}>
      <CardContent className="space-y-4">
        {/* Section header — factual format */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider">
            Artifact
          </p>
          <p className="text-sm text-slate-300">Non-Claims</p>
        </div>

        {/* Source reference — file path only, no interpretation */}
        <div className="border-b border-slate-800/50 pb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
            Source
          </p>
          <p className="text-sm text-slate-400 font-mono">
            docs/trust/TRUST_NON_CLAIMS.md
          </p>
        </div>

        {/* Verbatim non-claims — from canonical source */}
        <ul className="space-y-3 pt-2 text-sm text-slate-400">
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-SEC-01</p>
            <p>ChainBridge does not secure infrastructure.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-SEC-02</p>
            <p>ChainBridge does not harden or secure operating systems.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-SEC-03</p>
            <p>ChainBridge does not manage, store, or rotate credentials.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-SEC-04</p>
            <p>ChainBridge does not provide network-level security.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-COMP-01</p>
            <p>ChainBridge does not claim complete coverage of all attack vectors.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-COMP-02</p>
            <p>ChainBridge does not protect against unknown vulnerabilities.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-CORR-01</p>
            <p>ChainBridge does not guarantee code correctness.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-CORR-02</p>
            <p>ChainBridge does not validate data correctness.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-CERT-01</p>
            <p>ChainBridge governance is not externally certified.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-CERT-02</p>
            <p>ChainBridge does not guarantee regulatory compliance.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-AVAIL-01</p>
            <p>ChainBridge does not guarantee availability.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-ATK-01</p>
            <p>ChainBridge does not prevent supply chain attacks.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-ATK-02</p>
            <p>ChainBridge does not prevent social engineering.</p>
          </li>
          <li>
            <p className="text-slate-500 text-xs mb-1">TNC-ATK-03</p>
            <p>ChainBridge does not provide physical security.</p>
          </li>
        </ul>
      </CardContent>
    </Card>
  );
}
