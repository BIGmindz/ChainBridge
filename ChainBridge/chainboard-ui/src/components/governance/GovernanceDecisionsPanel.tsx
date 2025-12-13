/**
 * Governance Decisions Panel v0.1
 *
 * Read-only view of GID Kernel governance decisions for ChainBoard operators.
 * Shows APPROVE/FREEZE/REJECT decisions with economic context and policy visibility.
 *
 * GID-HGP Alignment:
 * - L1 (Code = Cash): Surfaces amount, corridor, economic context
 * - L2 (Trust = Truth): Shows policies_applied and risk_score
 * - L3 (Security > Speed): FREEZE decisions visually prominent
 * - L4 (One Truth, Many Views): View over canonical Context Ledger data
 */

import { useState, useEffect, useMemo } from 'react';
import { Search, Filter, AlertTriangle, CheckCircle2, Lock, Info } from 'lucide-react';
import { format } from 'date-fns';

import { governanceDecisionsMock } from '../../services/governanceDecisionsMock';
import type { GovernanceDecision, GovernanceDecisionFilter, GovernanceDecisionStatus } from '../../types/governance';
import { Badge } from '../ui/Badge';
import { CardSkeleton, ErrorState } from '../ui/LoadingStates';
import { classNames } from '../../utils/classNames';
import { GovernanceDecisionDetailDrawer } from './GovernanceDecisionDetailDrawer';

interface GovernanceDecisionsPanelProps {
  className?: string;
}

const statusConfig = {
  APPROVE: {
    variant: 'success' as const,
    icon: CheckCircle2,
    bgColor: 'bg-emerald-500/10',
    textColor: 'text-emerald-300',
    borderColor: 'border-emerald-500/30'
  },
  FREEZE: {
    variant: 'warning' as const,
    icon: Lock,
    bgColor: 'bg-amber-500/10',
    textColor: 'text-amber-300',
    borderColor: 'border-amber-500/40'
  },
  REJECT: {
    variant: 'danger' as const,
    icon: AlertTriangle,
    bgColor: 'bg-rose-500/10',
    textColor: 'text-rose-300',
    borderColor: 'border-rose-500/40'
  }
};

const formatCurrency = (amount: number, currency: string) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
};

const formatRiskScore = (score: number) => {
  const level = score >= 8 ? 'HIGH' : score >= 6 ? 'MEDIUM' : 'LOW';
  const colorClass = score >= 8 ? 'text-rose-300' : score >= 6 ? 'text-amber-300' : 'text-emerald-300';
  return { level, colorClass, score: score.toFixed(1) };
};

