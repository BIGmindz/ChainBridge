/**
 * Control Plane Console — Main Integration Component
 * PAC-CP-UI-EXEC-001: Control Plane UI for Benson Execution
 *
 * Integrates all Control Plane panels into a unified operator view.
 *
 * Author: Benson Execution Orchestrator (GID-00)
 */

import React from 'react';
import { ControlPlaneStateDTO } from '../../types/controlPlane';
import { PACLifecyclePanel } from './PACLifecyclePanel';
import { AgentACKPanel } from './AgentACKPanel';
import { WRAPValidationPanel } from './WRAPValidationPanel';
import { BERDisplayPanel } from './BERDisplayPanel';
import { SettlementEligibilityPanel } from './SettlementEligibilityPanel';

// ═══════════════════════════════════════════════════════════════════════════════
// CONTROL PLANE HEADER
// ═══════════════════════════════════════════════════════════════════════════════

interface ControlPlaneHeaderProps {
  state: ControlPlaneStateDTO | null;
  onRefresh?: () => void;
  refreshing?: boolean;
}

const ControlPlaneHeader: React.FC<ControlPlaneHeaderProps> = ({
  state,
  onRefresh,
  refreshing = false,
}) => {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🎛️</span>
          <div>
            <h1 className="text-xl font-bold text-gray-100">Control Plane</h1>
            <p className="text-xs text-gray-400">
              AI Workforce Governance — PAC Lifecycle Management
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {state && (
            <div className="text-right text-xs">
              <p className="text-gray-500">Runtime</p>
              <p className="font-mono text-gray-300">{state.runtime_id}</p>
            </div>
          )}
          
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={refreshing}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                refreshing
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {refreshing ? '⟳ Refreshing...' : '⟳ Refresh'}
            </button>
          )}
        </div>
      </div>
      
      {/* Governance Notice */}
      <div className="mt-3 pt-3 border-t border-gray-700">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>🔒</span>
          <span>
            <strong>FAIL_CLOSED Governance:</strong> 
            No execution without explicit ACK • Missing ACK blocks settlement • 
            All states auditable
          </span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CONTROL PLANE CONSOLE (MAIN COMPONENT)
// ═══════════════════════════════════════════════════════════════════════════════

interface ControlPlaneConsoleProps {
  state: ControlPlaneStateDTO | null;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const ControlPlaneConsole: React.FC<ControlPlaneConsoleProps> = ({
  state,
  loading = false,
  error = null,
  onRefresh,
}) => {
  return (
    <div className="min-h-screen bg-gray-950 p-6">
      {/* Header */}
      <ControlPlaneHeader
        state={state}
        onRefresh={onRefresh}
        refreshing={loading}
      />

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-4 bg-red-900/20 border border-red-800 rounded-lg">
          <div className="flex items-center gap-2 text-red-400">
            <span>🛑</span>
            <span className="font-medium">Control Plane Error</span>
          </div>
          <p className="mt-1 text-sm text-gray-400">{error}</p>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column: Lifecycle + ACKs */}
        <div className="space-y-4">
          <PACLifecyclePanel
            state={state}
            loading={loading}
            error={null}
          />
          <AgentACKPanel
            state={state}
            loading={loading}
            error={null}
          />
        </div>

        {/* Middle Column: WRAP + BER */}
        <div className="space-y-4">
          <WRAPValidationPanel
            state={state}
            loading={loading}
            error={null}
          />
          <BERDisplayPanel
            state={state}
            loading={loading}
            error={null}
          />
        </div>

        {/* Right Column: Settlement */}
        <div className="space-y-4">
          <SettlementEligibilityPanel
            state={state}
            loading={loading}
            error={null}
          />
          
          {/* Training Signals Panel (placeholder for BLOCK 8) */}
          <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800 bg-gray-800/50">
              <h3 className="text-sm font-medium text-gray-200">
                📊 Training Signals
              </h3>
            </div>
            <div className="p-4">
              {state ? (
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Execution Latency</span>
                    <span className="text-gray-300">
                      {state.ack_summary.latency.avg_ms 
                        ? `${state.ack_summary.latency.avg_ms}ms avg`
                        : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Agent Compliance</span>
                    <span className={state.ack_summary.rejected > 0 ? 'text-red-400' : 'text-green-400'}>
                      {state.ack_summary.total > 0
                        ? `${Math.round((state.ack_summary.acknowledged / state.ack_summary.total) * 100)}%`
                        : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Governance Failures</span>
                    <span className={
                      state.ack_summary.rejected + state.ack_summary.timeout > 0
                        ? 'text-red-400'
                        : 'text-green-400'
                    }>
                      {state.ack_summary.rejected + state.ack_summary.timeout}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">State Transitions</span>
                    <span className="text-gray-300">{state.state_transitions.length}</span>
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-4">
                  No training data available
                </div>
              )}
            </div>
            <div className="px-4 py-2 border-t border-gray-800 bg-gray-800/30">
              <p className="text-[10px] text-gray-600">
                PAC BLOCK 8: Training signals emitted for governance optimization
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-gray-800">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div className="flex items-center gap-4">
            <span>PAC-CP-UI-EXEC-001</span>
            <span>•</span>
            <span>Schema v1.1</span>
            <span>•</span>
            <span>FAIL_CLOSED</span>
          </div>
          <div>
            <span>Benson Execution Orchestrator (GID-00)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPlaneConsole;
