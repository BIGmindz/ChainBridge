/**
 * ChainBridge Agent State Badges
 * PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
 * 
 * Reusable state badges for agent execution states.
 * 
 * INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
 */

import React from 'react';
import type { AgentState } from '../types/agentExecution';
import { STATE_COLORS, STATE_LABELS } from '../types/agentExecution';

export interface StateBadgeProps {
  state: AgentState;
  size?: 'sm' | 'md' | 'lg';
  showPulse?: boolean;
}

/**
 * Agent state badge with optional pulse animation for ACTIVE state
 */
export const StateBadge: React.FC<StateBadgeProps> = ({
  state,
  size = 'md',
  showPulse = true,
}) => {
  const colorClass = STATE_COLORS[state] || 'bg-gray-500';
  const label = STATE_LABELS[state] || state;
  
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5',
  };
  
  const isActive = state === 'ACTIVE';
  
  return (
    <span
      className={`
        inline-flex items-center gap-1
        ${colorClass} text-white rounded-full font-medium
        ${sizeClasses[size]}
      `}
    >
      {/* Pulse indicator for active state */}
      {isActive && showPulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
        </span>
      )}
      {label}
    </span>
  );
};

export interface StateCountBadgeProps {
  queued: number;
  active: number;
  complete: number;
  failed: number;
}

/**
 * Summary badge showing counts for each state
 */
export const StateCountBadge: React.FC<StateCountBadgeProps> = ({
  queued,
  active,
  complete,
  failed,
}) => {
  return (
    <div className="flex items-center gap-2 text-xs">
      {queued > 0 && (
        <span className="bg-gray-500 text-white px-2 py-0.5 rounded-full">
          {queued} queued
        </span>
      )}
      {active > 0 && (
        <span className="bg-blue-500 text-white px-2 py-0.5 rounded-full flex items-center gap-1">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-white" />
          </span>
          {active} active
        </span>
      )}
      {complete > 0 && (
        <span className="bg-green-500 text-white px-2 py-0.5 rounded-full">
          {complete} complete
        </span>
      )}
      {failed > 0 && (
        <span className="bg-red-500 text-white px-2 py-0.5 rounded-full">
          {failed} failed
        </span>
      )}
    </div>
  );
};

export interface ExecutionStatusBadgeProps {
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED';
}

/**
 * Overall execution status badge
 */
export const ExecutionStatusBadge: React.FC<ExecutionStatusBadgeProps> = ({ status }) => {
  const statusConfig = {
    PENDING: { color: 'bg-gray-400', label: 'Pending' },
    IN_PROGRESS: { color: 'bg-blue-500', label: 'In Progress' },
    COMPLETE: { color: 'bg-green-500', label: 'Complete' },
    FAILED: { color: 'bg-red-500', label: 'Failed' },
  };
  
  const config = statusConfig[status] || statusConfig.PENDING;
  const isInProgress = status === 'IN_PROGRESS';
  
  return (
    <span
      className={`
        inline-flex items-center gap-1.5
        ${config.color} text-white text-xs px-2 py-1 rounded-full font-medium
      `}
    >
      {isInProgress && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
        </span>
      )}
      {config.label}
    </span>
  );
};

export default StateBadge;
