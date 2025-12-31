/**
 * Enterprise Compliance Summary — PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 *
 * Displays enterprise compliance framework mappings (SOX, SOC2, NIST, ISO 27001).
 * Shows how governance artifacts map to enterprise audit requirements.
 *
 * @see PAC-SONNY-P01-GOVERNANCE-HEALTH-DASHBOARD-01
 * @see GOVERNANCE_DOCTRINE_V1.1 Appendix A
 */

import { Shield, CheckCircle2, Info } from 'lucide-react';
import type { EnterpriseComplianceSummary, EnterpriseMapping } from '../../types/governanceHealth';

interface EnterpriseComplianceSummaryProps {
  summary: EnterpriseComplianceSummary;
  className?: string;
}

interface FrameworkCardProps {
  name: string;
  coverage: number;
  mappings: EnterpriseMapping[];
}

const FRAMEWORK_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  SOX: { label: 'SOX', color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  SOC2: { label: 'SOC 2', color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  NIST_CSF: { label: 'NIST CSF', color: 'text-emerald-400', bgColor: 'bg-emerald-500/10' },
  ISO_27001: { label: 'ISO 27001', color: 'text-amber-400', bgColor: 'bg-amber-500/10' },
};

const ARTIFACT_COLORS: Record<string, string> = {
  PAC: 'text-teal-400',
  BER: 'text-yellow-400',
  PDO: 'text-orange-400',
  WRAP: 'text-cyan-400',
  LEDGER: 'text-slate-400',
};

function FrameworkCard({ name, coverage, mappings }: FrameworkCardProps): JSX.Element {
  const config = FRAMEWORK_CONFIG[name] || { label: name, color: 'text-slate-400', bgColor: 'bg-slate-500/10' };

  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
        <span className="text-xs text-emerald-400 flex items-center gap-1">
          <CheckCircle2 className="h-3 w-3" />
          {coverage}%
        </span>
      </div>

      <div className="space-y-1">
        {mappings.map((mapping, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs">
            <span className="text-slate-500 font-mono">{mapping.control}</span>
            <span className={`font-mono ${ARTIFACT_COLORS[mapping.artifact]}`}>{mapping.artifact}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function EnterpriseComplianceSummaryPanel({
  summary,
  className = '',
}: EnterpriseComplianceSummaryProps): JSX.Element {
  // Group mappings by framework
  const groupedMappings = summary.mappings.reduce(
    (acc, mapping) => {
      const key = mapping.framework;
      if (!acc[key]) acc[key] = [];
      acc[key].push(mapping);
      return acc;
    },
    {} as Record<string, EnterpriseMapping[]>
  );

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-teal-400" />
          <h3 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
            Enterprise Compliance
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Overall Score:</span>
          <span className="text-sm font-bold text-emerald-400">{summary.complianceScore}%</span>
        </div>
      </div>

      {/* Framework Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <FrameworkCard
          name="SOX"
          coverage={summary.frameworkCoverage.sox}
          mappings={groupedMappings['SOX'] || []}
        />
        <FrameworkCard
          name="SOC2"
          coverage={summary.frameworkCoverage.soc2}
          mappings={groupedMappings['SOC2'] || []}
        />
        <FrameworkCard
          name="NIST_CSF"
          coverage={summary.frameworkCoverage.nist}
          mappings={groupedMappings['NIST_CSF'] || []}
        />
        <FrameworkCard
          name="ISO_27001"
          coverage={summary.frameworkCoverage.iso27001}
          mappings={groupedMappings['ISO_27001'] || []}
        />
      </div>

      {/* Artifact → Framework Mapping Table */}
      <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 overflow-hidden">
        <div className="px-3 py-2 bg-slate-800/50 border-b border-slate-700/50">
          <p className="text-xs text-slate-400 font-mono">Artifact → Framework Mapping (Doctrine V1.1)</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-3 py-2 text-slate-500 font-mono">Artifact</th>
                <th className="text-center px-3 py-2 text-blue-400 font-mono">SOX</th>
                <th className="text-center px-3 py-2 text-purple-400 font-mono">SOC 2</th>
                <th className="text-center px-3 py-2 text-emerald-400 font-mono">NIST</th>
                <th className="text-center px-3 py-2 text-amber-400 font-mono">ISO</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-800/50">
                <td className="px-3 py-2 text-teal-400 font-mono">PAC</td>
                <td className="text-center px-3 py-2 text-slate-400">§302</td>
                <td className="text-center px-3 py-2 text-slate-400">CC6.1</td>
                <td className="text-center px-3 py-2 text-slate-400">PR.IP-1</td>
                <td className="text-center px-3 py-2 text-slate-400">A.12.1</td>
              </tr>
              <tr className="border-b border-slate-800/50">
                <td className="px-3 py-2 text-yellow-400 font-mono">BER</td>
                <td className="text-center px-3 py-2 text-slate-400">§404</td>
                <td className="text-center px-3 py-2 text-slate-400">CC6.7</td>
                <td className="text-center px-3 py-2 text-slate-400">DE.CM-1</td>
                <td className="text-center px-3 py-2 text-slate-400">A.9.4</td>
              </tr>
              <tr className="border-b border-slate-800/50">
                <td className="px-3 py-2 text-orange-400 font-mono">PDO</td>
                <td className="text-center px-3 py-2 text-slate-400">—</td>
                <td className="text-center px-3 py-2 text-slate-400">CC7.2</td>
                <td className="text-center px-3 py-2 text-slate-400">RS.AN-1</td>
                <td className="text-center px-3 py-2 text-slate-400">A.12.4</td>
              </tr>
              <tr className="border-b border-slate-800/50">
                <td className="px-3 py-2 text-cyan-400 font-mono">WRAP</td>
                <td className="text-center px-3 py-2 text-slate-400">—</td>
                <td className="text-center px-3 py-2 text-slate-400">CC5.1</td>
                <td className="text-center px-3 py-2 text-slate-400">PR.IP-4</td>
                <td className="text-center px-3 py-2 text-slate-400">A.14.2</td>
              </tr>
              <tr>
                <td className="px-3 py-2 text-slate-400 font-mono">Ledger</td>
                <td className="text-center px-3 py-2 text-slate-400">§802</td>
                <td className="text-center px-3 py-2 text-slate-400">CC8.1</td>
                <td className="text-center px-3 py-2 text-slate-400">PR.DS-1</td>
                <td className="text-center px-3 py-2 text-slate-400">A.12.4.3</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Last Audit */}
      {summary.lastAuditDate && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Info className="h-3 w-3" />
          <span>Last audit: {summary.lastAuditDate}</span>
        </div>
      )}
    </div>
  );
}
