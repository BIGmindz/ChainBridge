/**
 * Governance Page — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Central page for governance oversight in ChainBoard.
 * Houses the Governance Health Dashboard and Decisions Panel.
 *
 * READ-ONLY — All governance data is displayed for visibility only.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 */

import { useState } from 'react';
import { Activity, FileText } from 'lucide-react';
import { GovernanceDecisionsPanel } from '../components/governance/GovernanceDecisionsPanel';
import { GovernanceHealthDashboard } from '../components/governance/GovernanceHealthDashboard';

type TabId = 'health' | 'decisions';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  { id: 'health', label: 'Settlement Health', icon: <Activity className="h-4 w-4" /> },
  { id: 'decisions', label: 'Decisions', icon: <FileText className="h-4 w-4" /> },
];

export default function GovernancePage(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>('health');

  return (
    <div className="space-y-6 px-6 py-8">
      <header className="space-y-2">
        <p className="text-xs text-slate-600 uppercase tracking-wider font-mono">
          governance_center
        </p>
        <p className="text-sm text-slate-500 font-mono">
          Decision Settlement System • Enterprise Compliance • Artifact Visibility
        </p>
      </header>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 border-b border-slate-700/50">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-teal-400 border-teal-400'
                : 'text-slate-500 border-transparent hover:text-slate-300'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'health' && <GovernanceHealthDashboard />}
      {activeTab === 'decisions' && <GovernanceDecisionsPanel />}
    </div>
  );
}
