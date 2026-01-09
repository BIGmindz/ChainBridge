/**
 * ChainBridge Agent Execution Timeline
 * PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
 * 
 * Timeline visualization of agent execution events.
 * 
 * INVARIANTS:
 * - INV-AGENT-001: Agent activation must be explicit and visible
 * - INV-AGENT-002: Each execution step maps to exactly one agent
 * - INV-AGENT-004: OC is read-only; no agent control actions
 */

import React from 'react';
import type { AgentTimelineEvent } from '../types/agentExecution';
import {
  STATE_COLORS,
  AGENT_COLOR_MAP,
  formatTimestamp,
  UNAVAILABLE_MARKER,
} from '../types/agentExecution';

/**
 * Timeline event type icons
 */
const EVENT_ICONS: Record<string, string> = {
  ACTIVATION: '🚀',
  STATE_CHANGE: '🔄',
  ARTIFACT_CREATED: '📄',
};

/**
 * Timeline event row component
 */
const TimelineEventRow: React.FC<{ event: AgentTimelineEvent; isLast: boolean }> = ({
  event,
  isLast,
}) => {
  const icon = EVENT_ICONS[event.event_type] || '•';
  const stateColor = event.new_state
    ? STATE_COLORS[event.new_state as keyof typeof STATE_COLORS]
    : null;
  
  return (
    <div className="flex gap-3">
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center text-lg">
          {icon}
        </div>
        {!isLast && (
          <div className="w-0.5 h-full bg-gray-200 my-1" style={{ minHeight: '24px' }} />
        )}
      </div>
      
      {/* Event content */}
      <div className="flex-1 pb-4">
        <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
          {/* Header */}
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900">{event.agent_name}</span>
              <span className="text-xs text-gray-500">({event.agent_gid})</span>
            </div>
            <span className="text-xs text-gray-400">
              {formatTimestamp(event.timestamp)}
            </span>
          </div>
          
          {/* Description */}
          <div className="text-sm text-gray-700">{event.description}</div>
          
          {/* State transition (if applicable) */}
          {event.event_type === 'STATE_CHANGE' && event.previous_state && event.new_state && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <span className="text-gray-500">{event.previous_state}</span>
              <span className="text-gray-400">→</span>
              {stateColor && (
                <span className={`${stateColor} text-white px-2 py-0.5 rounded-full`}>
                  {event.new_state}
                </span>
              )}
            </div>
          )}
          
          {/* Ledger hash */}
          {event.ledger_entry_hash !== UNAVAILABLE_MARKER && (
            <div className="mt-2 text-xs text-gray-400 font-mono truncate">
              {event.ledger_entry_hash.substring(0, 24)}...
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Agent Execution Timeline Component
 */
export interface AgentTimelineProps {
  events: AgentTimelineEvent[];
  title?: string;
  emptyMessage?: string;
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({
  events,
  title = 'Execution Timeline',
  emptyMessage = 'No execution events recorded.',
}) => {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <span className="text-xs text-gray-500">
          {events.length} event{events.length !== 1 ? 's' : ''}
        </span>
      </div>
      
      {/* Timeline */}
      {events.length === 0 ? (
        <div className="text-center py-8 text-gray-500">{emptyMessage}</div>
      ) : (
        <div className="space-y-0">
          {events.map((event, idx) => (
            <TimelineEventRow
              key={event.event_id}
              event={event}
              isLast={idx === events.length - 1}
            />
          ))}
        </div>
      )}
      
      {/* Footer */}
      <div className="mt-4 text-xs text-gray-400 text-center">
        INV-AGENT-001: Agent activation is explicit and visible
      </div>
    </div>
  );
};

export default AgentTimeline;
