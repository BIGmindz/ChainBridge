/**
 * GIE Timeline Component
 * 
 * Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
 * Agent: GID-02 (Sonny) — Senior Frontend Engineer
 * 
 * Features:
 * - Visual checkpoint markers
 * - Agent state timeline (READ-ONLY)
 * - Telemetry stream visualization
 */

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type AgentStatus = 
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'SKIPPED';

export type CheckpointType =
  | 'PAC_RECEIVED'
  | 'AGENTS_DISPATCHED'
  | 'AGENT_STARTED'
  | 'AGENT_COMPLETED'
  | 'WRAP_HASH_RECEIVED'
  | 'ALL_WRAPS_RECEIVED'
  | 'BER_ISSUED'
  | 'PDO_EMITTED'
  | 'ERROR_SIGNAL';

export interface AgentState {
  gid: string;
  name: string;
  role: string;
  status: AgentStatus;
  startedAt?: string;
  completedAt?: string;
  wrapHash?: string;
  testCount?: number;
  errorMessage?: string;
}

export interface Checkpoint {
  id: string;
  type: CheckpointType;
  message: string;
  timestamp: string;
  agentGid?: string;
  hashRef?: string;
}

export interface TimelineEntry {
  timestamp: string;
  type: 'checkpoint' | 'agent_update';
  checkpoint?: Checkpoint;
  agentState?: AgentState;
}

export interface GIETimelineProps {
  /** PAC ID being executed */
  pacId: string;
  /** List of agents in execution */
  agents: AgentState[];
  /** Checkpoint events */
  checkpoints: Checkpoint[];
  /** Timeline entries (combined view) */
  entries?: TimelineEntry[];
  /** Current phase label */
  phase?: string;
  /** Read-only mode (default: true) */
  readOnly?: boolean;
  /** Max visible checkpoints */
  maxVisible?: number;
  /** Callback when checkpoint clicked */
  onCheckpointClick?: (checkpoint: Checkpoint) => void;
  /** Custom class name */
  className?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_COLORS: Record<AgentStatus, string> = {
  PENDING: '#9CA3AF',   // gray-400
  RUNNING: '#3B82F6',   // blue-500
  COMPLETED: '#10B981', // green-500
  FAILED: '#EF4444',    // red-500
  SKIPPED: '#6B7280',   // gray-500
};

const STATUS_ICONS: Record<AgentStatus, string> = {
  PENDING: '⏸',
  RUNNING: '⏳',
  COMPLETED: '✓',
  FAILED: '✗',
  SKIPPED: '⊘',
};

const CHECKPOINT_ICONS: Record<CheckpointType, string> = {
  PAC_RECEIVED: '🟦',
  AGENTS_DISPATCHED: '🚀',
  AGENT_STARTED: '⏳',
  AGENT_COMPLETED: '✓',
  WRAP_HASH_RECEIVED: '📦',
  ALL_WRAPS_RECEIVED: '📦📦',
  BER_ISSUED: '🟩',
  PDO_EMITTED: '🧿',
  ERROR_SIGNAL: '🔴',
};

const CHECKPOINT_COLORS: Record<CheckpointType, string> = {
  PAC_RECEIVED: '#3B82F6',
  AGENTS_DISPATCHED: '#8B5CF6',
  AGENT_STARTED: '#F59E0B',
  AGENT_COMPLETED: '#10B981',
  WRAP_HASH_RECEIVED: '#6366F1',
  ALL_WRAPS_RECEIVED: '#6366F1',
  BER_ISSUED: '#10B981',
  PDO_EMITTED: '#06B6D4',
  ERROR_SIGNAL: '#EF4444',
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface AgentCardProps {
  agent: AgentState;
  isActive?: boolean;
}

export const AgentCard: React.FC<AgentCardProps> = ({ agent, isActive }) => {
  const statusColor = STATUS_COLORS[agent.status];
  const statusIcon = STATUS_ICONS[agent.status];
  
  return (
    <div
      className={`agent-card ${isActive ? 'active' : ''}`}
      style={{
        borderLeft: `4px solid ${statusColor}`,
        backgroundColor: isActive ? `${statusColor}15` : 'transparent',
        padding: '12px',
        borderRadius: '8px',
        marginBottom: '8px',
        transition: 'all 0.2s ease',
      }}
      data-testid={`agent-card-${agent.gid}`}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontWeight: 600, color: '#111827' }}>
            {agent.gid}
          </span>
          <span style={{ marginLeft: '8px', color: '#6B7280', fontSize: '14px' }}>
            {agent.name}
          </span>
        </div>
        <span style={{ color: statusColor, fontSize: '18px' }}>
          {statusIcon}
        </span>
      </div>
      
      <div style={{ fontSize: '12px', color: '#9CA3AF', marginTop: '4px' }}>
        {agent.role}
      </div>
      
      {agent.wrapHash && (
        <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '4px', fontFamily: 'monospace' }}>
          WRAP: {truncateHash(agent.wrapHash)}
        </div>
      )}
      
      {agent.testCount !== undefined && agent.status === 'COMPLETED' && (
        <div style={{ fontSize: '12px', color: '#10B981', marginTop: '4px' }}>
          {agent.testCount} tests passed
        </div>
      )}
      
      {agent.errorMessage && (
        <div style={{ fontSize: '12px', color: '#EF4444', marginTop: '4px' }}>
          Error: {agent.errorMessage}
        </div>
      )}
    </div>
  );
};

