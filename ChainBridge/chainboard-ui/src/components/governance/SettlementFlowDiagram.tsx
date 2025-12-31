/**
 * Settlement Flow Diagram — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Visualizes the PAC → BER → PDO → WRAP settlement chain.
 * Shows current status of each stage in the governance flow.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 * @see GOVERNANCE_DOCTRINE_V1.1 Section 4.2
 */

import { ChevronRight, Check, Clock, AlertCircle, Pause, XCircle } from 'lucide-react';
import type { SettlementChain, SettlementFlowNode, ArtifactStatus } from '../../types/governanceHealth';
import { STAGE_CONFIG, STATUS_COLORS } from '../../types/governanceHealth';
import { getStageProgress } from '../../hooks/useGovernanceHealth';

interface SettlementFlowDiagramProps {
  chain: SettlementChain;
  compact?: boolean;
  className?: string;
}

interface FlowNodeProps {
  node: SettlementFlowNode;
  isLast?: boolean;
  compact?: boolean;
}

function getStatusIcon(status: ArtifactStatus): JSX.Element {
  switch (status) {
    case 'FINALIZED':
      return <Check className="h-3 w-3 text-emerald-400" />;
    case 'ACTIVE':
      return <Clock className="h-3 w-3 text-blue-400 animate-pulse" />;
    case 'AWAITING_REVIEW':
      return <Pause className="h-3 w-3 text-amber-400" />;
    case 'BLOCKED':
    case 'REJECTED':
      return <XCircle className="h-3 w-3 text-rose-400" />;
    default:
      return <AlertCircle className="h-3 w-3 text-slate-500" />;
  }
}

function FlowNode({ node, isLast = false, compact = false }: FlowNodeProps): JSX.Element {
  const config = STAGE_CONFIG[node.stage];
  const statusColor = STATUS_COLORS[node.status];

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        <div
          className={`flex items-center justify-center w-6 h-6 rounded-full ${statusColor}`}
          title={`${config.label}: ${node.status}`}
        >
          {getStatusIcon(node.status)}
        </div>
        {!isLast && <ChevronRight className="h-3 w-3 text-slate-600" />}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <div className={`flex flex-col items-center min-w-[80px] p-2 rounded-lg ${statusColor}`}>
        <span className="text-lg">{config.icon}</span>
        <span className="text-[10px] font-mono text-center mt-1">{config.label}</span>
        <div className="flex items-center gap-1 mt-1">
          {getStatusIcon(node.status)}
          <span className="text-[9px] text-slate-400">{node.status}</span>
        </div>
      </div>
      {!isLast && (
        <div className="flex items-center">
          <div
            className={`h-0.5 w-4 ${node.status === 'FINALIZED' ? 'bg-emerald-500' : 'bg-slate-600'}`}
          />
          <ChevronRight
            className={`h-4 w-4 ${node.status === 'FINALIZED' ? 'text-emerald-500' : 'text-slate-600'}`}
          />
        </div>
      )}
    </div>
  );
}

export function SettlementFlowDiagram({ chain, compact = false, className = '' }: SettlementFlowDiagramProps): JSX.Element {
  const progress = getStageProgress(chain.currentStage);

  const statusBadgeColor =
    chain.status === 'COMPLETED'
      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : chain.status === 'IN_PROGRESS'
        ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
        : chain.status === 'BLOCKED'
          ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
          : 'bg-amber-500/20 text-amber-400 border-amber-500/30';

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="flex items-center">
          {chain.nodes.map((node, idx) => (
            <FlowNode key={node.stage} node={node} isLast={idx === chain.nodes.length - 1} compact />
          ))}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded border ${statusBadgeColor}`}>{progress}%</span>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-xs text-slate-500 font-mono truncate max-w-[300px]" title={chain.pacId}>
            {chain.pacId}
          </p>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded border ${statusBadgeColor}`}>{chain.status}</span>
            <span className="text-xs text-slate-400">{progress}% complete</span>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            chain.status === 'COMPLETED'
              ? 'bg-emerald-500'
              : chain.status === 'BLOCKED'
                ? 'bg-rose-500'
                : 'bg-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Flow nodes */}
      <div className="flex items-center justify-between overflow-x-auto pb-2">
        {chain.nodes.map((node, idx) => (
          <FlowNode key={node.stage} node={node} isLast={idx === chain.nodes.length - 1} />
        ))}
      </div>

      {/* Artifact IDs */}
      <div className="flex flex-wrap gap-2 text-xs">
        {chain.berId && (
          <span className="px-2 py-0.5 bg-slate-800/50 rounded text-slate-400 font-mono">
            BER: {chain.berId.split('-').slice(-1)[0]}
          </span>
        )}
        {chain.pdoId && (
          <span className="px-2 py-0.5 bg-slate-800/50 rounded text-slate-400 font-mono">
            PDO: {chain.pdoId.split('-').slice(-1)[0]}
          </span>
        )}
        {chain.wrapId && (
          <span className="px-2 py-0.5 bg-emerald-800/30 rounded text-emerald-400 font-mono">
            WRAP: {chain.wrapId.split('-').slice(-1)[0]}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Canonical settlement flow reference diagram.
 */
export function CanonicalSettlementFlow({ className = '' }: { className?: string }): JSX.Element {
  return (
    <div className={`rounded-lg border border-slate-700/50 bg-slate-900/50 p-4 ${className}`}>
      <p className="text-xs text-slate-500 uppercase tracking-wider font-mono mb-3">
        Canonical Settlement Flow (Doctrine V1.1)
      </p>

      <div className="flex items-center justify-between text-xs font-mono">
        <div className="flex flex-col items-center">
          <span className="text-lg">📋</span>
          <span className="text-teal-400">PAC</span>
          <span className="text-[9px] text-slate-500">Dispatch</span>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-600" />

        <div className="flex flex-col items-center">
          <span className="text-lg">⚙️</span>
          <span className="text-blue-400">Agent</span>
          <span className="text-[9px] text-slate-500">Execute</span>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-600" />

        <div className="flex flex-col items-center">
          <span className="text-lg">📊</span>
          <span className="text-yellow-400">BER</span>
          <span className="text-[9px] text-slate-500">Generate</span>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-600" />

        <div className="flex flex-col items-center">
          <span className="text-lg">👁️</span>
          <span className="text-purple-400">Human</span>
          <span className="text-[9px] text-slate-500">Review</span>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-600" />

        <div className="flex flex-col items-center">
          <span className="text-lg">🔐</span>
          <span className="text-orange-400">PDO</span>
          <span className="text-[9px] text-slate-500">Finalize</span>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-600" />

        <div className="flex flex-col items-center">
          <span className="text-lg">📦</span>
          <span className="text-cyan-400">WRAP</span>
          <span className="text-[9px] text-slate-500">Generate</span>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-600" />

        <div className="flex flex-col items-center">
          <span className="text-lg">✅</span>
          <span className="text-emerald-400">Accepted</span>
          <span className="text-[9px] text-slate-500">Ledger</span>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-700/50">
        <p className="text-[10px] text-slate-500 font-mono">
          Authority: BENSON (GID-00) • No WRAP without PDO • Human review mandatory
        </p>
      </div>
    </div>
  );
}
