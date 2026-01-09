// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust PDO Lifecycle Viewer
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY PDO lifecycle visualization.
// Displays: Proof → Decision → Outcome timeline, checkpoint markers, BER status.
//
// DATA SOURCE: PDO registry + BER pipeline
// INVARIANTS:
// - INV-UNIFORM-004: BER required for finality
// - F-INV: Finality invariants
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import type {
  PDOLifecycleViewerDTO,
  PDOLifecycleEntry,
  PDOCheckpoint,
  PDOLifecycleState,
  BERClassification,
} from '../../types/chaintrust';
import {
  PDO_STATE_COLORS,
  BER_CLASSIFICATION_COLORS,
  STATUS_COLORS,
} from '../../types/chaintrust';

interface PDOLifecycleViewerProps {
  data: PDOLifecycleViewerDTO | null;
  loading: boolean;
  error: string | null;
}

/**
 * PDO state badge.
 */
const PDOStateBadge: React.FC<{ state: PDOLifecycleState }> = ({ state }) => {
  const colorClass = PDO_STATE_COLORS[state];
  return (
    <span className={`${colorClass} text-white text-xs px-2 py-1 rounded font-medium`}>
      {state}
    </span>
  );
};

/**
 * BER classification badge.
 */
const BERBadge: React.FC<{ classification: BERClassification }> = ({ classification }) => {
  const colorClass = BER_CLASSIFICATION_COLORS[classification];
  return (
    <span className={`${colorClass} text-white text-xs px-2 py-1 rounded font-medium`}>
      BER: {classification}
    </span>
  );
};

/**
 * Checkpoint indicator in timeline.
 */
const CheckpointIndicator: React.FC<{ checkpoint: PDOCheckpoint }> = ({ checkpoint }) => {
  const statusColor = STATUS_COLORS[checkpoint.status] || STATUS_COLORS.PENDING;
  
  return (
    <div className="flex flex-col items-center">
      <div className={`w-4 h-4 rounded-full ${statusColor}`} title={checkpoint.checkpoint_name}></div>
      <div className="text-xs text-gray-500 mt-1 max-w-[60px] truncate text-center">
        {checkpoint.checkpoint_name.replace(/_/g, ' ')}
      </div>
    </div>
  );
};

/**
 * PDO lifecycle timeline visualization.
 */
const PDOTimeline: React.FC<{ checkpoints: PDOCheckpoint[] }> = ({ checkpoints }) => {
  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute top-2 left-0 right-0 h-0.5 bg-gray-700"></div>
      
      {/* Checkpoint markers */}
      <div className="flex justify-between relative">
        {checkpoints.map((cp, index) => (
          <CheckpointIndicator key={cp.checkpoint_id || index} checkpoint={cp} />
        ))}
      </div>
    </div>
  );
};

/**
 * Single PDO entry card.
 */
const PDOEntryCard: React.FC<{ pdo: PDOLifecycleEntry }> = ({ pdo }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-blue-400">{pdo.pdo_id}</span>
          <PDOStateBadge state={pdo.state} />
          {pdo.ber_id && <BERBadge classification={pdo.ber_classification} />}
        </div>
      </div>

      {/* PAC Reference */}
      <div className="text-xs text-gray-500 mb-3">
        PAC: <span className="text-gray-300 font-mono">{pdo.pac_id}</span>
      </div>

      {/* Timeline */}
      {pdo.checkpoints.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs text-gray-400 mb-2">Checkpoint Timeline</h4>
          <PDOTimeline checkpoints={pdo.checkpoints} />
        </div>
      )}

      {/* BER Details */}
      <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-gray-700">
        <div>
          <span className="text-xs text-gray-500">Execution Binding</span>
          <div className={`text-sm font-mono ${pdo.execution_binding ? 'text-green-400' : 'text-yellow-400'}`}>
            {pdo.execution_binding ? 'TRUE' : 'FALSE'}
          </div>
        </div>
        <div>
          <span className="text-xs text-gray-500">Ledger Commit</span>
          <div className={`text-sm font-mono ${pdo.ledger_commit_allowed ? 'text-green-400' : 'text-red-400'}`}>
            {pdo.ledger_commit_allowed ? 'ALLOWED' : 'FORBIDDEN'}
          </div>
        </div>
        <div>
          <span className="text-xs text-gray-500">Settlement Effect</span>
          <div className={`text-sm font-mono ${pdo.settlement_effect === 'BINDING' ? 'text-green-400' : 'text-yellow-400'}`}>
            {pdo.settlement_effect}
          </div>
        </div>
      </div>

      {/* Timestamps */}
      <div className="flex justify-between mt-3 text-xs text-gray-500">
        <span>Created: {new Date(pdo.created_at).toLocaleString()}</span>
        {pdo.finalized_at && (
          <span>Finalized: {new Date(pdo.finalized_at).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
};

/**
 * Loading skeleton.
 */
const LoadingSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-3">
    {[1, 2, 3].map((i) => (
      <div key={i} className="bg-gray-800 rounded-lg p-4">
        <div className="h-6 bg-gray-700 rounded w-48 mb-3"></div>
        <div className="h-4 bg-gray-700 rounded w-32 mb-3"></div>
        <div className="flex justify-between">
          {[1, 2, 3, 4, 5].map((j) => (
            <div key={j} className="h-8 w-8 bg-gray-700 rounded-full"></div>
          ))}
        </div>
      </div>
    ))}
  </div>
);

/**
 * PDO Lifecycle Viewer for ChainTrust.
 * Shows Proof → Decision → Outcome timeline with BER status.
 */
export const PDOLifecycleViewer: React.FC<PDOLifecycleViewerProps> = ({
  data,
  loading,
  error,
}) => {
  if (error) {
    return (
      <div className="bg-gray-900 border border-red-500 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-400 mb-2">PDO Lifecycle Error</h3>
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">PDO Lifecycle</h3>
        {!loading && data && (
          <span className="text-sm text-gray-400">
            {data.total_pdos} PDOs
          </span>
        )}
      </div>

      {/* Summary Stats */}
      {!loading && data && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-400">{data.total_pdos}</div>
            <div className="text-xs text-gray-400">Total</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-400">{data.finalized_count}</div>
            <div className="text-xs text-gray-400">Finalized</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-yellow-400">{data.pending_count}</div>
            <div className="text-xs text-gray-400">Pending</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-red-400">{data.rejected_count}</div>
            <div className="text-xs text-gray-400">Rejected</div>
          </div>
        </div>
      )}

      {/* PDO List */}
      {loading ? (
        <LoadingSkeleton />
      ) : data ? (
        <div className="max-h-[500px] overflow-y-auto">
          {data.pdos.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No PDO lifecycle entries available
            </div>
          ) : (
            data.pdos.map((pdo) => (
              <PDOEntryCard key={pdo.pdo_id} pdo={pdo} />
            ))
          )}
        </div>
      ) : null}
    </div>
  );
};

export default PDOLifecycleViewer;