interface CheckpointMarkerProps {
  checkpoint: Checkpoint;
  onClick?: () => void;
}

export const CheckpointMarker: React.FC<CheckpointMarkerProps> = ({ checkpoint, onClick }) => {
  const icon = CHECKPOINT_ICONS[checkpoint.type];
  const color = CHECKPOINT_COLORS[checkpoint.type];
  
  return (
    <div
      className="checkpoint-marker"
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        padding: '8px 12px',
        borderLeft: `3px solid ${color}`,
        backgroundColor: `${color}10`,
        borderRadius: '0 8px 8px 0',
        marginBottom: '4px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background-color 0.2s ease',
      }}
      data-testid={`checkpoint-${checkpoint.id}`}
    >
      <span style={{ marginRight: '8px', fontSize: '16px' }}>{icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '13px', fontWeight: 500, color: '#374151' }}>
          {checkpoint.type.replace(/_/g, ' ')}
        </div>
        <div style={{ fontSize: '12px', color: '#6B7280' }}>
          {checkpoint.message}
        </div>
        {checkpoint.hashRef && (
          <div style={{ fontSize: '11px', color: '#9CA3AF', fontFamily: 'monospace', marginTop: '2px' }}>
            {truncateHash(checkpoint.hashRef)}
          </div>
        )}
      </div>
      <div style={{ fontSize: '11px', color: '#9CA3AF' }}>
        {formatTime(checkpoint.timestamp)}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function truncateHash(hash: string, maxLength: number = 16): string {
  if (!hash) return '';
  if (hash.length <= maxLength) return hash;
  
  // Handle prefixed hashes like "sha256:abc..."
  if (hash.includes(':')) {
    const [prefix, value] = hash.split(':');
    if (value.length > maxLength - prefix.length - 1) {
      return `${prefix}:${value.slice(0, maxLength - prefix.length - 4)}...`;
    }
    return hash;
  }
  
  return `${hash.slice(0, maxLength - 3)}...`;
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return timestamp;
  }
}

