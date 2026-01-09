// ═══════════════════════════════════════════════════════════════════════════════
// OCC Phase 2 — Agent Trust Scorecard
// PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
// Agents: SONNY (GID-02) — Frontend / OCC UI
//         LIRA (GID-09) — Accessibility & UX
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * AgentTrustScorecard — Visual risk scorecard for agent trust
 *
 * PURPOSE:
 *   Display agent trust indices with multi-dimensional scoring,
 *   historical trends, and tier-based trust visualization.
 *
 * FEATURES:
 *   - Trust tier badges (PROBATION → TRUSTED)
 *   - Radar chart for trust dimensions
 *   - Historical trend indicators
 *   - Drill-down to dimension details
 *
 * ACCESSIBILITY (LIRA):
 *   - Trust levels announced via ARIA
 *   - Color-blind safe tier indicators
 *   - Keyboard navigable scorecard
 *   - Screen reader optimized scores
 *
 * INVARIANTS:
 *   INV-UI-TRUST-001: Trust scores are read-only display
 *   INV-UI-TRUST-002: No trust score manipulation from UI
 */

import React, { useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type TrustTier = 'PROBATION' | 'STANDARD' | 'ELEVATED' | 'TRUSTED';
export type TrustDimension =
  | 'EXECUTION_ACCURACY'
  | 'INVARIANT_COMPLIANCE'
  | 'RESPONSE_TIME'
  | 'ERROR_RATE'
  | 'GOVERNANCE_ADHERENCE';

export interface DimensionScore {
  dimension: TrustDimension;
  score: number; // 0.0 - 1.0
  samples: number;
  trend: 'up' | 'down' | 'stable';
}

export interface AgentTrustData {
  agent_id: string;
  agent_name: string;
  overall_trust: number; // 0.0 - 1.0
  trust_tier: TrustTier;
  dimensions: DimensionScore[];
  last_updated: string;
  pac_count_30d: number;
  violation_count_30d: number;
}

export interface AgentTrustScorecardProps {
  /** Agents with trust data */
  agents: AgentTrustData[];
  /** Selected agent ID */
  selectedAgentId?: string;
  /** Selection handler */
  onSelectAgent?: (agentId: string) => void;
  /** Sort by trust score */
  sortByTrust?: boolean;
  /** Show detailed dimensions */
  showDimensions?: boolean;
  /** ARIA label */
  ariaLabel?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const TIER_CONFIG: Record<TrustTier, {
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
}> = {
  PROBATION: {
    label: 'Probation',
    icon: '⚠️',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
    description: 'Under review, limited privileges',
  },
  STANDARD: {
    label: 'Standard',
    icon: '📋',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-300',
    description: 'Normal operation, monitored',
  },
  ELEVATED: {
    label: 'Elevated',
    icon: '⭐',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-300',
    description: 'Above average trust',
  },
  TRUSTED: {
    label: 'Trusted',
    icon: '🏆',
    color: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-300',
    description: 'Full trust, expedited approval',
  },
};

const DIMENSION_LABELS: Record<TrustDimension, {
  label: string;
  shortLabel: string;
  icon: string;
}> = {
  EXECUTION_ACCURACY: {
    label: 'Execution Accuracy',
    shortLabel: 'Accuracy',
    icon: '🎯',
  },
  INVARIANT_COMPLIANCE: {
    label: 'Invariant Compliance',
    shortLabel: 'Compliance',
    icon: '✓',
  },
  RESPONSE_TIME: {
    label: 'Response Time',
    shortLabel: 'Speed',
    icon: '⚡',
  },
  ERROR_RATE: {
    label: 'Error Rate (inverse)',
    shortLabel: 'Reliability',
    icon: '🛡️',
  },
  GOVERNANCE_ADHERENCE: {
    label: 'Governance Adherence',
    shortLabel: 'Governance',
    icon: '⚖️',
  },
};

const TREND_ICONS: Record<string, { icon: string; color: string; label: string }> = {
  up: { icon: '↑', color: 'text-green-600', label: 'Improving' },
  down: { icon: '↓', color: 'text-red-600', label: 'Declining' },
  stable: { icon: '→', color: 'text-gray-600', label: 'Stable' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// SUBCOMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface TrustGaugeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

const TrustGauge: React.FC<TrustGaugeProps> = ({ score, size = 'md' }) => {
  const percentage = Math.round(score * 100);
  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference - (score * circumference);

  const sizeConfig = {
    sm: { width: 60, strokeWidth: 4 },
    md: { width: 80, strokeWidth: 6 },
    lg: { width: 100, strokeWidth: 8 },
  };

  const { width, strokeWidth } = sizeConfig[size];

  // Color based on score
  const getColor = (s: number) => {
    if (s >= 0.95) return '#22c55e'; // green
    if (s >= 0.80) return '#3b82f6'; // blue
    if (s >= 0.60) return '#eab308'; // yellow
    return '#ef4444'; // red
  };

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        width={width}
        height={width}
        viewBox="0 0 100 100"
        className="transform -rotate-90"
        role="img"
        aria-label={`Trust score: ${percentage}%`}
      >
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          stroke={getColor(score)}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500"
        />
      </svg>
      <span className="absolute text-sm font-bold text-gray-900">
        {percentage}%
      </span>
    </div>
  );
};

interface DimensionBarProps {
  dimension: DimensionScore;
}

const DimensionBar: React.FC<DimensionBarProps> = ({ dimension }) => {
  const config = DIMENSION_LABELS[dimension.dimension];
  const trend = TREND_ICONS[dimension.trend];
  const percentage = Math.round(dimension.score * 100);

  // Color based on score
  const getBarColor = (s: number) => {
    if (s >= 0.90) return 'bg-green-500';
    if (s >= 0.70) return 'bg-blue-500';
    if (s >= 0.50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-gray-700">
          <span aria-hidden="true">{config.icon}</span>
          {config.shortLabel}
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium">{percentage}%</span>
          <span
            className={trend.color}
            role="img"
            aria-label={trend.label}
            title={trend.label}
          >
            {trend.icon}
          </span>
        </span>
      </div>
      <div
        className="h-2 bg-gray-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${config.label}: ${percentage}%`}
      >
        <div
          className={`h-full transition-all duration-300 ${getBarColor(dimension.score)}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

interface AgentCardProps {
  agent: AgentTrustData;
  isSelected: boolean;
  onSelect: () => void;
  showDimensions: boolean;
}

const AgentCard: React.FC<AgentCardProps> = ({
  agent,
  isSelected,
  onSelect,
  showDimensions,
}) => {
  const tierConfig = TIER_CONFIG[agent.trust_tier];

  return (
    <div
      role="article"
      aria-selected={isSelected}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      tabIndex={0}
      className={`
        p-4 border rounded-lg cursor-pointer transition-all duration-150
        ${tierConfig.bgColor} ${tierConfig.borderColor}
        ${isSelected ? 'ring-2 ring-blue-500 ring-offset-1' : 'hover:shadow-md'}
        focus:outline-none focus:ring-2 focus:ring-blue-500
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{agent.agent_name}</h3>
          <p className="text-xs text-gray-500 font-mono">{agent.agent_id}</p>
        </div>
        <TrustGauge score={agent.overall_trust} size="sm" />
      </div>

      {/* Tier Badge */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${tierConfig.color}`}
        >
          <span aria-hidden="true">{tierConfig.icon}</span>
          {tierConfig.label}
        </span>
        <span className="text-xs text-gray-500" title={tierConfig.description}>
          {tierConfig.description}
        </span>
      </div>

      {/* Dimensions */}
      {showDimensions && agent.dimensions.length > 0 && (
        <div className="space-y-2 mb-3">
          {agent.dimensions.map((dim) => (
            <DimensionBar key={dim.dimension} dimension={dim} />
          ))}
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 pt-2 border-t border-gray-200 text-xs text-gray-500">
        <span>
          <strong>{agent.pac_count_30d}</strong> PACs (30d)
        </span>
        <span className={agent.violation_count_30d > 0 ? 'text-red-600' : ''}>
          <strong>{agent.violation_count_30d}</strong> violations
        </span>
      </div>

      {/* Last Updated */}
      <div className="mt-2 text-xs text-gray-400">
        Updated: {new Date(agent.last_updated).toLocaleString()}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const AgentTrustScorecard: React.FC<AgentTrustScorecardProps> = ({
  agents,
  selectedAgentId,
  onSelectAgent,
  sortByTrust = true,
  showDimensions = true,
  ariaLabel = 'Agent Trust Scorecard',
}) => {
  // Sort and filter agents
  const displayAgents = useMemo(() => {
    const sorted = [...agents];
    if (sortByTrust) {
      sorted.sort((a, b) => b.overall_trust - a.overall_trust);
    }
    return sorted;
  }, [agents, sortByTrust]);

  // Statistics
  const stats = useMemo(() => {
    const tierCounts = agents.reduce((acc, agent) => {
      acc[agent.trust_tier] = (acc[agent.trust_tier] || 0) + 1;
      return acc;
    }, {} as Record<TrustTier, number>);

    const avgTrust =
      agents.length > 0
        ? agents.reduce((sum, a) => sum + a.overall_trust, 0) / agents.length
        : 0;

    return {
      total: agents.length,
      avgTrust,
      ...tierCounts,
    };
  }, [agents]);

  return (
    <div
      className="flex flex-col h-full bg-white rounded-lg border border-gray-200 shadow-sm"
      aria-label={ariaLabel}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Agent Trust Scorecard
          </h2>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-600">{stats.total} agents</span>
            <span className="text-gray-400">|</span>
            <span className="text-gray-600">
              Avg: {Math.round(stats.avgTrust * 100)}%
            </span>
          </div>
        </div>

        {/* Tier Summary */}
        <div
          className="flex items-center gap-2 mt-2"
          role="status"
          aria-live="polite"
        >
          {(Object.keys(TIER_CONFIG) as TrustTier[]).map((tier) => {
            const count = stats[tier] || 0;
            if (count === 0) return null;
            const config = TIER_CONFIG[tier];
            return (
              <span
                key={tier}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${config.bgColor} ${config.color}`}
              >
                <span aria-hidden="true">{config.icon}</span>
                {count} {config.label}
              </span>
            );
          })}
        </div>
      </div>

      {/* Agent Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {displayAgents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <span className="text-2xl mb-2">📊</span>
            <p>No agent trust data available</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {displayAgents.map((agent) => (
              <AgentCard
                key={agent.agent_id}
                agent={agent}
                isSelected={selectedAgentId === agent.agent_id}
                onSelect={() => onSelectAgent?.(agent.agent_id)}
                showDimensions={showDimensions}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span>
          Trust scores calculated from execution history, invariant compliance, and governance adherence
        </span>
      </div>
    </div>
  );
};

export default AgentTrustScorecard;
