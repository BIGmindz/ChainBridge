/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Operator Happy Path Demo
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Canonical demo flow: INTAKE → RISK → DECISION → SETTLEMENT → PROOF
 * 
 * DOCTRINE REFERENCES:
 * - Law 2: Cockpit Visibility
 * - Law 4: PDO Lifecycle
 * - Law 6: Visual Invariants
 * - Law 8: ProofPack Completeness
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * UX: LIRA (GID-09) — Accessibility & Cognitive Load
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import { DemoStepProgress, DemoStepList } from './DemoStepIndicator';
import { DemoBeaconGroup } from './DemoStateBeacon';
import type { DemoStep, DemoFlow, StateBeacon, OperatorDemoPhase } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// DEMO FLOW CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const HAPPY_PATH_STEPS: DemoStep[] = [
  {
    stepId: 'intake',
    label: 'Intake',
    description: 'Shipment received and validated',
    status: 'pending',
    component: 'IntakeView',
    durationMs: 2000,
    doctrineRef: 'Law 2 §2.1',
  },
  {
    stepId: 'risk-assessment',
    label: 'Risk Assessment',
    description: 'ChainIQ risk scoring completed',
    status: 'pending',
    component: 'RiskView',
    durationMs: 3000,
    doctrineRef: 'Law 2 §2.2',
  },
  {
    stepId: 'decision',
    label: 'Decision',
    description: 'Automated approval (PDO generated)',
    status: 'pending',
    component: 'DecisionView',
    durationMs: 2000,
    doctrineRef: 'Law 4 §4.1',
  },
  {
    stepId: 'settlement',
    label: 'Settlement',
    description: 'ChainPay settlement executed',
    status: 'pending',
    component: 'SettlementView',
    durationMs: 3000,
    doctrineRef: 'Law 4 §4.2',
  },
  {
    stepId: 'proof',
    label: 'ProofPack',
    description: 'Cryptographic proof generated',
    status: 'pending',
    component: 'ProofPackView',
    durationMs: 2000,
    doctrineRef: 'Law 8 §8.1',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE VIEWS
// ═══════════════════════════════════════════════════════════════════════════════

const IntakeView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">📦 Shipment Intake</h3>
    <div className="space-y-3">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Shipment ID:</span>
        <span className="text-gray-200 font-mono">SHIP-2026-0102-001</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Origin:</span>
        <span className="text-gray-200">Los Angeles, CA</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Destination:</span>
        <span className="text-gray-200">Mexico City, MX</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Value:</span>
        <span className="text-gray-200">$125,000 USD</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Status:</span>
        <span className="text-green-400">✓ Validated</span>
      </div>
    </div>
  </div>
);

const RiskView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">🎯 ChainIQ Risk Assessment</h3>
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-full bg-green-600 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">92</span>
        </div>
        <div>
          <div className="text-sm text-gray-400">Trust Score</div>
          <div className="text-green-400 font-medium">Low Risk</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="bg-gray-700 rounded p-2">
          <div className="text-gray-400">Counterparty</div>
          <div className="text-green-400">✓ Verified</div>
        </div>
        <div className="bg-gray-700 rounded p-2">
          <div className="text-gray-400">Route</div>
          <div className="text-green-400">✓ Approved</div>
        </div>
        <div className="bg-gray-700 rounded p-2">
          <div className="text-gray-400">Compliance</div>
          <div className="text-green-400">✓ Clear</div>
        </div>
        <div className="bg-gray-700 rounded p-2">
          <div className="text-gray-400">Insurance</div>
          <div className="text-green-400">✓ Active</div>
        </div>
      </div>
    </div>
  </div>
);

const DecisionView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">⚖️ Automated Decision</h3>
    <div className="space-y-3">
      <div className="bg-green-900/30 border border-green-700 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-400 font-medium">
          <span>✓</span>
          <span>APPROVED</span>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          All governance checks passed. No intervention required.
        </p>
      </div>
      <div className="text-sm space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">PDO ID:</span>
          <span className="text-gray-200 font-mono">PDO-2026-0102-001</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Decision Agent:</span>
          <span className="text-gray-200">BENSON (GID-00)</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Invariants Checked:</span>
          <span className="text-gray-200">12/12 ✓</span>
        </div>
      </div>
    </div>
  </div>
);