function calculateProgress(agents: AgentState[]): number {
  if (agents.length === 0) return 0;
  const completed = agents.filter(a => a.status === 'COMPLETED' || a.status === 'FAILED').length;
  return Math.round((completed / agents.length) * 100);
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const GIETimeline: React.FC<GIETimelineProps> = ({
  pacId,
  agents,
  checkpoints,
  entries,
  phase = 'EXECUTING',
  readOnly = true,
  maxVisible = 50,
  onCheckpointClick,
  className = '',
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  
  // Calculate derived state
  const progress = useMemo(() => calculateProgress(agents), [agents]);
  const runningAgents = useMemo(
    () => agents.filter(a => a.status === 'RUNNING'),
    [agents]
  );
  const completedCount = useMemo(
    () => agents.filter(a => a.status === 'COMPLETED').length,
    [agents]
  );
  const visibleCheckpoints = useMemo(
    () => checkpoints.slice(-maxVisible),
    [checkpoints, maxVisible]
  );
  
  // Auto-scroll to bottom on new checkpoints
  useEffect(() => {
    if (autoScroll && timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight;
    }
  }, [checkpoints.length, autoScroll]);
  
  // Handle scroll to detect manual scrolling
  const handleScroll = useCallback(() => {
    if (!timelineRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = timelineRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  }, []);
  
  const handleCheckpointClick = useCallback((checkpoint: Checkpoint) => {
    if (onCheckpointClick && !readOnly) {
      onCheckpointClick(checkpoint);
    }
  }, [onCheckpointClick, readOnly]);

  return (
    <div
      className={`gie-timeline ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#FAFAFA',
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid #E5E7EB',
      }}
      data-testid="gie-timeline"
    >
      {/* Header */}
      <div
        style={{
          padding: '16px',
          borderBottom: '1px solid #E5E7EB',
          backgroundColor: '#FFFFFF',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#111827' }}>
              GIE Execution Timeline
            </h3>
            <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px' }}>
              {pacId}
            </div>
          </div>
          <div
            style={{
              padding: '4px 12px',
              borderRadius: '16px',
              backgroundColor: phase === 'COMPLETE' ? '#D1FAE5' : '#DBEAFE',
              color: phase === 'COMPLETE' ? '#065F46' : '#1E40AF',
              fontSize: '12px',
              fontWeight: 500,
            }}
            data-testid="phase-badge"
          >
            {phase}
          </div>
        </div>
        
        {/* Progress Bar */}
        <div style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6B7280', marginBottom: '4px' }}>
            <span>Progress</span>
            <span>{completedCount}/{agents.length} agents</span>
          </div>
          <div
            style={{
              height: '6px',
              backgroundColor: '#E5E7EB',
              borderRadius: '3px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progress}%`,
                backgroundColor: '#10B981',
                borderRadius: '3px',
                transition: 'width 0.3s ease',
              }}
              data-testid="progress-bar"
            />
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Agent Panel */}
        <div
          style={{
            width: '280px',
            borderRight: '1px solid #E5E7EB',
            padding: '12px',
            overflowY: 'auto',
            backgroundColor: '#FFFFFF',
          }}
          data-testid="agent-panel"
        >
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#6B7280', marginBottom: '8px', textTransform: 'uppercase' }}>
            Agents ({agents.length})
          </div>
          {agents.map(agent => (
            <AgentCard
              key={agent.gid}
              agent={agent}
              isActive={runningAgents.some(a => a.gid === agent.gid)}
            />
          ))}
        </div>
        
        {/* Checkpoint Stream */}
        <div
          ref={timelineRef}
          onScroll={handleScroll}
          style={{
            flex: 1,
            padding: '12px',
            overflowY: 'auto',
          }}
          data-testid="checkpoint-stream"
        >
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#6B7280', marginBottom: '8px', textTransform: 'uppercase' }}>
            Checkpoints ({checkpoints.length})
          </div>
          {visibleCheckpoints.map(checkpoint => (
            <CheckpointMarker
              key={checkpoint.id}
              checkpoint={checkpoint}
              onClick={() => handleCheckpointClick(checkpoint)}
            />
          ))}
          
          {checkpoints.length === 0 && (
            <div style={{ textAlign: 'center', padding: '24px', color: '#9CA3AF', fontSize: '14px' }}>
              Awaiting checkpoints...
            </div>
          )}
          
          {checkpoints.length > maxVisible && (
            <div style={{ textAlign: 'center', padding: '8px', color: '#9CA3AF', fontSize: '12px' }}>
              Showing last {maxVisible} of {checkpoints.length} checkpoints
            </div>
          )}
        </div>
      </div>
      
      {/* Footer */}
      <div
        style={{
          padding: '8px 16px',
          borderTop: '1px solid #E5E7EB',
          backgroundColor: '#FFFFFF',
          fontSize: '11px',
          color: '#9CA3AF',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>
          {readOnly && '🔒 Read-only view'}
        </span>
        <span>
          {autoScroll ? '⬇ Auto-scrolling' : '⏸ Scroll paused'}
        </span>
      </div>
    </div>
  );
};

// Default export
export default GIETimeline;
