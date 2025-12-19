/**
 * Governance Page
 *
 * Central page for governance oversight in ChainBoard.
 * Houses the Governance Decisions Panel and future governance tools.
 */

import { GovernanceDecisionsPanel } from '../components/governance/GovernanceDecisionsPanel';

export default function GovernancePage(): JSX.Element {
  return (
    <div className="space-y-6 px-6 py-8">
      <header className="space-y-2">
        <p className="text-xs text-slate-600 uppercase tracking-wider font-mono">
          governance_center
        </p>
        <p className="text-sm text-slate-500 font-mono">
          Decision records and policy artifacts
        </p>
      </header>

      <GovernanceDecisionsPanel />
    </div>
  );
}
