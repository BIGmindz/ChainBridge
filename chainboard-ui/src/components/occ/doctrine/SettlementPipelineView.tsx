/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Settlement Pipeline View (MANDATORY)
 * PAC-BENSON-P32: UI Implementation (Operator Experience Doctrine Apply)
 * 
 * DOCTRINE LAW 4, §4.1 — Settlement Pipeline View (MANDATORY)
 * 
 * Displays the settlement pipeline stages:
 * INTAKE → RISK → DECISION → PROOF → SETTLEMENT → AUDIT
 * 
 * Each stage shows: Status indicator, count, alert badge
 * Click-through to detail view supported
 * Real-time update (≤5s refresh)
 * 
 * INVARIANTS:
 * - INV-OCC-001: Read-only display
 * - INV-DOC-001: UI reflects backend state only
 * - INV-DOC-002: No optimistic updates without proof
 * 
 * Author: SONNY (GID-02) — UI Implementation Lead
 * Security: SAM (GID-06)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useCallback } from 'react';
import type { 
  SettlementPipelineState, 
  PipelineStage, 
  PipelineStageData,
  StageStatus 
} from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// VISUAL INVARIANTS (LAW 6, §6.1)
// ═══════════════════════════════════════════════════════════════════════════════

const STAGE_STATUS_COLORS: Record<StageStatus, { bg: string; text: string; border: string }> = {
  IDLE: { bg: 'bg-gray-800', text: 'text-gray-400', border: 'border-gray-600' },
  ACTIVE: { bg: 'bg-blue-900/30', text: 'text-blue-400', border: 'border-blue-500' },
  COMPLETE: { bg: 'bg-green-900/30', text: 'text-green-400', border: 'border-green-500' },
  BLOCKED: { bg: 'bg-red-900/30', text: 'text-red-400', border: 'border-red-500' },
  ERROR: { bg: 'bg-red-900/50', text: 'text-red-300', border: 'border-red-600' },
};

const STAGE_LABELS: Record<PipelineStage, { label: string; icon: string }> = {
  INTAKE: { label: 'Intake', icon: '📥' },
  RISK: { label: 'Risk', icon: '⚖️' },
  DECISION: { label: 'Decision', icon: '🎯' },
  PROOF: { label: 'Proof', icon: '📋' },
  SETTLEMENT: { label: 'Settlement', icon: '✅' },
  AUDIT: { label: 'Audit', icon: '📝' },
};

const STAGE_ORDER: PipelineStage[] = ['INTAKE', 'RISK', 'DECISION', 'PROOF', 'SETTLEMENT', 'AUDIT'];

// ═══════════════════════════════════════════════════════════════════════════════
// STAGE CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface StageCardProps {
  data: PipelineStageData;
  onSelect: (stage: PipelineStage) => void;
  isLast: boolean;
}

