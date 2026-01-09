/**
 * ╔═══════════════════════════════════════════════════════════════════════════════╗
 * ║                    FIVE PILLARS STATUS PANEL                                  ║
 * ║                    PAC-OCC-P34 — Multi-Ledger Dashboard                       ║
 * ╚═══════════════════════════════════════════════════════════════════════════════╝
 * 
 * Displays real-time connectivity status for all five ledger pillars:
 * 1. Hedera (HCS) — Fair Ordering
 * 2. Space and Time (SxT) — ZK-Proof
 * 3. Chainlink — Cross-Chain Oracle
 * 4. XRP Ledger — Settlement
 * 5. Seeburger BIS — Enterprise B2B
 * 
 * Author: SONNY (GID-04)
 */

import React, { useState, useEffect } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type PillarStatus = 'online' | 'offline' | 'degraded' | 'disabled';

export interface PillarConfig {
  id: string;
  name: string;
  shortName: string;
  description: string;
  status: PillarStatus;
  enabled: boolean;
  lastPing?: string;
  latencyMs?: number;
  icon: string;
}

export interface FivePillarsStatusProps {
  pillars?: PillarConfig[];
  onPillarClick?: (pillarId: string) => void;
  refreshInterval?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DEFAULT PILLAR CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const DEFAULT_PILLARS: PillarConfig[] = [
  {
    id: 'hedera',
    name: 'Hedera Consensus',
    shortName: 'HCS',
    description: 'Fair Ordering / ABFT Consensus',
    status: 'disabled',
    enabled: false,
    icon: '🔷',
  },
  {
    id: 'sxt',
    name: 'Space and Time',
    shortName: 'SxT',
    description: 'ZK-Proof Verification',
    status: 'disabled',
    enabled: false,
    icon: '🔮',
  },
  {
    id: 'chainlink',
    name: 'Chainlink Functions',
    shortName: 'LINK',
    description: 'Cross-Chain Oracle Bridge',
    status: 'disabled',
    enabled: false,
    icon: '🔗',
  },
  {
    id: 'xrpl',
    name: 'XRP Ledger',
    shortName: 'XRPL',
    description: 'Payment Settlement',
    status: 'disabled',
    enabled: false,
    icon: '💎',
  },
  {
    id: 'seeburger',
    name: 'Seeburger BIS',
    shortName: 'BIS',
    description: 'Enterprise B2B Workflow',
    status: 'disabled',
    enabled: false,
    icon: '🏢',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// STATUS INDICATOR COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const StatusIndicator: React.FC<{ status: PillarStatus }> = ({ status }) => {
  const statusColors: Record<PillarStatus, string> = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    degraded: 'bg-yellow-500',
    disabled: 'bg-gray-400',
  };

  const statusLabels: Record<PillarStatus, string> = {
    online: 'Online',
    offline: 'Offline',
    degraded: 'Degraded',
    disabled: 'Disabled',
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${statusColors[status]} animate-pulse`} />
      <span className="text-xs text-gray-500">{statusLabels[status]}</span>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// PILLAR CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const PillarCard: React.FC<{
  pillar: PillarConfig;
  onClick?: () => void;
}> = ({ pillar, onClick }) => {
  const borderColors: Record<PillarStatus, string> = {
    online: 'border-green-500',
    offline: 'border-red-500',
    degraded: 'border-yellow-500',
    disabled: 'border-gray-300',
  };

  return (
    <div
      className={`
        p-4 rounded-lg border-2 ${borderColors[pillar.status]}
        bg-white dark:bg-gray-800
        hover:shadow-lg transition-shadow cursor-pointer
      `}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{pillar.icon}</span>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {pillar.shortName}
            </h3>
            <p className="text-xs text-gray-500">{pillar.name}</p>
          </div>
        </div>
        <StatusIndicator status={pillar.status} />
      </div>
      
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        {pillar.description}
      </p>
      
      {pillar.latencyMs !== undefined && pillar.status === 'online' && (
        <div className="mt-2 text-xs text-gray-400">
          Latency: {pillar.latencyMs}ms
        </div>
      )}
      
      {pillar.lastPing && (
        <div className="mt-1 text-xs text-gray-400">
          Last ping: {pillar.lastPing}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const FivePillarsStatus: React.FC<FivePillarsStatusProps> = ({
  pillars = DEFAULT_PILLARS,
  onPillarClick,
  refreshInterval = 30000,
}) => {
  const [pillarStates, setPillarStates] = useState<PillarConfig[]>(pillars);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Simulated refresh (replace with actual API calls)
  useEffect(() => {
    const interval = setInterval(() => {
      setLastRefresh(new Date());
      // In production, fetch actual status from /api/pillars/status
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const onlineCount = pillarStates.filter(p => p.status === 'online').length;
  const totalEnabled = pillarStates.filter(p => p.enabled).length;

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 rounded-xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Five Pillars Status
          </h2>
          <p className="text-sm text-gray-500">
            Multi-ledger connectivity dashboard
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {onlineCount}/{totalEnabled || pillarStates.length}
          </div>
          <div className="text-xs text-gray-500">
            Pillars Online
          </div>
        </div>
      </div>

      {/* Pillar Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {pillarStates.map((pillar) => (
          <PillarCard
            key={pillar.id}
            pillar={pillar}
            onClick={() => onPillarClick?.(pillar.id)}
          />
        ))}
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
        <span>
          Last refresh: {lastRefresh.toLocaleTimeString()}
        </span>
        <span>
          PAC-OCC-P34 • Five Pillars Architecture
        </span>
      </div>
    </div>
  );
};

export default FivePillarsStatus;
