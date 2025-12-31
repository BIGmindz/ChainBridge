/**
 * Governance Health Dashboard — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Main dashboard component for the ChainBridge Trust Center.
 * Visualizes the Decision Settlement System using governance artifacts.
 *
 * READ-ONLY — No write operations to governance data.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 * @see GOVERNANCE_DOCTRINE_V1.1
 */

import { RefreshCw, Activity, AlertTriangle, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { useGovernanceHealth } from '../../hooks/useGovernanceHealth';
import { GovernanceHealthMetricsPanel } from './GovernanceHealthMetrics';
import { CanonicalSettlementFlow } from './SettlementFlowDiagram';
import { ArtifactStatusTimeline } from './ArtifactStatusTimeline';
import { EnterpriseComplianceSummaryPanel } from './EnterpriseComplianceSummary';

interface GovernanceHealthDashboardProps {
  className?: string;
  refreshInterval?: number;
}

export function GovernanceHealthDashboard({
  className = '',
  refreshInterval = 30000,
}: GovernanceHealthDashboardProps): JSX.Element {
  const { metrics, recentChains, complianceSummary, isLoading, error, lastUpdated } =
    useGovernanceHealth(refreshInterval);

  const timeAgo = lastUpdated ? formatDistanceToNow(new Date(lastUpdated), { addSuffix: true }) : 'never';

  if (error) {
    return (
      <div className={`rounded-lg border border-rose-500/30 bg-rose-500/10 p-8 ${className}`}>
        <div className="flex flex-col items-center text-center">
          <AlertTriangle className="h-8 w-8 text-rose-400 mb-2" />
          <h3 className="text-lg font-medium text-rose-300">Failed to Load Governance Health</h3>
          <p className="text-sm text-rose-400/70 mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-teal-400" />
            <h2 className="text-xl font-semibold text-slate-100">Governance Health Dashboard</h2>
          </div>
          <p className="text-sm text-slate-500 font-mono">
            Decision Settlement System • Doctrine V1.1
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs text-slate-500 font-mono">Last updated</p>
            <p className="text-sm text-slate-400">{timeAgo}</p>
          </div>
          {isLoading && (
            <RefreshCw className="h-4 w-4 text-teal-400 animate-spin" />
          )}
        </div>
      </header>

      {/* Canonical Settlement Flow Reference */}
      <CanonicalSettlementFlow />

      {/* Health Metrics */}
      <GovernanceHealthMetricsPanel metrics={metrics} />

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Settlement Timeline */}
        <div className="space-y-4">
          <ArtifactStatusTimeline chains={recentChains} />
        </div>

        {/* Right: Enterprise Compliance */}
        <div className="space-y-4">
          <EnterpriseComplianceSummaryPanel summary={complianceSummary} />
        </div>
      </div>

      {/* Footer */}
      <footer className="flex items-center justify-between pt-4 border-t border-slate-700/50">
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="font-mono">🟦🟩 BENSON (GID-00) Authority</span>
          <span>•</span>
          <span>Settlement Chain: PAC → BER → PDO → WRAP</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <Clock className="h-3 w-3 text-slate-500" />
          <span className="text-slate-500">
            Auto-refresh: {refreshInterval / 1000}s
          </span>
        </div>
      </footer>
    </div>
  );
}

export default GovernanceHealthDashboard;
