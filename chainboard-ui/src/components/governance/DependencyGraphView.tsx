// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Dependency Graph Visualization
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type { DependencyDTO, DependencyGraphDTO, DependencyStatus } from '../../types/governance';

interface DependencyGraphViewProps {
  graph: DependencyGraphDTO;
}

/**
 * Get status color for dependency.
 */
function getStatusColor(status: DependencyStatus): string {
  switch (status) {
    case 'SATISFIED':
      return 'bg-green-100 text-green-800 border-green-300';
    case 'PENDING':
      return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 'FAILED':
      return 'bg-red-100 text-red-800 border-red-300';
    case 'SKIPPED':
      return 'bg-gray-100 text-gray-600 border-gray-300';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300';
  }
}

/**
 * Get dependency type badge style.
 */
function getTypeStyle(isBlocking: boolean): string {
  return isBlocking
    ? 'bg-red-500 text-white'
    : 'bg-blue-500 text-white';
}

/**
 * Dependency item component.
 */
const DependencyItem: React.FC<{ dep: DependencyDTO }> = ({ dep }) => {
  return (
    <div className={`border rounded-md p-3 ${getStatusColor(dep.status)}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium ${getTypeStyle(dep.is_blocking)}`}
          >
            {dep.dependency_type}
          </span>
          <span className="text-xs opacity-60">{dep.dependency_id}</span>
        </div>
        <span className="text-xs font-medium">{dep.status}</span>
      </div>

      {/* Dependency arrow */}
      <div className="flex items-center gap-2 text-sm mb-2">
        <span className="font-mono bg-white/50 px-2 py-0.5 rounded">
          {dep.source_order_id}
        </span>
        <span className="text-gray-400">→</span>
        <span className="font-mono bg-white/50 px-2 py-0.5 rounded">
          {dep.dependent_order_id}
        </span>
      </div>

      {/* Description */}
      <p className="text-xs opacity-75">{dep.description}</p>

      {/* Failure action */}
      {dep.is_blocking && (
        <p className="mt-1 text-xs text-red-700">
          On failure: {dep.on_failure_action}
        </p>
      )}
    </div>
  );
};

/**
 * Execution order visualization.
 */
const ExecutionOrder: React.FC<{ order: string[] }> = ({ order }) => {
  if (order.length === 0) return null;

  return (
    <div className="bg-gray-50 rounded-md p-3 mt-4">
      <h4 className="text-sm font-medium text-gray-700 mb-2">Execution Order</h4>
      <div className="flex flex-wrap items-center gap-2">
        {order.map((orderId, index) => (
          <React.Fragment key={orderId}>
            <span className="px-2 py-1 bg-white border border-gray-200 rounded text-xs font-mono">
              {index + 1}. {orderId}
            </span>
            {index < order.length - 1 && (
              <span className="text-gray-400">→</span>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

/**
 * Dependency graph visualization component.
 */
export const DependencyGraphView: React.FC<DependencyGraphViewProps> = ({ graph }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Dependency Graph
        </h3>
        <span className="text-sm text-gray-500">PAC: {graph.pac_id}</span>
      </div>

      {/* Summary badges */}
      <div className="flex gap-2 mb-4">
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {graph.total_dependencies} total
        </span>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          ✓ {graph.satisfied_count} satisfied
        </span>
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          ⏳ {graph.pending_count} pending
        </span>
        {graph.failed_count > 0 && (
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
            ✗ {graph.failed_count} failed
          </span>
        )}
      </div>

      {/* Dependencies list */}
      <div className="space-y-2">
        {graph.dependencies.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No dependencies declared</p>
        ) : (
          graph.dependencies.map((dep) => (
            <DependencyItem key={dep.dependency_id} dep={dep} />
          ))
        )}
      </div>

      {/* Execution order */}
      <ExecutionOrder order={graph.execution_order} />

      {/* INV-GOV-002 notice */}
      <div className="mt-4 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
        <strong>INV-GOV-002:</strong> No execution without declared dependencies
      </div>
    </div>
  );
};

export default DependencyGraphView;
