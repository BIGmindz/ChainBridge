/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Operator Intervention Path Demo
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Canonical demo flow: BLOCKED → REVIEW → RESOLUTION
 * 
 * DOCTRINE REFERENCES:
 * - Law 2: Cockpit Visibility
 * - Law 4: PDO Lifecycle (intervention path)
 * - Law 6: Visual Invariants (YELLOW/RED states)
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * UX: LIRA (GID-09) — Accessibility & Cognitive Load
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import { DemoStepProgress } from './DemoStepIndicator';
import { DemoBeaconGroup } from './DemoStateBeacon';
import type { DemoStep, StateBeacon } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// INTERVENTION STEPS
// ═══════════════════════════════════════════════════════════════════════════════

const INTERVENTION_STEPS: DemoStep[] = [
  {
    stepId: 'blocked',
    label: 'Blocked',
    description: 'Transaction flagged for review',
    status: 'pending',
    component: 'BlockedView',
    doctrineRef: 'Law 4 §4.3',
  },
  {
    stepId: 'review',
    label: 'Human Review',
    description: 'Operator reviewing decision',
    status: 'pending',
    component: 'ReviewView',
    doctrineRef: 'Law 2 §2.3',
  },
  {
    stepId: 'resolution',
    label: 'Resolution',
    description: 'Decision made with audit trail',
    status: 'pending',
    component: 'ResolutionView',
    doctrineRef: 'Law 4 §4.4',
  },
  {
    stepId: 'proof',
    label: 'ProofPack',
    description: 'Intervention recorded in proof',
    status: 'pending',
    component: 'ProofPackView',
    doctrineRef: 'Law 8 §8.2',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE VIEWS
// ═══════════════════════════════════════════════════════════════════════════════

const BlockedView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border-2 ${isActive ? 'border-red-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-red-400 mb-4">🚫 Transaction Blocked</h3>
    <div className="space-y-4">
      <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-400 font-medium">
          <span>⚠</span>
          <span>REQUIRES REVIEW</span>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          Automated approval blocked due to policy violation.
        </p>
      </div>

      <div className="text-sm space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">Shipment ID:</span>
          <span className="text-gray-200 font-mono">SHIP-2026-0102-002</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Value:</span>
          <span className="text-gray-200">$875,000 USD</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Block Reason:</span>
          <span className="text-red-400">Exceeds auto-approval limit</span>
        </div>
      </div>

      <div className="bg-yellow-900/20 border border-yellow-700 rounded p-3">
        <div className="text-xs text-yellow-400 font-medium">INVARIANT TRIGGERED</div>
        <div className="text-xs text-gray-400 mt-1">
          INV-LIMIT-001: Transaction value exceeds $500,000 auto-approval threshold
        </div>
      </div>
    </div>
  </div>
);

const ReviewView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border-2 ${isActive ? 'border-yellow-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-yellow-400 mb-4">👁 Human Review Required</h3>
    <div className="space-y-4">
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Decision Context</h4>
        <div className="text-sm space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-400">Risk Score:</span>
            <span className="text-yellow-400">68 (Medium)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Counterparty:</span>
            <span className="text-green-400">✓ Verified</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Compliance:</span>
            <span className="text-green-400">✓ Clear</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Insurance:</span>
            <span className="text-yellow-400">⚠ Partial</span>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-300">Operator Actions</h4>
        <div className="flex gap-2">
          <button className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white rounded text-sm">
            ✓ Approve
          </button>
          <button className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm">
            ✗ Reject
          </button>
          <button className="flex-1 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-sm">
            ↑ Escalate
          </button>
        </div>
      </div>

      <div className="bg-gray-700 rounded p-3">
        <label className="text-xs text-gray-400 block mb-1">Justification (Required)</label>
        <textarea 
          className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm text-gray-200"
          rows={2}
          placeholder="Enter reason for decision..."
        />
      </div>
    </div>
  </div>
);

const ResolutionView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border-2 ${isActive ? 'border-green-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-green-400 mb-4">✓ Resolution Complete</h3>
    <div className="space-y-4">
      <div className="bg-green-900/30 border border-green-700 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-400 font-medium">
          <span>✓</span>
          <span>APPROVED WITH OVERRIDE</span>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          Human operator approved transaction with documented justification.
        </p>
      </div>

      <div className="text-sm space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">Decision By:</span>
          <span className="text-gray-200">operator@chainbridge.io</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Override Type:</span>
          <span className="text-yellow-400">Limit Exception</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Audit ID:</span>
          <span className="text-gray-200 font-mono text-xs">AUD-2026-0102-002</span>
        </div>
      </div>

      <div className="bg-gray-700 rounded p-3">
        <div className="text-xs text-gray-400 mb-1">Justification Recorded</div>
        <div className="text-sm text-gray-200">
          "Approved per executive authorization. Customer has 5-year relationship with 
          zero incidents. Additional verification completed via secure channel."
        </div>
      </div>
    </div>
  </div>
);

const InterventionProofView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">📜 Intervention ProofPack</h3>
    <div className="space-y-4">
      <div className="bg-purple-900/20 border border-purple-700 rounded-lg p-4 text-center">
        <div className="text-4xl mb-2">📋</div>
        <div className="text-purple-400 font-medium">Full Audit Trail</div>
        <div className="text-xs text-gray-400 mt-1">Including human intervention record</div>
      </div>

      <div className="text-sm space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">ProofPack ID:</span>
          <span className="text-gray-200 font-mono text-xs">PP-2026-0102-002</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Events:</span>
          <span className="text-gray-200">8 audit events</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Includes:</span>
          <span className="text-yellow-400">Override Record</span>
        </div>
      </div>

      <div className="bg-gray-700 rounded p-3 text-xs">
        <div className="text-gray-400 mb-1">Event Chain:</div>
        <div className="space-y-1 text-gray-300">
          <div>1. INTAKE → Shipment received</div>
          <div>2. RISK → Score: 68 (Medium)</div>
          <div className="text-red-400">3. BLOCKED → Limit exceeded</div>
          <div className="text-yellow-400">4. REVIEW → Human assigned</div>
          <div className="text-green-400">5. APPROVED → With override</div>
          <div>6. SETTLEMENT → Complete</div>
          <div>7. PROOF → Signed</div>
        </div>
      </div>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface OperatorInterventionProps {
  onComplete?: () => void;
}

export const OperatorIntervention: React.FC<OperatorInterventionProps> = ({
  onComplete,
}) => {
  const [steps, setSteps] = useState<DemoStep[]>(INTERVENTION_STEPS);
  const [currentIndex, setCurrentIndex] = useState(0);

  // System beacons (showing intervention state)
  const beacons: StateBeacon[] = [
    { beaconId: 'governance', label: 'Governance', status: currentIndex >= 2 ? 'green' : 'yellow', tooltip: 'Override in progress' },
    { beaconId: 'review', label: 'Review Queue', status: currentIndex === 1 ? 'yellow' : 'green', tooltip: currentIndex === 1 ? '1 pending' : 'Clear' },
    { beaconId: 'audit', label: 'Audit', status: 'green', tooltip: 'Recording all events' },
  ];

  const advanceStep = useCallback(() => {
    if (currentIndex >= steps.length - 1) {
      onComplete?.();
      return;
    }

    setSteps((prev) => prev.map((step, i) => ({
      ...step,
      status: i < currentIndex + 1 ? 'completed' : i === currentIndex + 1 ? 'active' : 'pending',
    })));
    setCurrentIndex((prev) => prev + 1);
  }, [currentIndex, steps.length, onComplete]);

  const startDemo = useCallback(() => {
    setSteps(INTERVENTION_STEPS.map((step, i) => ({
      ...step,
      status: i === 0 ? 'active' : 'pending',
    })));
    setCurrentIndex(0);
  }, []);

  const resetDemo = useCallback(() => {
    setSteps(INTERVENTION_STEPS);
    setCurrentIndex(0);
  }, []);

  // Render current phase
  const renderPhaseView = () => {
    switch (currentIndex) {
      case 0: return <BlockedView isActive={true} />;
      case 1: return <ReviewView isActive={true} />;
      case 2: return <ResolutionView isActive={true} />;
      case 3: return <InterventionProofView isActive={true} />;
      default: return <BlockedView isActive={false} />;
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-100">
              ⚠️ Operator Intervention Path
            </h2>
            <p className="text-sm text-gray-400">
              BLOCKED → REVIEW → RESOLUTION → PROOF
            </p>
          </div>
          <DemoBeaconGroup beacons={beacons} />
        </div>
      </header>

      {/* Progress Bar */}
      <div className="px-6 py-4 bg-gray-850 border-b border-gray-700">
        <DemoStepProgress 
          steps={steps} 
          currentIndex={currentIndex}
        />
      </div>

      {/* Content */}
      <div className="p-6">
        <div className="max-w-xl mx-auto">
          {renderPhaseView()}
        </div>
      </div>

      {/* Controls */}
      <footer className="bg-gray-800 border-t border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-400">
            Step {currentIndex + 1} of {steps.length}
          </div>
          <div className="flex gap-2">
            <button
              onClick={resetDemo}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-sm"
            >
              Reset
            </button>
            {currentIndex === 0 && steps[0].status === 'pending' ? (
              <button
                onClick={startDemo}
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-sm"
              >
                ▶ Start Demo
              </button>
            ) : currentIndex < steps.length - 1 ? (
              <button
                onClick={advanceStep}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm"
              >
                Next Step →
              </button>
            ) : (
              <button
                onClick={onComplete}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded text-sm"
              >
                Complete ✓
              </button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default OperatorIntervention;
