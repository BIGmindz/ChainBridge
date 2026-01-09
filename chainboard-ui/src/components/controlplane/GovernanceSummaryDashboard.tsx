/**
 * Governance Summary Dashboard — Control Plane UI
 * PAC-JEFFREY-P01: Complete Governance Gate Visualization
 *
 * Aggregates all governance gates and eligibility checks:
 * - PAG-01 Agent Activation Gate
 * - Multi-Agent WRAP Collection Gate
 * - RG-01 Review Gate
 * - BSRG-01 Self-Review Gate
 * - ACK Latency Gate
 * - Ledger Commit Gate
 *
 * Displays positive closure conditions and schema references.
 *
 * Author: Benson Execution Orchestrator (GID-00)
 * Frontend Lane: SONNY (GID-02)
 */

import React from 'react';
import {
  GovernanceSummaryDTO,
  GateStatus,
  GateSummary,
  LIFECYCLE_STATE_CONFIG,
  SETTLEMENT_CONFIG,
} from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// GATE STATUS DISPLAY
// ═══════════════════════════════════════════════════════════════════════════════

const GATE_STATUS_CONFIG: Record<GateStatus, {
  icon: string;
  color: string;
  bgColor: string;
  label: string;
}> = {
  PASS: {
    icon: '✅',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    label: 'Pass',
  },
  FAIL: {
    icon: '❌',
    color: 'text-red-400',
    bgColor: 'bg-red-900/30',
    label: 'Fail',
  },
  PENDING: {
    icon: '⏳',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
    label: 'Pending',
  },
  BLOCKED: {
    icon: '🛑',
    color: 'text-red-500',
    bgColor: 'bg-red-900/40',
    label: 'Blocked',
  },
  COMMITTED: {
    icon: '📜',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-900/30',
    label: 'Committed',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// GATE CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface GateCardProps {
  gate: GateSummary;
  gateKey: string;
}

const GATE_ICONS: Record<string, string> = {
  ack_gate: '🤝',
  wrap_gate: '📦',
  rg01_gate: '🔍',
  bsrg01_gate: '🪞',
  latency_gate: '⚡',
  ledger_gate: '📜',
};

const GateCard: React.FC<GateCardProps> = ({ gate, gateKey }) => {
  const statusConfig = GATE_STATUS_CONFIG[gate.status] || GATE_STATUS_CONFIG.PENDING;
  const icon = GATE_ICONS[gateKey] || '📋';

  // Extract extra info based on gate type
  const extraInfo = React.useMemo(() => {
    const extra: string[] = [];
    if ('total' in gate && 'acknowledged' in gate) {
      extra.push(`${gate.acknowledged}/${gate.total} ACKs`);
    }
    if ('expected' in gate && 'collected' in gate) {
      extra.push(`${gate.collected}/${gate.expected} WRAPs`);
    }
    if ('reviewer' in gate) {
      extra.push(`Reviewer: ${gate.reviewer}`);
    }
    if ('threshold_ms' in gate) {
      extra.push(`Threshold: ${gate.threshold_ms}ms`);
    }
    return extra;
  }, [gate]);

  return (
    <div
      className={`${statusConfig.bgColor} border border-gray-700 rounded-lg p-4 transition-all hover:border-gray-600`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <span className="text-sm font-medium text-gray-200">{gate.name}</span>
        </div>
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bgColor} ${statusConfig.color}`}
        >
          <span>{statusConfig.icon}</span>
          <span>{statusConfig.label}</span>
        </span>
      </div>
      
      {extraInfo.length > 0 && (
        <div className="space-y-1">
          {extraInfo.map((info, idx) => (
            <div key={idx} className="text-xs text-gray-500">
              {info}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// POSITIVE CLOSURE CHECKLIST
// ═══════════════════════════════════════════════════════════════════════════════

interface PositiveClosureChecklistProps {
  conditions: GovernanceSummaryDTO['positive_closure'];
}

const PositiveClosureChecklist: React.FC<PositiveClosureChecklistProps> = ({
  conditions,
}) => {
  const items = [
    { key: 'all_wraps_pass_rg01', label: 'All Agent WRAPs pass RG-01', value: conditions.all_wraps_pass_rg01 },
    { key: 'bsrg01_attested', label: 'BSRG-01 attested', value: conditions.bsrg01_attested },
    { key: 'ber_issued', label: 'BER issued and validated', value: conditions.ber_issued },
    { key: 'ledger_committed', label: 'Ledger commit confirmed', value: conditions.ledger_committed },
  ];

  const allComplete = items.every((item) => item.value);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-400">Positive Closure Conditions</h3>
        {allComplete && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-green-900/50 text-green-400">
            ✅ All Met
          </span>
        )}
      </div>
      
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.key}
            className={`flex items-center gap-3 p-3 rounded-lg ${
              item.value ? 'bg-green-900/20 border border-green-800/50' : 'bg-gray-800 border border-gray-700'
            }`}
          >
            <span className={item.value ? 'text-green-400' : 'text-gray-500'}>
              {item.value ? '☑' : '☐'}
            </span>
            <span className={`text-sm ${item.value ? 'text-green-400' : 'text-gray-400'}`}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// SCHEMA REFERENCES
// ═══════════════════════════════════════════════════════════════════════════════

interface SchemaReferencesProps {
  schemas: GovernanceSummaryDTO['schema_references'];
}

const SchemaReferences: React.FC<SchemaReferencesProps> = ({ schemas }) => {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 space-y-2">
      <h4 className="text-xs font-medium text-gray-400 uppercase">Schema References</h4>
      <div className="grid grid-cols-3 gap-4 text-xs">
        <div>
          <span className="text-gray-500">PAC: </span>
          <span className="text-blue-400 font-mono">{schemas.pac}</span>
        </div>
        <div>
          <span className="text-gray-500">WRAP: </span>
          <span className="text-purple-400 font-mono">{schemas.wrap}</span>
        </div>
        <div>
          <span className="text-gray-500">BER: </span>
          <span className="text-green-400 font-mono">{schemas.ber}</span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface GovernanceSummaryDashboardProps {
  data: GovernanceSummaryDTO;
  className?: string;
}

export const GovernanceSummaryDashboard: React.FC<GovernanceSummaryDashboardProps> = ({
  data,
  className = '',
}) => {
  const lifecycleConfig = LIFECYCLE_STATE_CONFIG[data.lifecycle_state];
  const settlementConfig = SETTLEMENT_CONFIG[data.settlement_eligibility];

  return (
    <div className={`bg-gray-900 rounded-lg p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span>🏛️</span>
            <span>Governance Summary</span>
          </h2>
          <p className="text-sm text-gray-400 mt-1">{data.pac_title}</p>
          <p className="text-xs text-gray-500 mt-1">PAC ID: {data.pac_id}</p>
        </div>
        <div className="text-right space-y-2">
          <div className="text-xs text-gray-500">Governance Tier</div>
          <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-900/50 text-blue-400">
            {data.governance_tier}
          </span>
        </div>
      </div>

      {/* Fail Mode Banner */}
      <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-3 flex items-center gap-3">
        <span className="text-red-400">🛡️</span>
        <div>
          <span className="text-sm font-medium text-red-400">Fail Mode: </span>
          <span className="text-sm text-red-300">{data.fail_mode}</span>
        </div>
      </div>

      {/* Status Row */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2">Lifecycle State</div>
          <div className="flex items-center gap-2">
            <span>{lifecycleConfig.icon}</span>
            <span className={`text-sm font-medium ${lifecycleConfig.color}`}>
              {lifecycleConfig.label}
            </span>
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-2">Settlement Eligibility</div>
          <div className="flex items-center gap-2">
            <span>{settlementConfig.icon}</span>
            <span className={`text-sm font-medium ${settlementConfig.color}`}>
              {settlementConfig.label}
            </span>
          </div>
        </div>
      </div>

      {/* Gates Grid */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-400">Governance Gates</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Object.entries(data.gates).map(([key, gate]) => (
            <GateCard key={key} gateKey={key} gate={gate} />
          ))}
        </div>
      </div>

      {/* Positive Closure */}
      <PositiveClosureChecklist conditions={data.positive_closure} />

      {/* Schema References */}
      <SchemaReferences schemas={data.schema_references} />
    </div>
  );
};

export default GovernanceSummaryDashboard;
