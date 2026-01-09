/**
 * BSRG-01 Benson Self-Review Gate Panel — Control Plane UI
 * PAC-JEFFREY-P01: SECTION 9 — Benson Self-Review Visualization
 *
 * Displays BSRG-01 Self-Review Gate status per PAC-JEFFREY-P01:
 * - Self attestation status
 * - Violations list (NONE or list)
 * - Training signal emission status
 *
 * INVARIANTS:
 * - self_attestation: REQUIRED
 * - violations: ENUM[NONE | LIST]
 * - training_signal_emission: REQUIRED
 *
 * Author: Benson Execution Orchestrator (GID-00)
 * Frontend Lane: SONNY (GID-02)
 */

import React from 'react';
import { BSRG01DTO } from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// REQUIREMENT ROW
// ═══════════════════════════════════════════════════════════════════════════════

interface RequirementRowProps {
  label: string;
  required: boolean;
  satisfied: boolean;
  description?: string;
}

const RequirementRow: React.FC<RequirementRowProps> = ({
  label,
  required,
  satisfied,
  description,
}) => {
  return (
    <div
      className={`rounded-lg p-4 border ${
        satisfied
          ? 'bg-green-900/20 border-green-800/50'
          : 'bg-gray-800 border-gray-700'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className={satisfied ? 'text-green-400' : 'text-gray-400'}>
            {satisfied ? '✅' : '⏳'}
          </span>
          <span className="text-sm font-medium text-gray-200">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          {required && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900/50 text-red-400 uppercase">
              Required
            </span>
          )}
          <span
            className={`text-xs px-2 py-0.5 rounded ${
              satisfied
                ? 'bg-green-900/30 text-green-400'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            {satisfied ? 'Complete' : 'Pending'}
          </span>
        </div>
      </div>
      {description && (
        <p className="text-xs text-gray-500 ml-6">{description}</p>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// VIOLATIONS DISPLAY
// ═══════════════════════════════════════════════════════════════════════════════

interface ViolationsDisplayProps {
  violations: 'NONE' | string[];
}

const ViolationsDisplay: React.FC<ViolationsDisplayProps> = ({ violations }) => {
  if (violations === 'NONE') {
    return (
      <div className="bg-green-900/20 border border-green-800/50 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <span className="text-green-400">✅</span>
          <span className="text-sm font-medium text-green-400">No Violations</span>
        </div>
        <p className="text-xs text-green-500/70 mt-1 ml-6">
          Self-review found no governance violations
        </p>
      </div>
    );
  }

  return (
    <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2 text-yellow-400 text-sm font-medium">
        <span>⚠️</span>
        <span>Violations Detected ({violations.length})</span>
      </div>
      <ul className="space-y-2">
        {violations.map((violation, idx) => (
          <li key={idx} className="text-xs text-yellow-300 flex items-start gap-2">
            <span className="text-yellow-500 mt-0.5">•</span>
            <span>{violation}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// TRAINING SIGNALS DISPLAY
// ═══════════════════════════════════════════════════════════════════════════════

interface TrainingSignalsDisplayProps {
  signals: Record<string, unknown>[];
}

const TrainingSignalsDisplay: React.FC<TrainingSignalsDisplayProps> = ({
  signals,
}) => {
  if (signals.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <span>📊</span>
          <span>No training signals emitted yet</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2 text-blue-400 text-sm font-medium">
        <span>📊</span>
        <span>Training Signals ({signals.length})</span>
      </div>
      <div className="space-y-2">
        {signals.map((signal, idx) => (
          <div
            key={idx}
            className="bg-blue-900/30 rounded p-2 text-xs font-mono text-blue-300"
          >
            {JSON.stringify(signal, null, 0)}
          </div>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface BSRG01PanelProps {
  data: BSRG01DTO;
  className?: string;
}

export const BSRG01Panel: React.FC<BSRG01PanelProps> = ({
  data,
  className = '',
}) => {
  const isComplete = data.self_attestation && data.training_signals.length > 0;

  return (
    <div className={`bg-gray-900 rounded-lg p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span>🪞</span>
            <span>BSRG-01 Self-Review Gate</span>
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            PAC-JEFFREY-P01 Section 9 · Gate ID: {data.gate_id}
          </p>
        </div>
        <div>
          {isComplete ? (
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-900/50 text-green-400">
              ✅ Attested
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-900/50 text-yellow-400">
              ⏳ Pending
            </span>
          )}
        </div>
      </div>

      {/* Requirements */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-400">Requirements</h3>
        
        <RequirementRow
          label="Self Attestation"
          required={data.self_attestation_required}
          satisfied={data.self_attestation}
          description="Benson must explicitly attest to execution correctness"
        />
        
        <RequirementRow
          label="Training Signal Emission"
          required={data.training_signal_emission_required}
          satisfied={data.training_signals.length > 0}
          description="Learning signals must be emitted for continuous improvement"
        />
      </div>

      {/* Violations */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-400">Violations</h3>
        <ViolationsDisplay violations={data.violations} />
      </div>

      {/* Training Signals */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-400">Training Signals</h3>
        <TrainingSignalsDisplay signals={data.training_signals} />
      </div>

      {/* Attestation Timestamp */}
      {data.attested_at && (
        <div className="flex items-center justify-between pt-4 border-t border-gray-800 text-xs">
          <span className="text-gray-500">Attested at:</span>
          <span className="text-gray-300">
            {new Date(data.attested_at).toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
};

export default BSRG01Panel;
