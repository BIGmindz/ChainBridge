/**
 * TerminalUIParityDemo — PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 *
 * Side-by-side demonstration of terminal output vs UI rendering.
 * Proves 1:1 parity between terminal and UI governance signals.
 *
 * @see PAC-SONNY-P30-TERMINAL-UI-PARITY-AND-VISUAL-GOVERNANCE-01
 */

import { useState, useMemo } from 'react';

import {
  GovernanceSignalBadge,
  SeverityBadge,
  GovernanceSignalRow,
  ValidationSummary,
  GateIndicator,
} from './GovernanceSignalBadge';
import {
  type SignalStatus,
  type SignalSeverity,
  TERMINAL_BANNERS,
  TERMINAL_GLYPHS,
} from './GovernanceVisualLanguage';

// ============================================================================
// DEMO DATA
// ============================================================================

interface DemoSignal {
  status: SignalStatus;
  severity: SignalSeverity;
  code: string;
  title: string;
  description?: string;
  evidence?: string;
  resolution?: string;
}

const DEMO_SIGNALS: DemoSignal[] = [
  {
    status: 'PASS',
    severity: 'NONE',
    code: 'PAG_001',
    title: 'Agent Activation Block Present',
    description: 'The AGENT_ACTIVATION_ACK block is present and properly formatted.',
    evidence: '• Found: AGENT_ACTIVATION_ACK at line 12\n• Agent: SONNY (GID-02)\n• Color: YELLOW ✓',
  },
  {
    status: 'PASS',
    severity: 'NONE',
    code: 'PAG_003',
    title: 'Registry Binding Verified',
    description: 'Agent identity matches AGENT_REGISTRY.md entry.',
    evidence: '• Registry lookup: GID-02\n• Name match: SONNY ✓\n• Color match: YELLOW ✓',
  },
  {
    status: 'WARN',
    severity: 'MEDIUM',
    code: 'GS_010',
    title: 'Schema Version Advisory',
    description: 'Document uses schema v0.9.0 which is deprecated. Consider upgrading to v1.0.0.',
    evidence: '• Found: SCHEMA_REFERENCE v0.9.0\n• Latest: v1.0.0',
    resolution: 'Update SCHEMA_REFERENCE to CHAINBRIDGE_PAC_SCHEMA v1.0.0',
  },
  {
    status: 'FAIL',
    severity: 'HIGH',
    code: 'RG_001',
    title: 'Review Gate Not Declared',
    description: 'The REVIEW_GATE block is missing. All PACs require a review gate declaration.',
    evidence: '• Searched for: REVIEW_GATE\n• Found: Not present\n• Expected: Document body',
    resolution: 'Add REVIEW_GATE block with gate_id: REVIEW-GATE-v1.1 and mode: FAIL_CLOSED',
  },
  {
    status: 'SKIP',
    severity: 'NONE',
    code: 'BSRG_001',
    title: 'Benson Self-Review Gate',
    description: 'BSRG check skipped — document is not BENSON-issued.',
    evidence: '• Issuing agent: SONNY (GID-02)\n• BSRG required for: GID-00 only',
  },
];

// ============================================================================
// TERMINAL OUTPUT RENDERER
// ============================================================================

function renderTerminalOutput(signals: DemoSignal[]): string {
  const counts = signals.reduce(
    (acc, s) => {
      acc[s.status.toLowerCase() as 'pass' | 'warn' | 'fail' | 'skip']++;
      return acc;
    },
    { pass: 0, warn: 0, fail: 0, skip: 0 }
  );

  const status = counts.fail > 0 ? 'INVALID' : 'VALID';
  const banner = status === 'VALID' ? TERMINAL_BANNERS.PASS : TERMINAL_BANNERS.FAIL;

  let output = `══════════════════════════════════════════════════════════════════════════════
${banner}
GOVERNANCE VALIDATION RESULT
${banner}
══════════════════════════════════════════════════════════════════════════════

File: docs/governance/pacs/PAC-EXAMPLE-01.md

`;

  for (const signal of signals) {
    const glyph = TERMINAL_GLYPHS[signal.status];
    output += `┌─────────────────────────────────────────────────────────────────────────────┐
│ ${glyph} ${signal.status.padEnd(4)} | ${signal.severity.padEnd(8)} | ${signal.code.padEnd(10)}                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ ${signal.title.padEnd(75)} │`;

    if (signal.description) {
      output += `
│                                                                             │
│ ${signal.description.slice(0, 73).padEnd(75)} │`;
    }

    if (signal.evidence) {
      output += `
│                                                                             │
│ Evidence:                                                                   │`;
      for (const line of signal.evidence.split('\n')) {
        output += `
│   ${line.padEnd(73)} │`;
      }
    }

    if (signal.resolution) {
      output += `
│                                                                             │
│ Resolution:                                                                 │
│   ${signal.resolution.slice(0, 71).padEnd(73)} │`;
    }

    output += `
└─────────────────────────────────────────────────────────────────────────────┘

`;
  }

  output += `══════════════════════════════════════════════════════════════════════════════
  SUMMARY: ${counts.fail} FAIL | ${counts.warn} WARN | ${counts.pass} PASS | ${counts.skip} SKIP
  STATUS: ${counts.fail > 0 ? TERMINAL_GLYPHS.FAIL : TERMINAL_GLYPHS.PASS} ${status}
══════════════════════════════════════════════════════════════════════════════`;

  return output;
}

