/**
 * Governance Decision Detail Drawer
 *
 * Side drawer showing full details of a governance decision including
 * reason codes, policies applied, economic justification, and raw debug JSON.
 */

import { X, Clock, DollarSign, Shield, AlertCircle, Code2 } from 'lucide-react';
import { format } from 'date-fns';
import { useState } from 'react';

import type { GovernanceDecision } from '../../types/governance';
import { Badge } from '../ui/Badge';
import { classNames } from '../../utils/classNames';

interface GovernanceDecisionDetailDrawerProps {
  decision: GovernanceDecision;
  isOpen: boolean;
  onClose: () => void;
}

const formatCurrency = (amount: number, currency: string) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
};

export function GovernanceDecisionDetailDrawer({
  decision,
  isOpen,
  onClose
}: GovernanceDecisionDetailDrawerProps): JSX.Element | null {
  const [showRawJson, setShowRawJson] = useState(false);

  if (!isOpen) return null;

  const statusConfig = {
    APPROVE: { variant: 'success' as const, bgClass: 'bg-emerald-500/10', textClass: 'text-emerald-300' },
    FREEZE: { variant: 'warning' as const, bgClass: 'bg-amber-500/10', textClass: 'text-amber-300' },
    REJECT: { variant: 'danger' as const, bgClass: 'bg-rose-500/10', textClass: 'text-rose-300' }
  };

  const statusInfo = statusConfig[decision.status];

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed bottom-0 right-0 top-0 z-50 w-full overflow-y-auto bg-slate-950/95 shadow-2xl backdrop-blur-md border-l border-slate-800 md:w-[32rem]">
        <div className="space-y-6 p-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-semibold text-slate-100">{decision.id}</h2>
                <Badge variant={statusInfo.variant}>{decision.status}</Badge>
              </div>
              {decision.shipmentId && (
                <p className="font-mono text-sm text-emerald-300">{decision.shipmentId}</p>
              )}
              <p className="text-xs text-slate-500">
                {format(new Date(decision.createdAt), 'MMMM dd, yyyy • HH:mm:ss')}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 transition-colors hover:text-slate-200"
              aria-label="Close detail drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Economic Context */}
          <section className={classNames('rounded-xl border border-slate-800/70 p-4', statusInfo.bgClass)}>
            <div className="flex items-center gap-2 mb-3">
              <DollarSign className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-200">Economic Context</h3>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <p className="text-xs text-slate-500 mb-1">Transaction Amount</p>
                <p className="font-mono text-lg font-semibold text-slate-100">
                  {formatCurrency(decision.amount, decision.currency)}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-1">Corridor</p>
                <p className="font-mono text-sm text-slate-200">{decision.corridor || 'N/A'}</p>
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-1">Payer</p>
                <p className="font-mono text-sm text-slate-200">{decision.payerId}</p>
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-1">Payee</p>
                <p className="font-mono text-sm text-slate-200">{decision.payeeId}</p>
              </div>
            </div>
          </section>

          {/* Risk Assessment */}
          <section className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-200">Risk Assessment</h3>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-500 mb-1">ChainIQ Risk Score</p>
                <div className="flex items-center gap-3">
                  <span className={classNames(
                    'text-2xl font-bold',
                    decision.riskScore >= 8 ? 'text-rose-300' :
                    decision.riskScore >= 6 ? 'text-amber-300' : 'text-emerald-300'
                  )}>
                    {decision.riskScore.toFixed(1)}
                  </span>
                  <span className={classNames(
                    'px-2 py-1 text-xs font-semibold rounded',
                    decision.riskScore >= 8 ? 'bg-rose-500/20 text-rose-300' :
                    decision.riskScore >= 6 ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'
                  )}>
                    {decision.riskScore >= 8 ? 'HIGH RISK' : decision.riskScore >= 6 ? 'MEDIUM RISK' : 'LOW RISK'}
                  </span>
                </div>
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-2">Decision Type</p>
                <Badge variant="info">{decision.decisionType.replace(/_/g, ' ').toUpperCase()}</Badge>
              </div>
            </div>
          </section>

          {/* Reason Codes */}
          <section className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-200">Reason Codes</h3>
            </div>

            <div className="flex flex-wrap gap-2">
              {decision.reasonCodes.map((code, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {code}
                </Badge>
              ))}
            </div>
          </section>

          {/* Policies Applied */}
          <section className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-200">Policies Applied</h3>
            </div>

            <div className="space-y-2">
              {decision.policiesApplied.map((policy, index) => (
                <div key={index} className="flex items-center gap-2 text-sm">
                  <div className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                  <span className="text-slate-300">{policy}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Economic Justification */}
          {decision.economicJustification && (
            <section className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="h-4 w-4 text-slate-400" />
                <h3 className="text-sm font-semibold text-slate-200">Economic Justification</h3>
              </div>

              <p className="text-sm text-slate-300 leading-relaxed">
                {decision.economicJustification}
              </p>
            </section>
          )}

          {/* Agent Metadata */}
          <section className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-200">Agent Metadata</h3>
            </div>

            <div className="grid gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Agent</span>
                <span className="font-mono text-slate-300">{decision.agentId || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">GID</span>
                <span className="font-mono text-slate-300">{decision.gid || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Version</span>
                <span className="font-mono text-slate-300">{decision.gidVersion || 'N/A'}</span>
              </div>
            </div>
          </section>

          {/* Raw JSON Debug (Collapsible) */}
          <section className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="flex w-full items-center justify-between text-left"
            >
              <div className="flex items-center gap-2">
                <Code2 className="h-4 w-4 text-slate-400" />
                <h3 className="text-sm font-semibold text-slate-200">Raw JSON (Guardians/Engineers)</h3>
              </div>
              <span className="text-xs text-slate-500">
                {showRawJson ? 'Hide' : 'Show'}
              </span>
            </button>

            {showRawJson && (
              <div className="mt-3 rounded-lg border border-slate-700/50 bg-slate-950/60 p-3">
                <pre className="text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify({
                    id: decision.id,
                    createdAt: decision.createdAt,
                    decisionType: decision.decisionType,
                    status: decision.status,
                    riskScore: decision.riskScore,
                    reasonCodes: decision.reasonCodes,
                    policiesApplied: decision.policiesApplied,
                    raw: decision.raw
                  }, null, 2)}
                </pre>
              </div>
            )}
          </section>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-slate-800/50">
            {decision.shipmentId && (
              <a
                href={`/shipments?filter=${encodeURIComponent(decision.shipmentId)}`}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-center text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
              >
                View Shipment Details
              </a>
            )}
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:border-slate-600 hover:text-slate-200"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
