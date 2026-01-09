/**
 * GIE Checkpoint Timeline Component
 * 
 * Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
 * Agent: GID-02 (Sonny) — Frontend / Operator Console
 * 
 * REAL WORK MODE — Production-grade checkpoint visualization.
 * 
 * Features:
 * - Visual checkpoint timeline
 * - WRAP hash display
 * - Agent state tracking
 * - Read-only mode
 */

import React, { useMemo, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type CheckpointType = 
  | 'PAC_STARTED'
  | 'AGENT_DISPATCHED'
  | 'AGENT_STARTED'
  | 'WRAP_RECEIVED'
  | 'ALL_WRAPS_RECEIVED'
  | 'BER_ISSUED'
  | 'PDO_SEALED'
  | 'SESSION_COMPLETE'
  | 'ERROR';

export type AgentState = 
  | 'PENDING'
  | 'DISPATCHED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED';

export interface Checkpoint {
  id: string;
  type: CheckpointType;
  timestamp: string;
  agentGid?: string;
  wrapHash?: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface AgentStatus {
  gid: string;
  name: string;
  lane: string;
  state: AgentState;
  startedAt?: string;
  completedAt?: string;
  wrapHash?: string;
  taskName?: string;
}

export interface TimelineProps {
  pacId: string;
  checkpoints: Checkpoint[];
  agents: AgentStatus[];
  currentPhase: string;
  isComplete: boolean;
  onCheckpointClick?: (checkpoint: Checkpoint) => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const CHECKPOINT_COLORS: Record<CheckpointType, string> = {
  PAC_STARTED: '#3B82F6',       // blue
  AGENT_DISPATCHED: '#8B5CF6',  // purple
  AGENT_STARTED: '#F59E0B',     // amber
  WRAP_RECEIVED: '#10B981',     // emerald
  ALL_WRAPS_RECEIVED: '#059669', // darker emerald
  BER_ISSUED: '#6366F1',        // indigo
  PDO_SEALED: '#14B8A6',        // teal
  SESSION_COMPLETE: '#22C55E',  // green
  ERROR: '#EF4444',             // red
};

const AGENT_STATE_COLORS: Record<AgentState, string> = {
  PENDING: '#9CA3AF',    // gray
  DISPATCHED: '#8B5CF6', // purple
  RUNNING: '#F59E0B',    // amber
  COMPLETED: '#10B981',  // emerald
  FAILED: '#EF4444',     // red
};

const CHECKPOINT_ICONS: Record<CheckpointType, string> = {
  PAC_STARTED: '🚀',
  AGENT_DISPATCHED: '📤',
  AGENT_STARTED: '⏳',
  WRAP_RECEIVED: '📦',
  ALL_WRAPS_RECEIVED: '✅',
  BER_ISSUED: '📋',
  PDO_SEALED: '🔒',
  SESSION_COMPLETE: '🎉',
  ERROR: '❌',
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface CheckpointNodeProps {
  checkpoint: Checkpoint;
  isLast: boolean;
  onClick?: () => void;
}

const CheckpointNode: React.FC<CheckpointNodeProps> = ({
  checkpoint,
  isLast,
  onClick,
}) => {
  const color = CHECKPOINT_COLORS[checkpoint.type];
  const icon = CHECKPOINT_ICONS[checkpoint.type];
  
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const truncateHash = (hash?: string): string => {
    if (!hash) return '';
    if (hash.length <= 20) return hash;
    return `${hash.slice(0, 12)}...${hash.slice(-8)}`;
  };

  return (
    <div 
      className="checkpoint-node"
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        marginBottom: isLast ? 0 : '16px',
        cursor: onClick ? 'pointer' : 'default',
      }}
      role="listitem"
      aria-label={`Checkpoint: ${checkpoint.type}`}
    >
      {/* Timeline connector */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          marginRight: '12px',
        }}
      >
        {/* Node dot */}
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            flexShrink: 0,
          }}
          title={checkpoint.type}
        >
          {icon}
        </div>
        
        {/* Connector line */}
        {!isLast && (
          <div
            style={{
              width: '2px',
              flexGrow: 1,
              minHeight: '24px',
              backgroundColor: '#E5E7EB',
            }}
          />
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, paddingTop: '4px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span
            style={{
              fontWeight: 600,
              color: '#1F2937',
              fontSize: '14px',
            }}
          >
            {checkpoint.type.replace(/_/g, ' ')}
          </span>
          <span
            style={{
              fontSize: '12px',
              color: '#6B7280',
              fontFamily: 'monospace',
            }}
          >
            {formatTime(checkpoint.timestamp)}
          </span>
        </div>

        <p
          style={{
            margin: '4px 0 0 0',
            color: '#4B5563',
            fontSize: '13px',
          }}
        >
          {checkpoint.message}
        </p>

        {checkpoint.agentGid && (
          <span
            style={{
              display: 'inline-block',
              marginTop: '4px',
              padding: '2px 8px',
              backgroundColor: '#E0E7FF',
              borderRadius: '4px',
              fontSize: '12px',
              color: '#4338CA',
              fontFamily: 'monospace',
            }}
          >
            {checkpoint.agentGid}
          </span>
        )}

        {checkpoint.wrapHash && (
          <div
            style={{
              marginTop: '4px',
              padding: '4px 8px',
              backgroundColor: '#F3F4F6',
              borderRadius: '4px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: '#374151',
            }}
            title={checkpoint.wrapHash}
          >
            WRAP: {truncateHash(checkpoint.wrapHash)}
          </div>
        )}
      </div>
    </div>
  );
};

interface AgentCardProps {
  agent: AgentStatus;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent }) => {
  const stateColor = AGENT_STATE_COLORS[agent.state];
  
  const truncateHash = (hash?: string): string => {
    if (!hash) return '—';
    if (hash.length <= 16) return hash;
    return `${hash.slice(0, 10)}...${hash.slice(-6)}`;
  };

  return (
    <div
      className="agent-card"
      style={{
        padding: '12px',
        backgroundColor: '#FFFFFF',
        border: '1px solid #E5E7EB',
        borderRadius: '8px',
        borderLeft: `4px solid ${stateColor}`,
      }}
      role="article"
      aria-label={`Agent ${agent.gid}`}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
        }}
      >
        <span
          style={{
            fontWeight: 600,
            color: '#1F2937',
            fontSize: '14px',
          }}
        >
          {agent.gid}
        </span>
        <span
          style={{
            padding: '2px 8px',
            backgroundColor: stateColor,
            color: '#FFFFFF',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 500,
          }}
        >
          {agent.state}
        </span>
      </div>

      <div style={{ fontSize: '13px', color: '#4B5563' }}>
        <div style={{ marginBottom: '4px' }}>
          <strong>Name:</strong> {agent.name}
        </div>
        <div style={{ marginBottom: '4px' }}>
          <strong>Lane:</strong> {agent.lane}
        </div>
        {agent.taskName && (
          <div style={{ marginBottom: '4px' }}>
            <strong>Task:</strong> {agent.taskName}
          </div>
        )}
        {agent.wrapHash && (
          <div
            style={{
              marginTop: '8px',
              padding: '4px 8px',
              backgroundColor: '#ECFDF5',
              borderRadius: '4px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: '#065F46',
            }}
            title={agent.wrapHash}
          >
            {truncateHash(agent.wrapHash)}
          </div>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const GIECheckpointTimeline: React.FC<TimelineProps> = ({
  pacId,
  checkpoints,
  agents,
  currentPhase,
  isComplete,
  onCheckpointClick,
}) => {
  // Sort checkpoints by timestamp
  const sortedCheckpoints = useMemo(() => {
    return [...checkpoints].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [checkpoints]);

  // Compute progress
  const progress = useMemo(() => {
    const completed = agents.filter(a => a.state === 'COMPLETED').length;
    return agents.length > 0 ? (completed / agents.length) * 100 : 0;
  }, [agents]);

  // Count WRAPs received
  const wrapsReceived = useMemo(() => {
    return checkpoints.filter(c => c.type === 'WRAP_RECEIVED').length;
  }, [checkpoints]);

  const handleCheckpointClick = useCallback(
    (checkpoint: Checkpoint) => {
      if (onCheckpointClick) {
        onCheckpointClick(checkpoint);
      }
    },
    [onCheckpointClick]
  );

  return (
    <div
      className="gie-checkpoint-timeline"
      style={{
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#F9FAFB',
        borderRadius: '12px',
        padding: '24px',
      }}
      role="region"
      aria-label="GIE Checkpoint Timeline"
    >
      {/* Header */}
      <header
        style={{
          marginBottom: '24px',
          borderBottom: '1px solid #E5E7EB',
          paddingBottom: '16px',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: '18px',
              fontWeight: 600,
              color: '#111827',
            }}
          >
            {pacId}
          </h2>
          <span
            style={{
              padding: '4px 12px',
              backgroundColor: isComplete ? '#DCFCE7' : '#FEF3C7',
              color: isComplete ? '#166534' : '#92400E',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 500,
            }}
          >
            {currentPhase}
          </span>
        </div>

        {/* Progress bar */}
        <div
          style={{
            marginTop: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              flex: 1,
              height: '8px',
              backgroundColor: '#E5E7EB',
              borderRadius: '4px',
              overflow: 'hidden',
            }}
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              style={{
                width: `${progress}%`,
                height: '100%',
                backgroundColor: isComplete ? '#22C55E' : '#3B82F6',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <span style={{ fontSize: '13px', color: '#6B7280' }}>
            {wrapsReceived}/{agents.length} WRAPs
          </span>
        </div>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 300px',
          gap: '24px',
        }}
      >
        {/* Timeline */}
        <section>
          <h3
            style={{
              margin: '0 0 16px 0',
              fontSize: '14px',
              fontWeight: 600,
              color: '#374151',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Checkpoints
          </h3>
          <div role="list" aria-label="Checkpoint list">
            {sortedCheckpoints.length === 0 ? (
              <p style={{ color: '#9CA3AF', fontStyle: 'italic' }}>
                No checkpoints yet
              </p>
            ) : (
              sortedCheckpoints.map((checkpoint, index) => (
                <CheckpointNode
                  key={checkpoint.id}
                  checkpoint={checkpoint}
                  isLast={index === sortedCheckpoints.length - 1}
                  onClick={
                    onCheckpointClick
                      ? () => handleCheckpointClick(checkpoint)
                      : undefined
                  }
                />
              ))
            )}
          </div>
        </section>

        {/* Agent Status Panel */}
        <aside>
          <h3
            style={{
              margin: '0 0 16px 0',
              fontSize: '14px',
              fontWeight: 600,
              color: '#374151',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Agents ({agents.length})
          </h3>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {agents.map(agent => (
              <AgentCard key={agent.gid} agent={agent} />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default GIECheckpointTimeline;
