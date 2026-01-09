/**
 * PDOTimelineView — Operator Console PDO Timeline Component
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI
 * Effective Date: 2025-12-30
 * 
 * INVARIANTS:
 *   INV-OC-001: UI may not mutate PDO or settlement state
 *   INV-OC-003: Ledger hash visible for final outcomes
 *   INV-OC-004: Missing data explicit (shows UNAVAILABLE)
 */

import React, { useEffect, useState } from 'react';
import type {
  OCTimelineEvent,
  OCTimelineResponse,
} from '../types/operatorConsole';
import { UNAVAILABLE_MARKER } from '../types/operatorConsole';
import { fetchPDOTimeline, fetchSettlementTimeline } from '../api/operatorConsole';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface PDOTimelineViewProps {
  pdoId?: string | null;
  settlementId?: string | null;
  className?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// EVENT TYPE STYLING
// ═══════════════════════════════════════════════════════════════════════════════

const EVENT_TYPE_STYLES: Record<string, { icon: string; color: string; bg: string }> = {
  PDO_CREATED: { icon: '📄', color: 'text-blue-700', bg: 'bg-blue-100' },
  PDO_UPDATED: { icon: '✏️', color: 'text-blue-600', bg: 'bg-blue-50' },
  SETTLEMENT_INITIATED: { icon: '🚀', color: 'text-green-700', bg: 'bg-green-100' },
  MILESTONE_STARTED: { icon: '▶️', color: 'text-amber-700', bg: 'bg-amber-100' },
  MILESTONE_COMPLETED: { icon: '✅', color: 'text-green-700', bg: 'bg-green-100' },
  SETTLEMENT_COMPLETED: { icon: '🏁', color: 'text-green-800', bg: 'bg-green-200' },
  SETTLEMENT_LEDGER_ENTRY: { icon: '📒', color: 'text-purple-700', bg: 'bg-purple-100' },
  LEDGER_ENTRY: { icon: '📝', color: 'text-slate-700', bg: 'bg-slate-100' },
};

const getEventStyle = (eventType: string) => {
  return EVENT_TYPE_STYLES[eventType] || { icon: '•', color: 'text-slate-600', bg: 'bg-slate-50' };
};

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE EVENT ITEM
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineEventItemProps {
  event: OCTimelineEvent;
  isFirst: boolean;
  isLast: boolean;
}

const TimelineEventItem: React.FC<TimelineEventItemProps> = ({ event, isFirst, isLast }) => {
  const style = getEventStyle(event.event_type);
  const isHashUnavailable = event.ledger_hash === UNAVAILABLE_MARKER || event.ledger_hash === 'UNAVAILABLE';
  
  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        {/* Dot */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${style.bg}`}>
          <span>{style.icon}</span>
        </div>
        {/* Line */}
        {!isLast && (
          <div className="w-0.5 flex-1 bg-slate-200 mt-2" />
        )}
      </div>
      
      {/* Content */}
      <div className="flex-1 pb-6">
        {/* Event type and timestamp */}
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${style.color}`}>
            {event.event_type.replace(/_/g, ' ')}
          </span>
          <span className="text-xs text-slate-400">
            {new Date(event.timestamp).toLocaleString()}
          </span>
        </div>
        
        {/* Event ID */}
        <div className="text-xs text-slate-500 font-mono mt-1">
          {event.event_id}
        </div>
        
        {/* Ledger Hash (INV-OC-003: Must be visible) */}
        <div className="mt-2">
          {isHashUnavailable ? (
            <span className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded">
              Ledger Hash: UNAVAILABLE
            </span>
          ) : (
            <span
              className="text-xs font-mono text-slate-500 px-2 py-1 bg-slate-100 rounded"
              title={event.ledger_hash}
            >
              Hash: {event.ledger_hash.slice(0, 12)}...{event.ledger_hash.slice(-8)}
            </span>
          )}
        </div>
        
        {/* Details */}
        {Object.keys(event.details).length > 0 && (
          <div className="mt-2 text-xs space-y-1">
            {Object.entries(event.details).map(([key, value]) => (
              value !== null && value !== undefined && (
                <div key={key} className="text-slate-500">
                  <span className="font-medium">{key}:</span>{' '}
                  <span>{String(value)}</span>
                </div>
              )
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * PDOTimelineView — READ-ONLY timeline visualization.
 * 
 * INV-OC-001: No mutation actions.
 * INV-OC-003: Ledger hash visible for each event.
 * INV-OC-004: Missing hashes shown as UNAVAILABLE.
 */
export const PDOTimelineView: React.FC<PDOTimelineViewProps> = ({
  pdoId,
  settlementId,
  className = '',
}) => {
  const [timeline, setTimeline] = useState<OCTimelineResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Load timeline
  useEffect(() => {
    const loadTimeline = async () => {
      if (!pdoId && !settlementId) {
        setTimeline(null);
        return;
      }
      
      setLoading(true);
      setError(null);
      
      try {
        let response: OCTimelineResponse;
        
        if (pdoId) {
          response = await fetchPDOTimeline(pdoId);
        } else if (settlementId) {
          response = await fetchSettlementTimeline(settlementId);
        } else {
          return;
        }
        
        setTimeline(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load timeline');
      } finally {
        setLoading(false);
      }
    };
    
    loadTimeline();
  }, [pdoId, settlementId]);
  
  // Render
  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800">Timeline</h2>
          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
            READ-ONLY
          </span>
        </div>
        {(pdoId || settlementId) && (
          <span className="text-xs font-mono text-slate-500">
            {pdoId || settlementId}
          </span>
        )}
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {!pdoId && !settlementId && (
          <div className="text-center py-8 text-slate-400">
            Select a PDO or Settlement to view timeline
          </div>
        )}
        
        {loading && (
          <div className="text-center py-8 text-slate-500">
            Loading timeline...
          </div>
        )}
        
        {error && (
          <div className="text-center py-8 text-red-500">
            Error: {error}
          </div>
        )}
        
        {!loading && !error && timeline && timeline.events.length === 0 && (
          <div className="text-center py-8 text-slate-400">
            No timeline events
          </div>
        )}
        
        {!loading && !error && timeline && timeline.events.length > 0 && (
          <div>
            {timeline.events.map((event, index) => (
              <TimelineEventItem
                key={event.event_id}
                event={event}
                isFirst={index === 0}
                isLast={index === timeline.events.length - 1}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Time span footer */}
      {timeline && timeline.span_start && timeline.span_end && (
        <div className="px-4 py-2 border-t border-slate-200 text-xs text-slate-500">
          Span: {new Date(timeline.span_start).toLocaleDateString()} -{' '}
          {new Date(timeline.span_end).toLocaleDateString()}
        </div>
      )}
    </div>
  );
};

export default PDOTimelineView;
