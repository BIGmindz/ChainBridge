/**
 * Governance Health Metrics — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Displays key governance health metrics in card format.
 * READ-ONLY visualization of settlement system health.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 */

import { Activity, FileCheck, Shield, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { GovernanceHealthMetrics } from '../../types/governanceHealth';
import { formatSettlementTime } from '../../hooks/useGovernanceHealth';

interface GovernanceHealthMetricsProps {
  metrics: GovernanceHealthMetrics;
  className?: string;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  status?: 'healthy' | 'warning' | 'critical';
}

function MetricCard({ title, value, subtitle, icon, status = 'healthy' }: MetricCardProps): JSX.Element {
  const statusColors = {
    healthy: 'border-emerald-500/30 bg-emerald-500/5',
    warning: 'border-amber-500/30 bg-amber-500/5',
    critical: 'border-rose-500/30 bg-rose-500/5',
  };

  const iconColors = {
    healthy: 'text-emerald-400',
    warning: 'text-amber-400',
    critical: 'text-rose-400',
  };

  return (
    <div className={`rounded-lg border p-4 ${statusColors[status]}`}>
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-mono">{title}</p>
          <p className="text-2xl font-bold text-slate-100">{value}</p>
          {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
        </div>
        <div className={`p-2 rounded-lg bg-slate-800/50 ${iconColors[status]}`}>{icon}</div>
      </div>
    </div>
  );
}

export function GovernanceHealthMetricsPanel({ metrics, className = '' }: GovernanceHealthMetricsProps): JSX.Element {
  const ledgerStatus =
    metrics.ledgerIntegrity === 'HEALTHY'
      ? 'healthy'
      : metrics.ledgerIntegrity === 'DEGRADED'
        ? 'warning'
        : 'critical';

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-teal-400" />
        <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Settlement Health</h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* PAC Metrics */}
        <MetricCard
          title="Total PACs"
          value={metrics.totalPacs}
          subtitle={`${metrics.activePacs} active`}
          icon={<FileCheck className="h-5 w-5" />}
          status="healthy"
        />

        {/* Settlement Rate */}
        <MetricCard
          title="Settlement Rate"
          value={`${metrics.settlementRate.toFixed(1)}%`}
          subtitle="PAC → WRAP completion"
          icon={<CheckCircle2 className="h-5 w-5" />}
          status={metrics.settlementRate >= 90 ? 'healthy' : metrics.settlementRate >= 70 ? 'warning' : 'critical'}
        />

        {/* Avg Settlement Time */}
        <MetricCard
          title="Avg Settlement"
          value={formatSettlementTime(metrics.avgSettlementTimeMs)}
          subtitle="Time to WRAP_ACCEPTED"
          icon={<Clock className="h-5 w-5" />}
          status="healthy"
        />

        {/* Ledger Health */}
        <MetricCard
          title="Ledger Integrity"
          value={metrics.ledgerIntegrity}
          subtitle={metrics.sequenceGaps > 0 ? `${metrics.sequenceGaps} gaps` : 'No gaps'}
          icon={<Shield className="h-5 w-5" />}
          status={ledgerStatus}
        />
      </div>

      {/* Secondary Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
          <p className="text-xs text-slate-500 font-mono">BERs Generated</p>
          <p className="text-lg font-semibold text-slate-200">{metrics.totalBers}</p>
          <p className="text-xs text-emerald-400">{metrics.approvedBers} approved</p>
        </div>

        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
          <p className="text-xs text-slate-500 font-mono">PDOs Finalized</p>
          <p className="text-lg font-semibold text-slate-200">{metrics.finalizedPdos}</p>
          <p className="text-xs text-slate-400">of {metrics.totalPdos} total</p>
        </div>

        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
          <p className="text-xs text-slate-500 font-mono">WRAPs Accepted</p>
          <p className="text-lg font-semibold text-slate-200">{metrics.acceptedWraps}</p>
          <p className="text-xs text-slate-400">of {metrics.totalWraps} total</p>
        </div>

        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
          <p className="text-xs text-slate-500 font-mono">Positive Closures</p>
          <p className="text-lg font-semibold text-emerald-400">{metrics.positiveClosures}</p>
          <p className="text-xs text-slate-400">completed</p>
        </div>

        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
          <p className="text-xs text-slate-500 font-mono">Pending</p>
          <div className="flex items-center gap-2">
            <p className="text-lg font-semibold text-amber-400">{metrics.pendingSettlements}</p>
            {metrics.blockedPacs > 0 && (
              <span className="flex items-center gap-1 text-xs text-rose-400">
                <AlertTriangle className="h-3 w-3" />
                {metrics.blockedPacs} blocked
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
