/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Demo Experience Dashboard
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Main navigation hub for all demo flows.
 * 
 * DOCTRINE REFERENCES:
 * - Law 2: Cockpit Visibility
 * - Law 6: Visual Invariants
 * 
 * DEMO FLOWS:
 * 1. Operator Happy Path (INTAKE → SETTLEMENT → PROOF)
 * 2. Operator Intervention (BLOCKED → REVIEW)
 * 3. Auditor Replay (TIMELINE → PROOFPACK → VERIFY)
 * 4. Public Trust Center Verification
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * UX: LIRA (GID-09) — Accessibility & Cognitive Load
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback } from 'react';
import { OperatorHappyPath } from './OperatorHappyPath';
import { OperatorIntervention } from './OperatorIntervention';
import { AuditorReplay } from './AuditorReplay';
import { TrustCenterDashboard } from '../trust-center';
import { DemoBeaconGroup } from './DemoStateBeacon';
import type { DemoFlowId, StateBeacon } from './types';

// ═══════════════════════════════════════════════════════════════════════════════
// FLOW CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

interface FlowConfig {
  id: DemoFlowId;
  title: string;
  description: string;
  icon: string;
  persona: 'operator' | 'auditor' | 'public';
  color: string;
}

const DEMO_FLOWS: FlowConfig[] = [
  {
    id: 'operator-happy-path',
    title: 'Operator Happy Path',
    description: 'Complete flow: Intake → Risk → Decision → Settlement → Proof',
    icon: '🚀',
    persona: 'operator',
    color: 'green',
  },
  {
    id: 'operator-intervention',
    title: 'Operator Intervention',
    description: 'Human review flow: Blocked → Review → Resolution',
    icon: '⚠️',
    persona: 'operator',
    color: 'yellow',
  },
  {
    id: 'auditor-replay',
    title: 'Auditor Replay',
    description: 'Evidence-first: Timeline → ProofPack → Verify',
    icon: '🔍',
    persona: 'auditor',
    color: 'blue',
  },
  {
    id: 'trust-center-verify',
    title: 'Trust Center',
    description: 'Public verification interface for external auditors',
    icon: '🛡',
    persona: 'public',
    color: 'purple',
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
// FLOW CARD
// ═══════════════════════════════════════════════════════════════════════════════

interface FlowCardProps {
  flow: FlowConfig;
  onClick: () => void;
}

const FlowCard: React.FC<FlowCardProps> = ({ flow, onClick }) => {
  const colorClasses = {
    green: 'border-green-600 hover:border-green-500 hover:bg-green-900/20',
    yellow: 'border-yellow-600 hover:border-yellow-500 hover:bg-yellow-900/20',
    blue: 'border-blue-600 hover:border-blue-500 hover:bg-blue-900/20',
    purple: 'border-purple-600 hover:border-purple-500 hover:bg-purple-900/20',
  };

  const personaBadge = {
    operator: { label: 'Operator', color: 'bg-green-600' },
    auditor: { label: 'Auditor', color: 'bg-blue-600' },
    public: { label: 'Public', color: 'bg-purple-600' },
  };

  return (
    <button
      onClick={onClick}
      className={`
        w-full p-6 rounded-lg border-2 text-left transition-all
        bg-gray-800 ${colorClasses[flow.color as keyof typeof colorClasses]}
      `}
    >
      <div className="flex items-start justify-between">
        <span className="text-4xl">{flow.icon}</span>
        <span className={`text-xs px-2 py-1 rounded ${personaBadge[flow.persona].color} text-white`}>
          {personaBadge[flow.persona].label}
        </span>
      </div>
      <h3 className="text-lg font-semibold text-gray-100 mt-4">{flow.title}</h3>
      <p className="text-sm text-gray-400 mt-1">{flow.description}</p>
    </button>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const DemoExperienceDashboard: React.FC = () => {
  const [activeFlow, setActiveFlow] = useState<DemoFlowId | null>(null);

  // System beacons
  const beacons: StateBeacon[] = [
    { beaconId: 'system', label: 'System', status: 'green', tooltip: 'All systems operational' },
    { beaconId: 'governance', label: 'Governance', status: 'green', tooltip: 'Fail-closed active' },
    { beaconId: 'demo', label: 'Demo Mode', status: 'green', tooltip: 'Demo mode enabled' },
  ];

  const handleFlowComplete = useCallback(() => {
    setActiveFlow(null);
  }, []);

  const handleBack = useCallback(() => {
    setActiveFlow(null);
  }, []);

  // Render active flow
  if (activeFlow) {
    return (
      <div className="min-h-screen bg-gray-950">
        {/* Back Navigation */}
        <nav className="bg-gray-900 border-b border-gray-700 px-6 py-3">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <span>←</span>
            <span>Back to Demo Hub</span>
          </button>
        </nav>

        {/* Active Flow Content */}
        <main className="p-6">
          {activeFlow === 'operator-happy-path' && (
            <OperatorHappyPath onComplete={handleFlowComplete} />
          )}
          {activeFlow === 'operator-intervention' && (
            <OperatorIntervention onComplete={handleFlowComplete} />
          )}
          {activeFlow === 'auditor-replay' && (
            <AuditorReplay onComplete={handleFlowComplete} />
          )}
          {activeFlow === 'trust-center-verify' && (
            <TrustCenterDashboard />
          )}
        </main>
      </div>
    );
  }

  // Render flow selection hub
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-700 px-6 py-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-100">
                ChainBridge Demo Experience
              </h1>
              <p className="text-gray-400 mt-1">
                Explore canonical operator and auditor workflows
              </p>
            </div>
            <DemoBeaconGroup beacons={beacons} />
          </div>
        </div>
      </header>

      {/* Flow Selection */}
      <main className="max-w-4xl mx-auto p-6">
        {/* Operator Flows */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <span>👤</span>
            <span>Operator Flows</span>
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {DEMO_FLOWS.filter(f => f.persona === 'operator').map((flow) => (
              <FlowCard
                key={flow.id}
                flow={flow}
                onClick={() => setActiveFlow(flow.id)}
              />
            ))}
          </div>
        </section>

        {/* Auditor Flows */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <span>🔍</span>
            <span>Auditor Flows</span>
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {DEMO_FLOWS.filter(f => f.persona === 'auditor').map((flow) => (
              <FlowCard
                key={flow.id}
                flow={flow}
                onClick={() => setActiveFlow(flow.id)}
              />
            ))}
          </div>
        </section>

        {/* Public Flows */}
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4 flex items-center gap-2">
            <span>🌐</span>
            <span>Public Access</span>
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {DEMO_FLOWS.filter(f => f.persona === 'public').map((flow) => (
              <FlowCard
                key={flow.id}
                flow={flow}
                onClick={() => setActiveFlow(flow.id)}
              />
            ))}
          </div>
        </section>

        {/* Doctrine Reference */}
        <footer className="mt-12 text-center text-sm text-gray-500">
          <p>Operator Experience Doctrine v1.0.0</p>
          <p className="mt-1">
            All demos map to real API endpoints • No demo-only logic
          </p>
        </footer>
      </main>
    </div>
  );
};

export default DemoExperienceDashboard;