// ============================================================================
// PARITY DEMO COMPONENT
// ============================================================================

export interface TerminalUIParityDemoProps {
  /** Additional CSS classes */
  className?: string;
}

/**
 * TerminalUIParityDemo — Side-by-side terminal vs UI comparison.
 */
export function TerminalUIParityDemo({ className = '' }: TerminalUIParityDemoProps) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const terminalOutput = useMemo(() => renderTerminalOutput(DEMO_SIGNALS), []);

  const counts = useMemo(
    () =>
      DEMO_SIGNALS.reduce(
        (acc, s) => {
          acc[s.status.toLowerCase() as 'pass' | 'warn' | 'fail' | 'skip']++;
          return acc;
        },
        { pass: 0, warn: 0, fail: 0, skip: 0 }
      ),
    []
  );

  const overallStatus = counts.fail > 0 ? 'INVALID' : 'VALID';

  return (
    <div className={`space-y-6 ${className}`} data-testid="terminal-ui-parity-demo">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Terminal ↔ UI Parity Demonstration
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Governance signals render identically in terminal and UI
        </p>
      </div>

      {/* Side-by-side comparison */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Terminal Output */}
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <span>📟</span> Terminal Output
          </h3>
          <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
            <pre className="text-xs font-mono whitespace-pre">{terminalOutput}</pre>
          </div>
        </div>

        {/* UI Output */}
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <span>🖥️</span> UI Output
          </h3>
          <div className="space-y-3">
            {/* Banner */}
            <div
              className={`
                text-center py-3 rounded-lg font-mono text-2xl tracking-widest
                ${overallStatus === 'VALID' ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-rose-100 dark:bg-rose-900/30'}
              `}
            >
              {overallStatus === 'VALID' ? TERMINAL_BANNERS.PASS : TERMINAL_BANNERS.FAIL}
            </div>

            {/* Signals */}
            <div className="space-y-2">
              {DEMO_SIGNALS.map((signal, idx) => (
                <GovernanceSignalRow
                  key={`${signal.code}-${idx}`}
                  status={signal.status}
                  severity={signal.severity}
                  code={signal.code}
                  title={signal.title}
                  description={signal.description}
                  evidence={signal.evidence}
                  resolution={signal.resolution}
                  expanded={expandedRow === idx}
                  onClick={() => setExpandedRow(expandedRow === idx ? null : idx)}
                />
              ))}
            </div>

            {/* Summary */}
            <ValidationSummary
              passCount={counts.pass}
              warnCount={counts.warn}
              failCount={counts.fail}
              skipCount={counts.skip}
              status={overallStatus === 'VALID' ? 'VALID' : 'INVALID'}
            />
          </div>
        </div>
      </div>

      {/* Visual Language Reference */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-4">
          Governance Visual Language Reference
        </h3>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Status Badges */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-gray-500 uppercase">
              Signal Status
            </span>
            <div className="flex flex-wrap gap-2">
              <GovernanceSignalBadge status="PASS" />
              <GovernanceSignalBadge status="WARN" />
              <GovernanceSignalBadge status="FAIL" />
              <GovernanceSignalBadge status="SKIP" />
            </div>
          </div>

          {/* Severity Badges */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-gray-500 uppercase">
              Severity Levels
            </span>
            <div className="flex flex-wrap gap-2">
              <SeverityBadge severity="CRITICAL" />
              <SeverityBadge severity="HIGH" />
              <SeverityBadge severity="MEDIUM" />
              <SeverityBadge severity="LOW" />
            </div>
          </div>

          {/* Gate States */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-gray-500 uppercase">
              Gate States
            </span>
            <div className="space-y-1">
              <GateIndicator gateName="Review Gate" gateId="RG-v1.1" state="PASS" size="sm" />
              <GateIndicator gateName="BSRG" gateId="BSRG-01" state="PENDING" size="sm" />
            </div>
          </div>

          {/* Terminal Glyphs */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-gray-500 uppercase">
              Terminal Glyphs
            </span>
            <div className="font-mono text-sm space-y-1 bg-gray-100 dark:bg-gray-800 rounded p-2">
              <div>✓ PASS &nbsp; ⚠ WARN</div>
              <div>✗ FAIL &nbsp; ○ SKIP</div>
              <div>🔓 OPEN &nbsp; 🔒 CLOSED</div>
            </div>
          </div>
        </div>
      </div>

      {/* Design Note */}
      <div className="bg-slate-100 dark:bg-slate-800/50 rounded-lg p-4 text-sm">
        <div className="font-semibold text-slate-700 dark:text-slate-300 mb-1">
          🎨 Design Note: Governance vs Agent Visual Separation
        </div>
        <p className="text-slate-600 dark:text-slate-400">
          Governance signals use <strong>emerald</strong> (not green), <strong>orange</strong>{' '}
          (not yellow), and <strong>rose</strong> (not red) to ensure they are never
          confused with agent identity colors. Agent colors (🟡 YELLOW for SONNY, 🔴 RED
          for BENSON, etc.) are reserved exclusively for agent identity markers.
        </p>
      </div>
    </div>
  );
}

export default TerminalUIParityDemo;
