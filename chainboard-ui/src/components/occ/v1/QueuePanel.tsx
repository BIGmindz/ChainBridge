/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 Queue Panel — Read-Only Queue Visualization
 * PAC-JEFFREY-P03: OCC UI Execution
 * 
 * Displays the OCC action queue with:
 *   - Priority-grouped queue items
 *   - Operator attribution
 *   - Hash chain visualization
 *   - Queue metrics
 * 
 * INVARIANTS:
 * - INV-OCC-UI-001: Read-only display, no mutations
 * - INV-OCC-UI-002: Observer pattern only
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0, Article III
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useMemo } from 'react';
import type { QueueState, QueueItem, QueuePriority, QueueMetrics } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// PRIORITY COLORS & LABELS
// ═══════════════════════════════════════════════════════════════════════════════

const PRIORITY_CONFIG: Record<QueuePriority, { color: string; bg: string; label: string }> = {
  EMERGENCY: { color: 'text-red-400', bg: 'bg-red-900/30', label: 'Emergency' },
  CRITICAL: { color: 'text-orange-400', bg: 'bg-orange-900/30', label: 'Critical' },
  HIGH: { color: 'text-yellow-400', bg: 'bg-yellow-900/30', label: 'High' },
  NORMAL: { color: 'text-blue-400', bg: 'bg-blue-900/30', label: 'Normal' },
  LOW: { color: 'text-gray-400', bg: 'bg-gray-800', label: 'Low' },
  DEFERRED: { color: 'text-gray-500', bg: 'bg-gray-900', label: 'Deferred' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// QUEUE METRICS COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const QueueMetricsPanel: React.FC<{ metrics: QueueMetrics; isClosed: boolean }> = ({
  metrics,
  isClosed,
}) => {
  const utilizationPercent = Math.round((metrics.currentSize / metrics.maxSize) * 100);
  const utilizationColor = 
    utilizationPercent > 90 ? 'text-red-400' :
    utilizationPercent > 70 ? 'text-yellow-400' :
    'text-green-400';

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-300">Queue Metrics</h4>
        {isClosed && (
          <span className="px-2 py-0.5 text-xs bg-red-900 text-red-300 rounded">
            FAIL-CLOSED
          </span>
        )}
      </div>
      
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">Size:</span>
          <span className={`ml-2 font-mono ${utilizationColor}`}>
            {metrics.currentSize}/{metrics.maxSize}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Utilization:</span>
          <span className={`ml-2 font-mono ${utilizationColor}`}>
            {utilizationPercent}%
          </span>
        </div>
        <div>
          <span className="text-gray-500">Enqueued:</span>
          <span className="ml-2 font-mono text-green-400">{metrics.enqueueCount}</span>
        </div>
        <div>
          <span className="text-gray-500">Dequeued:</span>
          <span className="ml-2 font-mono text-blue-400">{metrics.dequeueCount}</span>
        </div>
        <div>
          <span className="text-gray-500">Rejected:</span>
          <span className="ml-2 font-mono text-red-400">{metrics.rejectCount}</span>
        </div>
        <div>
          <span className="text-gray-500">Sequence:</span>
          <span className="ml-2 font-mono text-gray-400">{metrics.sequenceCounter}</span>
        </div>
      </div>
      
      {/* Utilization bar */}
      <div className="mt-3 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            utilizationPercent > 90 ? 'bg-red-500' :
            utilizationPercent > 70 ? 'bg-yellow-500' :
            'bg-green-500'
          }`}
          style={{ width: `${utilizationPercent}%` }}
        />
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// QUEUE ITEM CARD
// ═══════════════════════════════════════════════════════════════════════════════

const QueueItemCard: React.FC<{ item: QueueItem }> = ({ item }) => {
  const priorityConfig = PRIORITY_CONFIG[item.priority];
  const shortHash = item.hashCurrent.substring(0, 8);
  
  return (
    <div className={`rounded-lg p-3 border border-gray-700 ${priorityConfig.bg}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 text-xs rounded ${priorityConfig.color} bg-gray-900/50`}>
            {priorityConfig.label}
          </span>
          <span className="text-xs text-gray-500">#{item.sequenceNumber}</span>
        </div>
        <span className="text-xs font-mono text-gray-500" title={item.hashCurrent}>
          {shortHash}...
        </span>
      </div>
      
      <div className="text-sm font-medium text-white mb-1">{item.actionType}</div>
      
      <div className="text-xs text-gray-400 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Operator:</span>
          <span className="font-mono">{item.operator.operatorId}</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
            item.operator.tier === 'T6' ? 'bg-purple-900 text-purple-300' :
            item.operator.tier === 'T5' ? 'bg-red-900 text-red-300' :
            item.operator.tier === 'T4' ? 'bg-orange-900 text-orange-300' :
            'bg-gray-700 text-gray-300'
          }`}>
            {item.operator.tier}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Created:</span>
          <span className="ml-2">{new Date(item.createdAt).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// PRIORITY GROUP
// ═══════════════════════════════════════════════════════════════════════════════

const PriorityGroup: React.FC<{ priority: QueuePriority; items: QueueItem[] }> = ({
  priority,
  items,
}) => {
  const config = PRIORITY_CONFIG[priority];
  
  if (items.length === 0) return null;
  
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h5 className={`text-sm font-semibold ${config.color}`}>{config.label}</h5>
        <span className="text-xs text-gray-500">({items.length})</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <QueueItemCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN QUEUE PANEL COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export interface QueuePanelProps {
  state: QueueState;
  loading?: boolean;
  onRefresh?: () => void;
}

export const QueuePanel: React.FC<QueuePanelProps> = ({
  state,
  loading = false,
  onRefresh,
}) => {
  // Group items by priority
  const groupedItems = useMemo(() => {
    const groups: Record<QueuePriority, QueueItem[]> = {
      EMERGENCY: [],
      CRITICAL: [],
      HIGH: [],
      NORMAL: [],
      LOW: [],
      DEFERRED: [],
    };
    
    state.items.forEach((item) => {
      groups[item.priority].push(item);
    });
    
    return groups;
  }, [state.items]);
  
  const priorities: QueuePriority[] = ['EMERGENCY', 'CRITICAL', 'HIGH', 'NORMAL', 'LOW', 'DEFERRED'];

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">OCC Queue</h3>
          <span className="text-xs text-gray-500">
            INV-OCC-006: Priority Ordering
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            Last: {new Date(state.lastRefresh).toLocaleTimeString()}
          </span>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded disabled:opacity-50"
              aria-label="Refresh queue"
            >
              {loading ? '...' : '↻'}
            </button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Metrics */}
        <QueueMetricsPanel metrics={state.metrics} isClosed={state.isClosed} />
        
        {/* Queue Items */}
        {state.items.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            Queue is empty
          </div>
        ) : (
          <div className="space-y-4">
            {priorities.map((priority) => (
              <PriorityGroup
                key={priority}
                priority={priority}
                items={groupedItems[priority]}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Footer - Read-only notice */}
      <div className="bg-gray-800 px-4 py-2 border-t border-gray-700">
        <span className="text-xs text-gray-500">
          📖 Read-only view • INV-OCC-UI-001
        </span>
      </div>
    </div>
  );
};

export default QueuePanel;
