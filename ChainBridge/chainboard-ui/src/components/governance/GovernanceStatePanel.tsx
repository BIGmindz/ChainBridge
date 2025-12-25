/**
 * GovernanceStatePanel — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * Real-time governance state visualization for operators.
 * Shows current governance state, blocks, escalations, and PAC status.
 *
 * Visual Language:
 * - 🟢 OPEN/UNBLOCKED = Green, system healthy
 * - 🟡 CORRECTION_REQUIRED/RESUBMITTED = Yellow, action needed
 * - 🔴 BLOCKED/REJECTED = Red, system halted
 * - 🔵 RATIFIED = Blue, awaiting unblock
 *
 * CONSTRAINTS:
 * - Read-only display — no actions except allowed ones
 * - All data from backend — no client-side interpretation
 * - State always visible — cannot be hidden
 * - Errors surfaced prominently
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

import { 
  Shield, 
  ShieldAlert, 
  ShieldCheck, 
  ShieldX, 
  Clock, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useState } from 'react';

import { useGovernanceState } from '../../hooks/useGovernanceState';
import type { 
  GovernanceUIState, 
  EscalationLevel,
  GovernanceBlockReason,
  GovernanceEscalation,
} from '../../types/governanceState';
import { classNames } from '../../utils/classNames';

/**
 * State visual configuration.
 */
const STATE_CONFIG: Record<GovernanceUIState, {
  icon: typeof Shield;
  bg: string;
  border: string;
  text: string;
  label: string;
  description: string;
}> = {
  OPEN: {
    icon: ShieldCheck,
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/40',
    text: 'text-emerald-400',
    label: 'SYSTEM OPEN',
    description: 'Governance gates passed. Actions enabled.',
  },
  BLOCKED: {
    icon: ShieldX,
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/40',
    text: 'text-rose-400',
    label: 'SYSTEM BLOCKED',
    description: 'Governance gate failure. All actions disabled.',
  },
  CORRECTION_REQUIRED: {
    icon: ShieldAlert,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/40',
    text: 'text-amber-400',
    label: 'CORRECTION REQUIRED',
    description: 'PAC correction needed. Resubmit to proceed.',
  },
  RESUBMITTED: {
    icon: Clock,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/40',
    text: 'text-amber-300',
    label: 'RESUBMITTED',
    description: 'PAC resubmitted. Awaiting re-evaluation.',
  },
  RATIFIED: {
    icon: Shield,
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/40',
    text: 'text-sky-400',
    label: 'RATIFIED',
    description: 'Authority ratified. Unblock system to proceed.',
  },
  UNBLOCKED: {
    icon: ShieldCheck,
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/40',
    text: 'text-emerald-400',
    label: 'UNBLOCKED',
    description: 'System unblocked. Normal operation resumed.',
  },
  REJECTED: {
    icon: XCircle,
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/40',
    text: 'text-rose-300',
    label: 'REJECTED',
    description: 'PAC rejected. Archive only.',
  },
};

/**
 * Escalation level visual configuration.
 */
const ESCALATION_CONFIG: Record<EscalationLevel, {
  color: string;
  label: string;
}> = {
  NONE: { color: 'text-slate-400', label: 'None' },
  L1_AGENT: { color: 'text-sky-400', label: 'L1 Agent' },
  L2_GUARDIAN: { color: 'text-amber-400', label: 'L2 Guardian' },
  L3_HUMAN: { color: 'text-rose-400', label: 'L3 Human' },
};

/**
 * Block reason row component.
 */
function BlockReasonRow({ block }: { block: GovernanceBlockReason }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-rose-500/5 border border-rose-500/20">
      <XCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <code className="text-xs font-mono text-rose-300 bg-rose-500/20 px-1.5 py-0.5 rounded">
            {block.rule_code}
          </code>
          <span className="text-xs text-slate-500">
            by {block.triggered_by_gid}
          </span>
        </div>
        <p className="text-sm text-rose-200">{block.reason}</p>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>{new Date(block.blocked_at).toLocaleString()}</span>
          <code className="text-slate-600">{block.correlation_id}</code>
        </div>
      </div>
    </div>
  );
}

/**
 * Escalation row component.
 */
function EscalationRow({ escalation }: { escalation: GovernanceEscalation }) {
  const levelConfig = ESCALATION_CONFIG[escalation.level];
  
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
      <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={classNames('text-xs font-semibold', levelConfig.color)}>
            {levelConfig.label}
          </span>
          <span className="text-xs text-slate-500">
            {escalation.from_gid} → {escalation.to_gid}
          </span>
          <span className={classNames(
            'text-xs px-1.5 py-0.5 rounded',
            escalation.status === 'PENDING' 
              ? 'bg-amber-500/20 text-amber-300'
              : escalation.status === 'RESOLVED'
                ? 'bg-emerald-500/20 text-emerald-300'
                : 'bg-slate-500/20 text-slate-300'
          )}>
            {escalation.status}
          </span>
        </div>
        <p className="text-sm text-amber-200">{escalation.reason}</p>
        <div className="text-xs text-slate-500">
          {new Date(escalation.escalated_at).toLocaleString()}
        </div>
      </div>
    </div>
  );
}

/**
 * Governance State Panel Props.
 */
export interface GovernanceStatePanelProps {
  /** Compact mode for embedded views */
  compact?: boolean;
  /** Additional className */
  className?: string;
}

