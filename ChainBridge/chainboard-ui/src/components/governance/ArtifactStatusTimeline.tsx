/**
 * Artifact Status Timeline — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Displays settlement chains as a timeline with color-coded status.
 * Shows recent PAC → WRAP flows with current progress.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 */

import { Clock, CheckCircle2, AlertTriangle, Pause, XCircle } from 'lucide-react';
import type { SettlementChain } from '../../types/governanceHealth';
import { SettlementFlowDiagram } from './SettlementFlowDiagram';
import { getStageProgress } from '../../hooks/useGovernanceHealth';
import { formatDistanceToNow } from 'date-fns';

interface ArtifactStatusTimelineProps {
  chains: SettlementChain[];
  className?: string;
}

interface TimelineEntryProps {
  chain: SettlementChain;
  isLast?: boolean;
}

function getStatusConfig(status: SettlementChain['status']) {
  switch (status) {
    case 'COMPLETED':
      return {
        icon: CheckCircle2,
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500/20',
        borderColor: 'border-emerald-500/30',
        lineColor: 'bg-emerald-500',
      };
    case 'IN_PROGRESS':
      return {
        icon: Clock,
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/20',
        borderColor: 'border-blue-500/30',
        lineColor: 'bg-blue-500',
      };
    case 'BLOCKED':
      return {
        icon: XCircle,
        color: 'text-rose-400',
        bgColor: 'bg-rose-500/20',
        borderColor: 'border-rose-500/30',
        lineColor: 'bg-rose-500',
      };
    case 'REJECTED':
      return {
        icon: AlertTriangle,
        color: 'text-amber-400',
        bgColor: 'bg-amber-500/20',
        borderColor: 'border-amber-500/30',
        lineColor: 'bg-amber-500',
      };
    default:
      return {
        icon: Pause,
        color: 'text-slate-400',
        bgColor: 'bg-slate-500/20',
        borderColor: 'border-slate-500/30',
        lineColor: 'bg-slate-500',
      };
  }
}

function TimelineEntry({ chain, isLast = false }: TimelineEntryProps): JSX.Element {
  const config = getStatusConfig(chain.status);
  const Icon = config.icon;
  const progress = getStageProgress(chain.currentStage);
  const timeAgo = formatDistanceToNow(new Date(chain.startedAt), { addSuffix: true });

  // Extract short PAC name
  const pacShortName = chain.pacId.split('-').slice(1, 4).join('-');

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div className={`flex items-center justify-center w-8 h-8 rounded-full ${config.bgColor} border ${config.borderColor}`}>
          <Icon className={`h-4 w-4 ${config.color}`} />
        </div>
        {!isLast && (
          <div className={`w-0.5 h-full min-h-[60px] ${config.lineColor} opacity-30`} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-6">
        <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4 space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-200">{pacShortName}</p>
              <p className="text-xs text-slate-500 font-mono truncate max-w-[350px]" title={chain.pacId}>
                {chain.pacId}
              </p>
            </div>
            <div className="text-right">
              <span className={`text-xs px-2 py-0.5 rounded ${config.bgColor} ${config.color}`}>
                {chain.status}
              </span>
              <p className="text-xs text-slate-500 mt-1">{timeAgo}</p>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Settlement Progress</span>
              <span className={config.color}>{progress}%</span>
            </div>
            <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
              <div
                className={`h-full ${config.lineColor} transition-all duration-500`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Compact flow */}
          <SettlementFlowDiagram chain={chain} compact />

          {/* Artifacts */}
          {(chain.berId || chain.pdoId || chain.wrapId) && (
            <div className="flex items-center gap-2 text-xs pt-2 border-t border-slate-700/50">
              <span className="text-slate-500">Artifacts:</span>
              {chain.berId && (
                <span className="px-1.5 py-0.5 bg-yellow-500/10 text-yellow-400 rounded font-mono">
                  BER
                </span>
              )}
              {chain.pdoId && (
                <span className="px-1.5 py-0.5 bg-orange-500/10 text-orange-400 rounded font-mono">
                  PDO
                </span>
              )}
              {chain.wrapId && (
                <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded font-mono">
                  WRAP
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ArtifactStatusTimeline({ chains, className = '' }: ArtifactStatusTimelineProps): JSX.Element {
  if (chains.length === 0) {
    return (
      <div className={`rounded-lg border border-slate-700/50 bg-slate-800/30 p-8 text-center ${className}`}>
        <Clock className="h-8 w-8 text-slate-500 mx-auto mb-2" />
        <p className="text-sm text-slate-400">No settlement chains in progress</p>
        <p className="text-xs text-slate-500 mt-1">Settlement activity will appear here</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-teal-400" />
          <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
            Settlement Timeline
          </h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">{chains.length} chains</span>
      </div>

      <div className="space-y-0">
        {chains.map((chain, idx) => (
          <TimelineEntry
            key={chain.chainId}
            chain={chain}
            isLast={idx === chains.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
