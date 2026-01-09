/**
 * TraceView Component
 * PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
 * 
 * Full end-to-end trace visualization: PDO → Agent → Settlement → Ledger.
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-TRACE-004: OC renders full chain without inference
 * - INV-TRACE-005: Missing links are explicit and non-silent
 */

import React, { useState } from 'react';
import type {
  OCTraceView,
  TraceDecisionNode,
  TraceExecutionNode,
  TraceSettlementNode,
  TraceLedgerNode,
  TraceDomain,
} from '../../types/trace';

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN STYLING
// ═══════════════════════════════════════════════════════════════════════════════

const DOMAIN_CONFIG: Record<TraceDomain, { 
  title: string;
  icon: string;
  bg: string;
  border: string;
  text: string;
}> = {
  DECISION: {
    title: 'Decision',
    icon: '📋',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    text: 'text-purple-800',
  },
  EXECUTION: {
    title: 'Execution',
    icon: '⚙️',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-800',
  },
  SETTLEMENT: {
    title: 'Settlement',
    icon: '✅',
    bg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-green-800',
  },
  LEDGER: {
    title: 'Ledger',
    icon: '📒',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface TraceViewProps {
  traceView: OCTraceView;
  onNodeClick?: (domain: TraceDomain, nodeId: string) => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// NODE CARD COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface DecisionNodeCardProps {
  node: TraceDecisionNode;
  onClick?: () => void;
}

const DecisionNodeCard: React.FC<DecisionNodeCardProps> = ({ node, onClick }) => {
  const config = DOMAIN_CONFIG.DECISION;
  const isMissing = node.status === 'MISSING';

  return (
    <div
      className={`p-3 rounded-lg border ${config.border} ${config.bg} ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      } ${isMissing ? 'opacity-50 border-dashed' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-2">
        <span>{config.icon}</span>
        <span className={`text-sm font-medium ${config.text}`}>
          {isMissing ? 'Missing Decision' : 'Decision'}
        </span>
        {!isMissing && (
          <span className="ml-auto text-xs bg-purple-200 text-purple-800 px-2 py-0.5 rounded">
            {Math.round(node.confidence_score * 100)}% conf
          </span>
        )}
      </div>
      {!isMissing && (
        <>
          <p className="text-xs text-gray-600 mb-1 truncate">
            ID: {node.decision_id}
          </p>
          <p className="text-sm text-gray-800 line-clamp-2">
            {node.summary}
          </p>
          <div className="mt-2 text-xs text-gray-500">
            {node.factor_count} decision factors
          </div>
        </>
      )}
    </div>
  );
};

interface ExecutionNodeCardProps {
  node: TraceExecutionNode;
  onClick?: () => void;
}

const ExecutionNodeCard: React.FC<ExecutionNodeCardProps> = ({ node, onClick }) => {
  const config = DOMAIN_CONFIG.EXECUTION;

  return (
    <div
      className={`p-3 rounded-lg border ${config.border} ${config.bg} ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-2">
        <span>{config.icon}</span>
        <span className={`text-sm font-medium ${config.text}`}>Execution</span>
        <span className={`ml-auto text-xs px-2 py-0.5 rounded ${
          node.agent_state === 'COMPLETE' ? 'bg-green-200 text-green-800' :
          node.agent_state === 'FAILED' ? 'bg-red-200 text-red-800' :
          node.agent_state === 'ACTIVE' ? 'bg-blue-200 text-blue-800' :
          'bg-gray-200 text-gray-800'
        }`}>
          {node.agent_state}
        </span>
      </div>
      <p className="text-xs text-gray-600 mb-1">
        Agent: {node.agent_name} ({node.agent_gid || 'N/A'})
      </p>
      {node.duration_ms !== null && (
        <p className="text-xs text-gray-500">
          Duration: {node.duration_ms}ms
        </p>
      )}
    </div>
  );
};

interface SettlementNodeCardProps {
  node: TraceSettlementNode;
  onClick?: () => void;
}

const SettlementNodeCard: React.FC<SettlementNodeCardProps> = ({ node, onClick }) => {
  const config = DOMAIN_CONFIG.SETTLEMENT;

  return (
    <div
      className={`p-3 rounded-lg border ${config.border} ${config.bg} ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-2">
        <span>{config.icon}</span>
        <span className={`text-sm font-medium ${config.text}`}>Settlement</span>
      </div>
      <p className="text-xs text-gray-600 mb-1 truncate">
        ID: {node.settlement_id}
      </p>
      <p className="text-sm text-gray-800">
        Status: {node.outcome_status}
      </p>
      {node.settled_at && (
        <p className="text-xs text-gray-500 mt-1">
          Settled: {new Date(node.settled_at).toLocaleString()}
        </p>
      )}
    </div>
  );
};

interface LedgerNodeCardProps {
  node: TraceLedgerNode;
  onClick?: () => void;
}

const LedgerNodeCard: React.FC<LedgerNodeCardProps> = ({ node, onClick }) => {
  const config = DOMAIN_CONFIG.LEDGER;

  return (
    <div
      className={`p-3 rounded-lg border ${config.border} ${config.bg} ${
        onClick ? 'cursor-pointer hover:shadow-md' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 mb-2">
        <span>{config.icon}</span>
        <span className={`text-sm font-medium ${config.text}`}>Ledger Entry</span>
        <span className="ml-auto text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded">
          #{node.sequence_number}
        </span>
      </div>
      <p className="text-xs text-gray-600 mb-1">
        Type: {node.entry_type}
      </p>
      <p className="text-xs font-mono text-gray-500 truncate">
        Hash: {node.entry_hash.slice(0, 16)}...
      </p>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CONNECTOR LINE
// ═══════════════════════════════════════════════════════════════════════════════

interface ConnectorProps {
  hasGap?: boolean;
}

const Connector: React.FC<ConnectorProps> = ({ hasGap }) => (
  <div className="flex items-center justify-center py-2">
    <div className={`h-8 w-0.5 ${hasGap ? 'border-l-2 border-dashed border-amber-400' : 'bg-gray-300'}`} />
    <span className="absolute text-lg">↓</span>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN SECTION
// ═══════════════════════════════════════════════════════════════════════════════

interface DomainSectionProps {
  domain: TraceDomain;
  children: React.ReactNode;
  nodeCount: number;
}

const DomainSection: React.FC<DomainSectionProps> = ({ domain, children, nodeCount }) => {
  const config = DOMAIN_CONFIG[domain];

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span>{config.icon}</span>
        <h4 className={`text-sm font-semibold ${config.text}`}>
          {config.title}
        </h4>
        <span className="text-xs text-gray-500">
          ({nodeCount} node{nodeCount !== 1 ? 's' : ''})
        </span>
      </div>
      <div className="grid gap-2">
        {children}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const TraceView: React.FC<TraceViewProps> = ({ traceView, onNodeClick }) => {
  const [selectedDomain, setSelectedDomain] = useState<TraceDomain | null>(null);

  const handleNodeClick = (domain: TraceDomain, nodeId: string) => {
    if (onNodeClick) {
      onNodeClick(domain, nodeId);
    }
    setSelectedDomain(domain);
  };

  // Check for gaps between domains
  const hasDecisionToExecutionGap = 
    traceView.decision_nodes.length > 0 && 
    traceView.execution_nodes.length === 0;
  const hasExecutionToSettlementGap = 
    traceView.execution_nodes.length > 0 && 
    traceView.settlement_nodes.length === 0;
  const hasSettlementToLedgerGap = 
    traceView.settlement_nodes.length > 0 && 
    traceView.ledger_nodes.length === 0;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">
            End-to-End Trace View
          </h3>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-1 rounded ${
              traceView.status === 'COMPLETE' ? 'bg-green-100 text-green-800' :
              traceView.status === 'INCOMPLETE' ? 'bg-amber-100 text-amber-800' :
              'bg-red-100 text-red-800'
            }`}>
              {traceView.status}
            </span>
            <span className="text-xs text-gray-500">
              {Math.round(traceView.completeness_score * 100)}% complete
            </span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          PDO: {traceView.pdo_id} • PAC: {traceView.pac_id}
        </p>
      </div>

      {/* Trace Chain */}
      <div className="p-4">
        {/* Decision Phase */}
        <DomainSection domain="DECISION" nodeCount={traceView.decision_nodes.length}>
          {traceView.decision_nodes.map((node) => (
            <DecisionNodeCard
              key={node.node_id}
              node={node}
              onClick={() => handleNodeClick('DECISION', node.node_id)}
            />
          ))}
        </DomainSection>

        <Connector hasGap={hasDecisionToExecutionGap} />

        {/* Execution Phase */}
        <DomainSection domain="EXECUTION" nodeCount={traceView.execution_nodes.length}>
          {traceView.execution_nodes.length > 0 ? (
            traceView.execution_nodes.map((node) => (
              <ExecutionNodeCard
                key={node.node_id}
                node={node}
                onClick={() => handleNodeClick('EXECUTION', node.node_id)}
              />
            ))
          ) : (
            <div className="p-3 text-center text-gray-400 border-2 border-dashed rounded-lg">
              No execution data
            </div>
          )}
        </DomainSection>

        <Connector hasGap={hasExecutionToSettlementGap} />

        {/* Settlement Phase */}
        <DomainSection domain="SETTLEMENT" nodeCount={traceView.settlement_nodes.length}>
          {traceView.settlement_nodes.length > 0 ? (
            traceView.settlement_nodes.map((node) => (
              <SettlementNodeCard
                key={node.node_id}
                node={node}
                onClick={() => handleNodeClick('SETTLEMENT', node.node_id)}
              />
            ))
          ) : (
            <div className="p-3 text-center text-gray-400 border-2 border-dashed rounded-lg">
              No settlement data
            </div>
          )}
        </DomainSection>

        <Connector hasGap={hasSettlementToLedgerGap} />

        {/* Ledger Phase */}
        <DomainSection domain="LEDGER" nodeCount={traceView.ledger_nodes.length}>
          {traceView.ledger_nodes.length > 0 ? (
            traceView.ledger_nodes.map((node) => (
              <LedgerNodeCard
                key={node.node_id}
                node={node}
                onClick={() => handleNodeClick('LEDGER', node.node_id)}
              />
            ))
          ) : (
            <div className="p-3 text-center text-gray-400 border-2 border-dashed rounded-lg">
              No ledger data
            </div>
          )}
        </DomainSection>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-400 flex justify-between">
        <span>Aggregated: {new Date(traceView.aggregated_at).toLocaleString()}</span>
        <span>v{traceView.aggregator_version}</span>
      </div>
    </div>
  );
};

export default TraceView;
