// chainboard-ui/src/components/LiveMap.tsx
/**
 * LiveMap Component — Real-Time Container Tracking
 * =================================================
 * 
 * PAC: PAC-STRAT-P36-SWARM-STRIKE
 * Lane: DASHBOARD (The Face)
 * Agent: SONNY (L9)
 * 
 * Displays SmartContainers on a map with:
 * - Real-time position updates via WebSocket
 * - Color-coded status (green=OK, yellow=warning, red=breach)
 * - Click for container details
 */

import React, { useEffect, useState, useCallback } from 'react';

// Types
interface ContainerPosition {
  containerId: string;
  lat: number;
  lon: number;
  temperature: number;
  status: 'OK' | 'WARNING' | 'BREACH';
  lastUpdate: string;
  contractId?: string;
}

interface LiveMapProps {
  wsEndpoint?: string;
  initialContainers?: ContainerPosition[];
  onContainerClick?: (containerId: string) => void;
}

// Status colors
const STATUS_COLORS = {
  OK: '#22c55e',      // green-500
  WARNING: '#eab308', // yellow-500
  BREACH: '#ef4444',  // red-500
};

/**
 * LiveMap displays real-time container positions.
 * 
 * In V1, this renders a simple SVG map.
 * In production, integrate with Mapbox/Leaflet.
 */
export const LiveMap: React.FC<LiveMapProps> = ({
  wsEndpoint = 'ws://localhost:8000/ws/telemetry',
  initialContainers = [],
  onContainerClick,
}) => {
  const [containers, setContainers] = useState<Map<string, ContainerPosition>>(
    new Map(initialContainers.map(c => [c.containerId, c]))
  );
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket connection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket(wsEndpoint);

        ws.onopen = () => {
          setConnected(true);
          setError(null);
          console.log('[LiveMap] WebSocket connected');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'TELEMETRY_UPDATE') {
              const position: ContainerPosition = {
                containerId: data.container_id,
                lat: data.gps_lat,
                lon: data.gps_lon,
                temperature: data.temperature,
                status: getStatus(data.temperature, data.contract),
                lastUpdate: data.timestamp,
                contractId: data.contract_id,
              };

              setContainers(prev => {
                const next = new Map(prev);
                next.set(position.containerId, position);
                return next;
              });
            }
          } catch (e) {
            console.error('[LiveMap] Failed to parse message:', e);
          }
        };

        ws.onclose = () => {
          setConnected(false);
          console.log('[LiveMap] WebSocket closed, reconnecting...');
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = (e) => {
          setError('WebSocket connection failed');
          console.error('[LiveMap] WebSocket error:', e);
        };
      } catch (e) {
        setError('Failed to connect');
        reconnectTimeout = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [wsEndpoint]);

  // Determine container status based on temperature
  const getStatus = (temp: number, contract?: { minTemp: number; maxTemp: number }): 'OK' | 'WARNING' | 'BREACH' => {
    if (!contract) return 'OK';
    
    const margin = (contract.maxTemp - contract.minTemp) * 0.1;
    
    if (temp < contract.minTemp || temp > contract.maxTemp) {
      return 'BREACH';
    }
    if (temp < contract.minTemp + margin || temp > contract.maxTemp - margin) {
      return 'WARNING';
    }
    return 'OK';
  };

  // Convert lat/lon to SVG coordinates (simple Mercator)
  const toSvgCoords = (lat: number, lon: number): { x: number; y: number } => {
    // Simple mapping: lon (-180 to 180) -> x (0 to 800)
    //                 lat (-90 to 90) -> y (400 to 0)
    const x = ((lon + 180) / 360) * 800;
    const y = ((90 - lat) / 180) * 400;
    return { x, y };
  };

  const handleContainerClick = useCallback((containerId: string) => {
    if (onContainerClick) {
      onContainerClick(containerId);
    }
  }, [onContainerClick]);

  return (
    <div className="live-map-container">
      {/* Header */}
      <div className="live-map-header">
        <h3>🌍 Live Container Tracking</h3>
        <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* Map SVG */}
      <svg
        viewBox="0 0 800 400"
        className="live-map-svg"
        style={{ background: '#1e293b', borderRadius: '8px' }}
      >
        {/* Grid lines */}
        {[...Array(9)].map((_, i) => (
          <line
            key={`h-${i}`}
            x1="0"
            y1={i * 50}
            x2="800"
            y2={i * 50}
            stroke="#334155"
            strokeWidth="0.5"
          />
        ))}
        {[...Array(17)].map((_, i) => (
          <line
            key={`v-${i}`}
            x1={i * 50}
            y1="0"
            x2={i * 50}
            y2="400"
            stroke="#334155"
            strokeWidth="0.5"
          />
        ))}

        {/* Container markers */}
        {Array.from(containers.values()).map((container) => {
          const { x, y } = toSvgCoords(container.lat, container.lon);
          return (
            <g
              key={container.containerId}
              onClick={() => handleContainerClick(container.containerId)}
              style={{ cursor: 'pointer' }}
            >
              {/* Pulse animation for active containers */}
              <circle
                cx={x}
                cy={y}
                r="12"
                fill={STATUS_COLORS[container.status]}
                opacity="0.3"
                className="pulse"
              />
              {/* Container marker */}
              <circle
                cx={x}
                cy={y}
                r="6"
                fill={STATUS_COLORS[container.status]}
                stroke="#fff"
                strokeWidth="2"
              />
              {/* Label */}
              <text
                x={x}
                y={y - 12}
                textAnchor="middle"
                fill="#fff"
                fontSize="10"
              >
                {container.containerId.slice(0, 8)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="live-map-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ background: STATUS_COLORS.OK }}></span>
          OK
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: STATUS_COLORS.WARNING }}></span>
          Warning
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: STATUS_COLORS.BREACH }}></span>
          Breach
        </div>
        <div className="legend-item">
          <strong>{containers.size}</strong> containers tracked
        </div>
      </div>

      {/* Styles */}
      <style>{`
        .live-map-container {
          background: #0f172a;
          border-radius: 12px;
          padding: 16px;
          color: white;
        }
        .live-map-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .live-map-header h3 {
          margin: 0;
          font-size: 18px;
        }
        .connection-status {
          font-size: 12px;
          padding: 4px 8px;
          border-radius: 4px;
        }
        .connection-status.connected {
          background: rgba(34, 197, 94, 0.2);
        }
        .connection-status.disconnected {
          background: rgba(239, 68, 68, 0.2);
        }
        .error-banner {
          background: rgba(239, 68, 68, 0.2);
          padding: 8px;
          border-radius: 4px;
          margin-bottom: 12px;
          font-size: 14px;
        }
        .live-map-svg {
          width: 100%;
          height: auto;
        }
        .live-map-legend {
          display: flex;
          gap: 16px;
          margin-top: 12px;
          font-size: 12px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .legend-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .pulse {
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.1; transform: scale(1.5); }
          100% { opacity: 0.3; transform: scale(1); }
        }
      `}</style>
    </div>
  );
};

export default LiveMap;
