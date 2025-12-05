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
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-500">
          ChainBridge Intelligence
        </p>
        <h1 className="text-4xl font-semibold text-slate-900">Governance Center</h1>
        <p className="max-w-3xl text-base text-slate-600">
          AI governance decisions, policy enforcement, and Guardian oversight for the ChainBridge network.
        </p>
      </header>

      <GovernanceDecisionsPanel />
    </div>
  );
}
