/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Auditor Replay Demo
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Canonical demo flow: TIMELINE → PROOFPACK → VERIFY
 * Evidence-first approach for external auditors.
 * 
 * DOCTRINE REFERENCES:
 * - Law 4, §4.3: Decision history with filtering
 * - Law 8: ProofPack Completeness
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * Auditor UX: SAM (GID-06) — Auditor Narrative Integrity
 * UX: LIRA (GID-09) — Accessibility & Cognitive Load
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import { DemoStepProgress } from './DemoStepIndicator';
import { DemoBeaconGroup } from './DemoStateBeacon';
import type { DemoStep, StateBeacon } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// AUDITOR STEPS
// ═══════════════════════════════════════════════════════════════════════════════

const AUDITOR_STEPS: DemoStep[] = [
  {
    stepId: 'timeline',
    label: 'Timeline View',
    description: 'Browse audit history',
    status: 'pending',
    component: 'TimelineView',
    doctrineRef: 'Law 4 §4.3',
  },
  {
    stepId: 'select',
    label: 'Select ProofPack',
    description: 'Choose artifact to verify',
    status: 'pending',
    component: 'SelectView',
    doctrineRef: 'Law 8 §8.1',
  },
  {
    stepId: 'verify',
    label: 'Verify Integrity',
    description: 'Cryptographic verification',
    status: 'pending',
    component: 'VerifyView',
    doctrineRef: 'Law 8 §8.2',
  },
  {
    stepId: 'evidence',
    label: 'Review Evidence',
    description: 'Examine decision trail',
    status: 'pending',
    component: 'EvidenceView',
    doctrineRef: 'Law 4 §4.4',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MOCK DATA
// ═══════════════════════════════════════════════════════════════════════════════

const MOCK_TIMELINE_ENTRIES = [
  { id: 'pp-001', type: 'DECISION', timestamp: '2026-01-02T14:30:00Z', description: 'Settlement approved - SHIP-2026-001', hasProofPack: true },
  { id: 'pp-002', type: 'VERIFICATION', timestamp: '2026-01-02T12:15:00Z', description: 'Audit bundle integrity verified', hasProofPack: false },
  { id: 'pp-003', type: 'DECISION', timestamp: '2026-01-02T10:45:00Z', description: 'Manual override - SHIP-2026-002', hasProofPack: true },
  { id: 'pp-004', type: 'EXPORT', timestamp: '2026-01-01T18:00:00Z', description: 'ProofPack exported for audit', hasProofPack: true },
  { id: 'pp-005', type: 'SYSTEM', timestamp: '2026-01-01T09:00:00Z', description: 'Gameday adversarial testing completed', hasProofPack: false },
];

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE VIEWS
// ═══════════════════════════════════════════════════════════════════════════════

const TimelineView: React.FC<{ isActive: boolean; onSelect: (id: string) => void }> = ({ isActive, onSelect }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">📜 Public Audit Timeline</h3>
    <div className="space-y-2 max-h-80 overflow-y-auto">
      {MOCK_TIMELINE_ENTRIES.map((entry) => (
        <div 
          key={entry.id}
          className={`
            flex items-center justify-between p-3 rounded
            ${entry.hasProofPack ? 'bg-gray-700 hover:bg-gray-600 cursor-pointer' : 'bg-gray-750 opacity-60'}
          `}
          onClick={() => entry.hasProofPack && onSelect(entry.id)}
          role={entry.hasProofPack ? 'button' : undefined}
          tabIndex={entry.hasProofPack ? 0 : undefined}
        >
          <div className="flex items-center gap-3">
            <span className={`
              w-8 h-8 rounded-full flex items-center justify-center text-sm
              ${entry.type === 'DECISION' ? 'bg-blue-600' : 
                entry.type === 'VERIFICATION' ? 'bg-green-600' :
                entry.type === 'EXPORT' ? 'bg-purple-600' : 'bg-gray-600'}
            `}>
              {entry.type === 'DECISION' ? '⚖' : 
               entry.type === 'VERIFICATION' ? '✓' :
               entry.type === 'EXPORT' ? '⬇' : '⚙'}
            </span>
            <div>
              <div className="text-sm text-gray-200">{entry.description}</div>
              <div className="text-xs text-gray-500">
                {new Date(entry.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
          {entry.hasProofPack && (
            <span className="text-xs text-blue-400">View ProofPack →</span>
          )}
        </div>
      ))}
    </div>
    <p className="text-xs text-gray-500 mt-4 text-center">
      Click any entry with ProofPack to verify
    </p>
  </div>
);

const SelectView: React.FC<{ isActive: boolean; selectedId: string | null }> = ({ isActive, selectedId }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">📄 ProofPack Selected</h3>
    {selectedId ? (
      <div className="space-y-4">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400">ProofPack ID:</span>
              <span className="text-gray-200 font-mono">{selectedId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Generated:</span>
              <span className="text-gray-200">2026-01-02 14:30:00</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Schema Version:</span>
              <span className="text-gray-200">1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Event Count:</span>
              <span className="text-gray-200">5 events</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Signed:</span>
              <span className="text-green-400">✓ Ed25519</span>
            </div>
          </div>
        </div>
        <div className="bg-gray-700 rounded p-3">
          <div className="text-xs text-gray-400 mb-1">Manifest Hash</div>
          <div className="font-mono text-xs text-gray-300 break-all">
            sha256:4fde4644551c35b2b27a10550130be03384e47ef...
          </div>
        </div>
      </div>
    ) : (
      <div className="text-center text-gray-500 py-8">
        No ProofPack selected
      </div>
    )}
  </div>
);

const VerifyView: React.FC<{ isActive: boolean; verifying: boolean; verified: boolean | null }> = ({ 
  isActive, verifying, verified 
}) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">🔐 Integrity Verification</h3>
    <div className="space-y-4">
      {verifying ? (
        <div className="text-center py-8">
          <div className="text-4xl animate-spin mb-4">⟳</div>
          <div className="text-yellow-400">Verifying integrity...</div>
          <div className="text-xs text-gray-500 mt-2">
            Checking hashes and signature
          </div>
        </div>
      ) : verified === null ? (
        <div className="text-center py-8 text-gray-500">
          Click "Verify" to check integrity
        </div>
      ) : verified ? (
        <div className="space-y-4">
          <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 text-center">
            <div className="text-4xl mb-2">✓</div>
            <div className="text-green-400 font-medium">VERIFIED</div>
            <div className="text-xs text-gray-400 mt-1">All integrity checks passed</div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-gray-700 rounded p-2">
              <div className="text-gray-400 text-xs">Hash</div>
              <div className="text-green-400">✓ Valid</div>
            </div>
            <div className="bg-gray-700 rounded p-2">
              <div className="text-gray-400 text-xs">Signature</div>
              <div className="text-green-400">✓ Valid</div>
            </div>
            <div className="bg-gray-700 rounded p-2">
              <div className="text-gray-400 text-xs">Algorithm</div>
              <div className="text-gray-200">SHA-256</div>
            </div>
            <div className="bg-gray-700 rounded p-2">
              <div className="text-gray-400 text-xs">Verified At</div>
              <div className="text-gray-200">{new Date().toLocaleTimeString()}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-center">
          <div className="text-4xl mb-2">✗</div>
          <div className="text-red-400 font-medium">VERIFICATION FAILED</div>
          <div className="text-xs text-gray-400 mt-1">Integrity check did not pass</div>
        </div>
      )}
    </div>
  </div>
);

const EvidenceView: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <div className={`bg-gray-800 rounded-lg p-6 border ${isActive ? 'border-blue-500' : 'border-gray-700'}`}>
    <h3 className="text-lg font-semibold text-gray-100 mb-4">📋 Evidence Review</h3>
    <div className="space-y-4">
      <div className="bg-gray-700 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Audit Event Chain</h4>
        <div className="space-y-2">
          {[
            { time: '14:30:00', event: 'PROOF_GENERATED', detail: 'ProofPack created' },
            { time: '14:29:58', event: 'SETTLEMENT_COMPLETE', detail: '$125,000 settled' },
            { time: '14:29:55', event: 'DECISION_APPROVED', detail: 'Automated approval' },
            { time: '14:29:50', event: 'RISK_ASSESSED', detail: 'Score: 92 (Low Risk)' },
            { time: '14:29:45', event: 'SHIPMENT_INTAKE', detail: 'SHIP-2026-001 received' },
          ].map((event, i) => (
            <div key={i} className="flex items-start gap-3 text-sm">
              <span className="text-gray-500 font-mono text-xs">{event.time}</span>
              <span className="text-blue-400 font-mono text-xs w-40">{event.event}</span>
              <span className="text-gray-300">{event.detail}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-purple-900/20 border border-purple-700 rounded p-3">
        <div className="text-xs text-purple-400 font-medium">EXPLAINABILITY</div>
        <div className="text-sm text-gray-300 mt-1">
          Decision approved based on: Trust Score 92 (threshold 70), verified counterparty, 
          compliant route, active insurance coverage.
        </div>
      </div>

      <button className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm">
        ⬇ Download Full ProofPack
      </button>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface AuditorReplayProps {
  onComplete?: () => void;
}

export const AuditorReplay: React.FC<AuditorReplayProps> = ({
  onComplete,
}) => {
  const [steps, setSteps] = useState<DemoStep[]>(AUDITOR_STEPS);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedProofPackId, setSelectedProofPackId] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verified, setVerified] = useState<boolean | null>(null);

  // System beacons
  const beacons: StateBeacon[] = [
    { beaconId: 'api', label: 'Trust API', status: 'green', tooltip: 'Public API online' },
    { beaconId: 'verification', label: 'Verification', status: verified ? 'green' : verifying ? 'yellow' : 'green', tooltip: 'Ready' },
  ];

  const handleSelectProofPack = useCallback((id: string) => {
    setSelectedProofPackId(id);
    setSteps((prev) => prev.map((step, i) => ({
      ...step,
      status: i === 0 ? 'completed' : i === 1 ? 'active' : 'pending',
    })));
    setCurrentIndex(1);
  }, []);

  const handleVerify = useCallback(() => {
    setVerifying(true);
    setSteps((prev) => prev.map((step, i) => ({
      ...step,
      status: i <= 1 ? 'completed' : i === 2 ? 'active' : 'pending',
    })));
    setCurrentIndex(2);

    // Simulate verification
    setTimeout(() => {
      setVerifying(false);
      setVerified(true);
    }, 2000);
  }, []);

  const handleViewEvidence = useCallback(() => {
    setSteps((prev) => prev.map((step, i) => ({
      ...step,
      status: i <= 2 ? 'completed' : i === 3 ? 'active' : 'pending',
    })));
    setCurrentIndex(3);
  }, []);

  const startDemo = useCallback(() => {
    setSteps(AUDITOR_STEPS.map((step, i) => ({
      ...step,
      status: i === 0 ? 'active' : 'pending',
    })));
    setCurrentIndex(0);
    setSelectedProofPackId(null);
    setVerified(null);
  }, []);

  const resetDemo = useCallback(() => {
    setSteps(AUDITOR_STEPS);
    setCurrentIndex(0);
    setSelectedProofPackId(null);
    setVerified(null);
    setVerifying(false);
  }, []);

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-100">
              🔍 Auditor Replay
            </h2>
            <p className="text-sm text-gray-400">
              TIMELINE → SELECT → VERIFY → EVIDENCE
            </p>
          </div>
          <DemoBeaconGroup beacons={beacons} />
        </div>
      </header>

      {/* Progress Bar */}
      <div className="px-6 py-4 bg-gray-850 border-b border-gray-700">
        <DemoStepProgress steps={steps} currentIndex={currentIndex} />
      </div>

      {/* Content Grid */}
      <div className="p-6 grid md:grid-cols-2 gap-4">
        <TimelineView 
          isActive={currentIndex === 0} 
          onSelect={handleSelectProofPack}
        />
        <SelectView 
          isActive={currentIndex === 1} 
          selectedId={selectedProofPackId}
        />
        <VerifyView 
          isActive={currentIndex === 2} 
          verifying={verifying}
          verified={verified}
        />
        <EvidenceView isActive={currentIndex === 3} />
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
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm"
              >
                ▶ Start Demo
              </button>
            ) : currentIndex === 1 && selectedProofPackId ? (
              <button
                onClick={handleVerify}
                className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
              >
                🔐 Verify Integrity
              </button>
            ) : currentIndex === 2 && verified ? (
              <button
                onClick={handleViewEvidence}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded text-sm"
              >
                📋 View Evidence
              </button>
            ) : currentIndex === 3 ? (
              <button
                onClick={onComplete}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded text-sm"
              >
                Complete ✓
              </button>
            ) : null}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AuditorReplay;