/**
 * Governance State Panel Component.
 */
export function GovernanceStatePanel({ 
  compact = false,
  className,
}: GovernanceStatePanelProps) {
  const {
    context,
    isLoading,
    error,
    state,
    escalationLevel,
    isBlocked,
    hasEscalation,
    actionsEnabled,
    refresh,
  } = useGovernanceState();

  const [expanded, setExpanded] = useState(!compact);
  const config = STATE_CONFIG[state];
  const Icon = config.icon;

  // Loading state
  if (isLoading && !context) {
    return (
      <div className={classNames(
        'rounded-lg border border-slate-700/50 bg-slate-800/30 p-4',
        className
      )}>
        <div className="flex items-center gap-3">
          <div className="h-6 w-6 rounded-full bg-slate-700 animate-pulse" />
          <div className="h-4 w-32 rounded bg-slate-700 animate-pulse" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={classNames(
        'rounded-lg border border-rose-500/40 bg-rose-500/10 p-4',
        className
      )}>
        <div className="flex items-center gap-3">
          <XCircle className="h-6 w-6 text-rose-400" />
          <div>
            <p className="text-sm font-medium text-rose-300">Governance State Error</p>
            <p className="text-xs text-rose-400">{error.message}</p>
          </div>
          <button
            onClick={refresh}
            className="ml-auto p-2 rounded-lg hover:bg-rose-500/20 transition-colors"
          >
            <RefreshCw className="h-4 w-4 text-rose-400" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={classNames(
      'rounded-lg border transition-colors',
      config.bg,
      config.border,
      className
    )}>
      {/* Header */}
      <div 
        className="flex items-center gap-3 p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <Icon className={classNames('h-6 w-6', config.text)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={classNames('text-sm font-semibold uppercase tracking-wider', config.text)}>
              {config.label}
            </span>
            {hasEscalation && (
              <span className={classNames(
                'text-xs px-1.5 py-0.5 rounded',
                ESCALATION_CONFIG[escalationLevel].color,
                'bg-slate-800/50'
              )}>
                {ESCALATION_CONFIG[escalationLevel].label}
              </span>
            )}
          </div>
          {!compact && (
            <p className="text-xs text-slate-400 mt-0.5">{config.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!actionsEnabled && (
            <span className="text-xs px-2 py-1 rounded bg-rose-500/20 text-rose-300">
              ACTIONS DISABLED
            </span>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              refresh();
            }}
            className="p-1.5 rounded hover:bg-slate-700/50 transition-colors"
            title="Refresh governance state"
          >
            <RefreshCw className={classNames(
              'h-4 w-4 text-slate-400',
              isLoading && 'animate-spin'
            )} />
          </button>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && context && (
        <div className="border-t border-slate-700/30 p-4 space-y-4">
          {/* Active Blocks */}
          {context.active_blocks.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-400">
                Active Blocks ({context.active_blocks.length})
              </h4>
              <div className="space-y-2">
                {context.active_blocks.map((block, idx) => (
                  <BlockReasonRow key={idx} block={block} />
                ))}
              </div>
            </div>
          )}

          {/* Pending Escalations */}
          {context.pending_escalations.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-400">
                Pending Escalations ({context.pending_escalations.length})
              </h4>
              <div className="space-y-2">
                {context.pending_escalations.map((esc) => (
                  <EscalationRow key={esc.escalation_id} escalation={esc} />
                ))}
              </div>
            </div>
          )}

          {/* Active PACs */}
          {context.active_pacs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Active PACs ({context.active_pacs.length})
              </h4>
              <div className="space-y-1">
                {context.active_pacs.map((pac) => (
                  <div 
                    key={pac.pac_id}
                    className="flex items-center gap-2 text-xs text-slate-300 p-2 rounded bg-slate-800/30"
                  >
                    <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                    <code className="font-mono text-slate-400">{pac.pac_id}</code>
                    <span className="text-slate-500">— {pac.owner_gid}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* System Health */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-700/30">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>Last sync:</span>
              <span>{new Date(context.last_sync).toLocaleTimeString()}</span>
            </div>
            <div className={classNames(
              'flex items-center gap-1.5 text-xs',
              context.system_healthy ? 'text-emerald-400' : 'text-rose-400'
            )}>
              <span className={classNames(
                'w-2 h-2 rounded-full',
                context.system_healthy ? 'bg-emerald-400' : 'bg-rose-400 animate-pulse'
              )} />
              {context.system_healthy ? 'System Healthy' : 'System Degraded'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact governance state indicator for header bars.
 */
export function GovernanceStateIndicator() {
  const { state, isBlocked, hasEscalation, escalationLevel } = useGovernanceState();
  const config = STATE_CONFIG[state];
  const Icon = config.icon;

  return (
    <div className={classNames(
      'flex items-center gap-2 px-3 py-1.5 rounded-lg border',
      config.bg,
      config.border
    )}>
      <Icon className={classNames('h-4 w-4', config.text)} />
      <span className={classNames('text-xs font-semibold uppercase', config.text)}>
        {isBlocked ? 'BLOCKED' : state}
      </span>
      {hasEscalation && (
        <span className={classNames(
          'text-xs px-1 rounded',
          ESCALATION_CONFIG[escalationLevel].color,
          'bg-slate-800/50'
        )}>
          {escalationLevel}
        </span>
      )}
    </div>
  );
}