const SettlementView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">💰 ChainPay Settlement</h3>
    <div className="space-y-4">
      <div className="bg-gray-700 rounded-lg p-4">
        <div className="text-center">
          <div className="text-3xl font-bold text-green-400">$125,000</div>
          <div className="text-sm text-gray-400 mt-1">USD → MXN</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-gray-400">Exchange Rate</div>
          <div className="text-gray-200">17.2450</div>
        </div>
        <div>
          <div className="text-gray-400">Settlement</div>
          <div className="text-green-400">✓ Complete</div>
        </div>
        <div>
          <div className="text-gray-400">Corridor</div>
          <div className="text-gray-200">P0 (Primary)</div>
        </div>
        <div>
          <div className="text-gray-400">Fees</div>
          <div className="text-gray-200">0.15%</div>
        </div>
      </div>
    </div>
  </div>
);

const ProofPackView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">📜 ProofPack Generated</h3>
    <div className="space-y-4">
      <div className="bg-green-900/20 border border-green-700 rounded-lg p-4 text-center">
        <div className="text-4xl mb-2">✓</div>
        <div className="text-green-400 font-medium">Cryptographically Signed</div>
        <div className="text-xs text-gray-400 mt-1">Ed25519 Signature</div>
      </div>
      <div className="text-sm space-y-2">
        <div className="flex justify-between">
          <span className="text-gray-400">ProofPack ID:</span>
          <span className="text-gray-200 font-mono text-xs">PP-2026-0102-001</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Hash:</span>
          <span className="text-gray-200 font-mono text-xs">sha256:4fde46...</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Events:</span>
          <span className="text-gray-200">5 audit events</span>
        </div>
      </div>
      <button className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm">
        ⬇ Download ProofPack
      </button>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface OperatorHappyPathProps {
  onComplete?: () => void;
  autoPlay?: boolean;
}

export const OperatorHappyPath: React.FC<OperatorHappyPathProps> = ({
  onComplete,
  autoPlay = false,
}) => {
  const [steps, setSteps] = useState<DemoStep[]>(HAPPY_PATH_STEPS);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(autoPlay);

  // System beacons
  const beacons: StateBeacon[] = [
    { beaconId: 'governance', label: 'Governance', status: 'green', tooltip: 'All invariants passing' },
    { beaconId: 'settlement', label: 'Settlement', status: 'green', tooltip: 'ChainPay online' },
    { beaconId: 'risk', label: 'Risk Engine', status: 'green', tooltip: 'ChainIQ operational' },
  ];

  const advanceStep = useCallback(() => {
    if (currentIndex >= steps.length - 1) {
      setIsPlaying(false);
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
    setSteps(HAPPY_PATH_STEPS.map((step, i) => ({
      ...step,
      status: i === 0 ? 'active' : 'pending',
    })));
    setCurrentIndex(0);
    setIsPlaying(true);
  }, []);

  const resetDemo = useCallback(() => {
    setSteps(HAPPY_PATH_STEPS);
    setCurrentIndex(0);
    setIsPlaying(false);
  }, []);

  // Get current phase view
  const renderPhaseView = () => {
    const views = [IntakeView, RiskView, DecisionView, SettlementView, ProofPackView];
    return views.map((View, index) => (
      <View key={index} isActive={index === currentIndex} />
    ));
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-100">
              🚀 Operator Happy Path
            </h2>
            <p className="text-sm text-gray-400">
              INTAKE → RISK → DECISION → SETTLEMENT → PROOF
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
          onStepClick={(index) => {
            if (steps[index].status !== 'pending') {
              setCurrentIndex(index);
            }
          }}
        />
      </div>

      {/* Content Grid */}
      <div className="p-6 grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {renderPhaseView()}
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
            {currentIndex === 0 && !isPlaying ? (
              <button
                onClick={startDemo}
                className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
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

export default OperatorHappyPath;