const StageCard: React.FC<StageCardProps> = ({ data, onSelect, isLast }) => {
  const colors = STAGE_STATUS_COLORS[data.status];
  const { label, icon } = STAGE_LABELS[data.stage];

  const handleClick = useCallback(() => {
    onSelect(data.stage);
  }, [data.stage, onSelect]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect(data.stage);
      }
    },
    [data.stage, onSelect]
  );

  return (
    <div className="flex items-center">
      <button
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={`
          flex flex-col items-center p-3 rounded-lg border-2 min-w-[100px]
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500
          hover:scale-105 cursor-pointer
          ${colors.bg} ${colors.border}
        `}
        aria-label={`${label} stage: ${data.count} items, ${data.alertCount} alerts`}
        role="button"
        tabIndex={0}
      >
        {/* Stage Icon & Label */}
        <div className="flex items-center gap-1.5 mb-2">
          <span aria-hidden="true">{icon}</span>
          <span className={`text-sm font-medium ${colors.text}`}>{label}</span>
        </div>

        {/* Count Badge */}
        <div className={`text-2xl font-bold ${colors.text}`}>
          {data.count}
        </div>

        {/* Alert Badge (if any) */}
        {data.alertCount > 0 && (
          <div 
            className="mt-1 px-2 py-0.5 bg-red-600 text-white text-xs font-bold rounded-full"
            role="status"
            aria-label={`${data.alertCount} alerts`}
          >
            {data.alertCount} ⚠️
          </div>
        )}

        {/* Status Indicator */}
        <div className="mt-2 flex items-center gap-1">
          <span 
            className={`w-2 h-2 rounded-full ${
              data.status === 'ACTIVE' ? 'bg-blue-500 animate-pulse' :
              data.status === 'COMPLETE' ? 'bg-green-500' :
              data.status === 'BLOCKED' ? 'bg-red-500' :
              data.status === 'ERROR' ? 'bg-red-600 animate-pulse' :
              'bg-gray-500'
            }`}
            aria-hidden="true"
          />
          <span className="text-xs text-gray-500">{data.status}</span>
        </div>
      </button>

      {/* Arrow Connector (except for last stage) */}
      {!isLast && (
        <div className="mx-2 text-gray-600" aria-hidden="true">
          →
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface SettlementPipelineViewProps {
  /** Pipeline state from backend */
  state: SettlementPipelineState | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Callback when a stage is selected */
  onStageSelect: (stage: PipelineStage) => void;
  /** Callback to refresh data */
  onRefresh: () => void;
}

export const SettlementPipelineView: React.FC<SettlementPipelineViewProps> = ({
  state,
  isLoading,
  error,
  onStageSelect,
  onRefresh,
}) => {
  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Loading State
  // ═══════════════════════════════════════════════════════════════════════════
  if (isLoading && !state) {
    return (
      <div 
        className="bg-gray-900 border border-gray-700 rounded-lg p-6"
        role="status"
        aria-live="polite"
      >
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <span className="animate-spin">⟳</span>
          <span>Loading pipeline state...</span>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Error State
  // ═══════════════════════════════════════════════════════════════════════════
  if (error) {
    return (
      <div 
        className="bg-red-900/20 border border-red-700 rounded-lg p-6"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-400">
            <span>✗</span>
            <span>Pipeline Error: {error}</span>
          </div>
          <button
            onClick={onRefresh}
            className="px-3 py-1 bg-red-700 hover:bg-red-600 text-white text-sm rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: Pipeline View
  // ═══════════════════════════════════════════════════════════════════════════
  
  // Build ordered stage data (ensure all stages present)
  const orderedStages: PipelineStageData[] = STAGE_ORDER.map((stage) => {
    const existing = state?.stages.find((s) => s.stage === stage);
    return existing ?? {
      stage,
      status: 'IDLE' as StageStatus,
      count: 0,
      alertCount: 0,
      lastUpdated: new Date().toISOString(),
    };
  });

  return (
    <section
      className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      aria-labelledby="pipeline-title"
    >
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 id="pipeline-title" className="text-lg font-semibold text-gray-100">
            Settlement Pipeline
          </h2>
          {state && (
            <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
              {state.totalInPipeline} in pipeline
            </span>
          )}
          {state && state.blockedCount > 0 && (
            <span className="px-2 py-0.5 bg-red-900/50 text-red-400 text-xs rounded">
              {state.blockedCount} blocked
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {state?.lastRefresh && (
            <span className="text-xs text-gray-500">
              Updated: {new Date(state.lastRefresh).toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className={`
              px-3 py-1.5 text-sm font-medium rounded transition-colors
              focus:outline-none focus:ring-2 focus:ring-blue-500
              ${isLoading
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            `}
            aria-label="Refresh pipeline data"
          >
            {isLoading ? '⟳ Refreshing...' : '⟳ Refresh'}
          </button>
        </div>
      </header>

      {/* Pipeline Stages */}
      <div className="p-6">
        <div 
          className="flex items-center justify-center flex-wrap gap-2"
          role="list"
          aria-label="Settlement pipeline stages"
        >
          {orderedStages.map((stageData, index) => (
            <StageCard
              key={stageData.stage}
              data={stageData}
              onSelect={onStageSelect}
              isLast={index === orderedStages.length - 1}
            />
          ))}
        </div>

        {/* Legend */}
        <div className="mt-6 flex items-center justify-center gap-6 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-gray-500" aria-hidden="true" />
            <span>Idle</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" aria-hidden="true" />
            <span>Active</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" aria-hidden="true" />
            <span>Complete</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" aria-hidden="true" />
            <span>Blocked</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SettlementPipelineView;