export function GovernanceDecisionsPanel({ className }: GovernanceDecisionsPanelProps): JSX.Element {
  const [decisions, setDecisions] = useState<GovernanceDecision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedDecision, setSelectedDecision] = useState<GovernanceDecision | null>(null);

  // Filter state
  const [filters, setFilters] = useState<GovernanceDecisionFilter>({
    status: 'ALL',
    searchQuery: '',
    decisionType: 'ALL'
  });

  // Load decisions
  useEffect(() => {
    const loadDecisions = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await governanceDecisionsMock.fetchGovernanceDecisions(filters, 1, 50);
        setDecisions(response.decisions);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to load governance decisions'));
      } finally {
        setIsLoading(false);
      }
    };

    loadDecisions();
  }, [filters]);

  const statusCounts = useMemo(() => {
    const counts = { APPROVE: 0, FREEZE: 0, REJECT: 0, ALL: decisions.length };
    decisions.forEach(d => {
      counts[d.status] = (counts[d.status] || 0) + 1;
    });
    return counts;
  }, [decisions]);

  const handleStatusFilter = (status: GovernanceDecisionStatus | 'ALL') => {
    setFilters(prev => ({ ...prev, status }));
  };

  const handleSearch = (query: string) => {
    setFilters(prev => ({ ...prev, searchQuery: query }));
  };

  if (error) {
    return (
      <div className={classNames('rounded-2xl border border-slate-800 bg-slate-950/80 p-6', className)}>
        <ErrorState
          title="Governance feed unavailable"
          message={error.message}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className={classNames('rounded-2xl border border-slate-800 bg-slate-950/80 p-6 space-y-6', className)}>
      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Lock className="h-5 w-5 text-indigo-400" />
            <div>
              <h2 className="text-xl font-semibold text-slate-100">Governance Decisions</h2>
              <p className="mt-1 text-sm text-slate-400">
                GID-HGP v1.0 • Real-time settlement decisions by AI governance kernel
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Info className="h-3 w-3" />
          <span>FREEZE indicates ChainIQ Risk Score ≥ threshold</span>
        </div>
      </header>

      {/* Status Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        {(['ALL', 'APPROVE', 'FREEZE', 'REJECT'] as const).map((status) => {
          const isActive = filters.status === status;
          const count = statusCounts[status] || 0;

          return (
            <button
              key={status}
              onClick={() => handleStatusFilter(status)}
              className={classNames(
                'flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-all',
                isActive
                  ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300'
                  : 'border-slate-700/50 bg-slate-800/30 text-slate-300 hover:border-slate-600 hover:bg-slate-800/50'
              )}
            >
              <span>{status === 'ALL' ? 'All Decisions' : status}</span>
              <span className={classNames(
                'rounded-full px-1.5 py-0.5 text-[10px] font-bold',
                isActive ? 'bg-indigo-400/20 text-indigo-200' : 'bg-slate-700 text-slate-400'
              )}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          placeholder="Search by shipment ID, payer, or payee..."
          value={filters.searchQuery || ''}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full rounded-lg border border-slate-700/50 bg-slate-900/50 py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
        />
      </div>

      {/* Decisions Table */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} className="h-16" />
          ))}
        </div>
      ) : decisions.length === 0 ? (
        <div className="rounded-lg border border-slate-800/50 bg-slate-900/30 py-12 text-center">
          <Filter className="mx-auto h-8 w-8 text-slate-500 mb-3" />
          <p className="text-sm font-medium text-slate-300 mb-1">No decisions found</p>
          <p className="text-xs text-slate-500">Try adjusting your filters or search query</p>
        </div>
      ) : (
        <div className="space-y-2">
          {decisions.map((decision) => {
            const statusInfo = statusConfig[decision.status];
            const StatusIcon = statusInfo.icon;
            const riskInfo = formatRiskScore(decision.riskScore);

            return (
              <div
                key={decision.id}
                onClick={() => setSelectedDecision(decision)}
                className={classNames(
                  'cursor-pointer rounded-lg border p-4 transition-all hover:border-indigo-500/30 hover:bg-slate-900/40',
                  statusInfo.borderColor,
                  statusInfo.bgColor
                )}
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  {/* Left: Status + Core Info */}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <StatusIcon className={classNames('h-4 w-4', statusInfo.textColor)} />
                      <Badge variant={statusInfo.variant}>{decision.status}</Badge>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-mono font-medium text-slate-100">{decision.id}</span>
                        {decision.shipmentId && (
                          <>
                            <span className="text-slate-600">→</span>
                            <span className="font-mono text-emerald-300">{decision.shipmentId}</span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>{format(new Date(decision.createdAt), 'MMM dd, HH:mm')}</span>
                        <span>•</span>
                        <span className="capitalize">{decision.decisionType.replace(/_/g, ' ')}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Economic Context + Risk */}
                  <div className="flex flex-col items-start gap-2 md:items-end">
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="font-mono text-sm font-semibold text-slate-100">
                          {formatCurrency(decision.amount, decision.currency)}
                        </div>
                        {decision.corridor && (
                          <div className="text-xs text-slate-400">{decision.corridor}</div>
                        )}
                      </div>

                      <div className="text-right">
                        <div className={classNames('text-sm font-semibold', riskInfo.colorClass)}>
                          {riskInfo.score}
                        </div>
                        <div className="text-xs text-slate-500">{riskInfo.level} RISK</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Drawer */}
      {selectedDecision && (
        <GovernanceDecisionDetailDrawer
          decision={selectedDecision}
          isOpen={!!selectedDecision}
          onClose={() => setSelectedDecision(null)}
        />
      )}
    </div>
  );
}
