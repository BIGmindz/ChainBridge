// chainboard-ui/src/components/SettlementStream.tsx
/**
 * SettlementStream Component — Real-Time Settlement Feed
 * =======================================================
 * 
 * PAC: PAC-STRAT-P36-SWARM-STRIKE
 * Lane: DASHBOARD (The Face)
 * Agent: SONNY (L9)
 * 
 * Displays a live stream of settlement events:
 * - Contract state transitions
 * - Payment executions
 * - Temperature breaches
 * 
 * INVARIANT: UI reflects Real-Time Ledger State (No caching lies)
 */

import React, { useEffect, useState, useRef } from 'react';

// Types
interface SettlementEvent {
  id: string;
  type: 'STATE_CHANGE' | 'PAYMENT' | 'BREACH' | 'ALERT';
  timestamp: string;
  contractId?: string;
  containerId?: string;
  fromState?: string;
  toState?: string;
  txHash?: string;
  amount?: string;
  currency?: string;
  reason?: string;
}

interface SettlementStreamProps {
  wsEndpoint?: string;
  maxEvents?: number;
  onEventClick?: (event: SettlementEvent) => void;
}

// Event type colors and icons
const EVENT_STYLES: Record<string, { icon: string; color: string; bg: string }> = {
  STATE_CHANGE: { icon: '🔄', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
  PAYMENT: { icon: '💸', color: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)' },
  BREACH: { icon: '🚨', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
  ALERT: { icon: '⚠️', color: '#eab308', bg: 'rgba(234, 179, 8, 0.1)' },
};

/**
 * SettlementStream displays real-time settlement events.
 */
export const SettlementStream: React.FC<SettlementStreamProps> = ({
  wsEndpoint = 'ws://localhost:8000/ws/settlements',
  maxEvents = 50,
  onEventClick,
}) => {
  const [events, setEvents] = useState<SettlementEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Stats
  const [stats, setStats] = useState({
    totalPayments: 0,
    totalAmount: 0,
    breachCount: 0,
  });

  // WebSocket connection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket(wsEndpoint);

        ws.onopen = () => {
          setConnected(true);
          console.log('[SettlementStream] Connected');
        };

        ws.onmessage = (msg) => {
          if (paused) return;

          try {
            const data = JSON.parse(msg.data);
            
            const event: SettlementEvent = {
              id: data.event_id || crypto.randomUUID(),
              type: mapEventType(data.event_type),
              timestamp: data.timestamp || new Date().toISOString(),
              contractId: data.contract_id,
              containerId: data.container_id,
              fromState: data.from_state,
              toState: data.to_state || data.settlement_state,
              txHash: data.tx_hash,
              amount: data.amount,
              currency: data.currency,
              reason: data.reason,
            };

            setEvents(prev => {
              const next = [event, ...prev].slice(0, maxEvents);
              return next;
            });

            // Update stats
            if (event.type === 'PAYMENT' && event.amount) {
              setStats(prev => ({
                ...prev,
                totalPayments: prev.totalPayments + 1,
                totalAmount: prev.totalAmount + parseFloat(event.amount || '0'),
              }));
            } else if (event.type === 'BREACH') {
              setStats(prev => ({
                ...prev,
                breachCount: prev.breachCount + 1,
              }));
            }
          } catch (e) {
            console.error('[SettlementStream] Parse error:', e);
          }
        };

        ws.onclose = () => {
          setConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = (e) => {
          console.error('[SettlementStream] Error:', e);
        };
      } catch (e) {
        reconnectTimeout = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [wsEndpoint, paused, maxEvents]);

  // Map backend event types to UI types
  const mapEventType = (type: string): SettlementEvent['type'] => {
    switch (type) {
      case 'SETTLEMENT_TRIGGERED':
        return 'STATE_CHANGE';
      case 'PAYMENT_EXECUTED':
        return 'PAYMENT';
      case 'TEMPERATURE_BREACH':
        return 'BREACH';
      default:
        return 'ALERT';
    }
  };

  // Format timestamp
  const formatTime = (iso: string): string => {
    const date = new Date(iso);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Format amount
  const formatAmount = (amount: string, currency: string = 'USD'): string => {
    const num = parseFloat(amount);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(num);
  };

  return (
    <div className="settlement-stream-container">
      {/* Header */}
      <div className="stream-header">
        <div className="header-left">
          <h3>📊 Settlement Stream</h3>
          <div className={`connection-badge ${connected ? 'connected' : ''}`}>
            {connected ? '● Live' : '○ Offline'}
          </div>
        </div>
        <div className="header-right">
          <button 
            className={`pause-btn ${paused ? 'paused' : ''}`}
            onClick={() => setPaused(!paused)}
          >
            {paused ? '▶ Resume' : '⏸ Pause'}
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat">
          <span className="stat-value">{stats.totalPayments}</span>
          <span className="stat-label">Payments</span>
        </div>
        <div className="stat">
          <span className="stat-value">${stats.totalAmount.toLocaleString()}</span>
          <span className="stat-label">Total Settled</span>
        </div>
        <div className="stat">
          <span className="stat-value" style={{ color: stats.breachCount > 0 ? '#ef4444' : 'inherit' }}>
            {stats.breachCount}
          </span>
          <span className="stat-label">Breaches</span>
        </div>
      </div>

      {/* Event List */}
      <div className="event-list" ref={containerRef}>
        {events.length === 0 ? (
          <div className="empty-state">
            <span>Waiting for events...</span>
          </div>
        ) : (
          events.map((event) => {
            const style = EVENT_STYLES[event.type];
            return (
              <div
                key={event.id}
                className="event-item"
                style={{ background: style.bg, borderLeftColor: style.color }}
                onClick={() => onEventClick?.(event)}
              >
                <div className="event-icon">{style.icon}</div>
                <div className="event-content">
                  <div className="event-main">
                    {event.type === 'PAYMENT' && (
                      <span className="event-title">
                        Payment: {formatAmount(event.amount || '0', event.currency)}
                      </span>
                    )}
                    {event.type === 'STATE_CHANGE' && (
                      <span className="event-title">
                        {event.fromState || '?'} → {event.toState}
                      </span>
                    )}
                    {event.type === 'BREACH' && (
                      <span className="event-title">Temperature Breach</span>
                    )}
                    {event.type === 'ALERT' && (
                      <span className="event-title">System Alert</span>
                    )}
                  </div>
                  <div className="event-meta">
                    {event.contractId && (
                      <span className="meta-tag">
                        Contract: {event.contractId.slice(0, 8)}...
                      </span>
                    )}
                    {event.txHash && (
                      <span className="meta-tag tx-hash">
                        TX: {event.txHash.slice(0, 12)}...
                      </span>
                    )}
                    {event.reason && (
                      <span className="meta-reason">{event.reason}</span>
                    )}
                  </div>
                </div>
                <div className="event-time">{formatTime(event.timestamp)}</div>
              </div>
            );
          })
        )}
      </div>

      {/* Styles */}
      <style>{`
        .settlement-stream-container {
          background: #0f172a;
          border-radius: 12px;
          padding: 16px;
          color: white;
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        .stream-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .header-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .stream-header h3 {
          margin: 0;
          font-size: 18px;
        }
        .connection-badge {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 10px;
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
        }
        .connection-badge.connected {
          background: rgba(34, 197, 94, 0.2);
          color: #22c55e;
        }
        .pause-btn {
          background: rgba(255, 255, 255, 0.1);
          border: none;
          color: white;
          padding: 6px 12px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
        }
        .pause-btn:hover {
          background: rgba(255, 255, 255, 0.2);
        }
        .pause-btn.paused {
          background: rgba(59, 130, 246, 0.3);
        }
        .stats-bar {
          display: flex;
          gap: 24px;
          padding: 12px 16px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          margin-bottom: 12px;
        }
        .stat {
          display: flex;
          flex-direction: column;
        }
        .stat-value {
          font-size: 20px;
          font-weight: bold;
        }
        .stat-label {
          font-size: 11px;
          color: #94a3b8;
        }
        .event-list {
          flex: 1;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .empty-state {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100px;
          color: #64748b;
        }
        .event-item {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 12px;
          border-radius: 8px;
          border-left: 3px solid;
          cursor: pointer;
          transition: transform 0.1s;
        }
        .event-item:hover {
          transform: translateX(4px);
        }
        .event-icon {
          font-size: 20px;
        }
        .event-content {
          flex: 1;
        }
        .event-title {
          font-weight: 600;
          font-size: 14px;
        }
        .event-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 4px;
        }
        .meta-tag {
          font-size: 11px;
          background: rgba(255, 255, 255, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
        }
        .tx-hash {
          font-family: monospace;
        }
        .meta-reason {
          font-size: 11px;
          color: #94a3b8;
        }
        .event-time {
          font-size: 11px;
          color: #64748b;
          white-space: nowrap;
        }
      `}</style>
    </div>
  );
};

export default SettlementStream;
