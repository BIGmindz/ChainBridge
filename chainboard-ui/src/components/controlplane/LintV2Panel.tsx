/**
 * Lint v2 Invariant Panel
 * PAC-JEFFREY-P06R: Lint v2 Runtime Enforcement · Gold Standard
 * 
 * INVARIANT CLASSES (PAC-JEFFREY-P05R):
 * - S-INV: Structural — Schema validation, required fields
 * - M-INV: Semantic — Meaning/intent validation
 * - X-INV: Cross-Artifact — Inter-document consistency
 * - T-INV: Temporal — Ordering, timestamps, sequences
 * - A-INV: Authority — GID/lane authorization
 * - F-INV: Finality — BER/settlement eligibility
 * - C-INV: Training — Signal emission compliance
 * 
 * Schema: CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0
 * 
 * Author: SONNY (GID-02) — Frontend Lane
 */

import React, { useEffect, useState } from 'react';
import { formatTimestamp } from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type InvariantClass = 'S-INV' | 'M-INV' | 'X-INV' | 'T-INV' | 'A-INV' | 'F-INV' | 'C-INV';

export type EnforcementPoint = 
  | 'PAC_ADMISSION' 
  | 'WRAP_INGESTION' 
  | 'RG01_EVALUATION' 
  | 'BER_ELIGIBILITY' 
  | 'SETTLEMENT_READINESS';

export type EvaluationResult = 'PASS' | 'FAIL';

export interface InvariantDTO {
  invariant_id: string;
  invariant_class: InvariantClass;
  name: string;
  description: string;
  enforcement_points: EnforcementPoint[];
  severity: string;
  schema_version: string;
}

export interface ViolationDTO {
  violation_id: string;
  invariant_id: string;
  invariant_class: InvariantClass;
  enforcement_point: EnforcementPoint;
  artifact_id: string;
  artifact_type: string;
  description: string;
  context: Record<string, unknown>;
  detected_at: string;
  violation_hash: string;
}

export interface EvaluationReportDTO {
  report_id: string;
  enforcement_point: EnforcementPoint;
  artifact_id: string;
  artifact_type: string;
  result: EvaluationResult;
  is_pass: boolean;
  violations: ViolationDTO[];
  violation_count: number;
  invariants_evaluated: string[];
  invariants_count: number;
  evaluation_started_at: string;
  evaluation_completed_at: string | null;
  evaluation_duration_ms: number | null;
  report_hash: string;
}

export interface InvariantRegistryDTO {
  schema_version: string;
  total_invariants: number;
  by_class: Record<string, number>;
  by_enforcement_point: Record<string, number>;
  invariants: InvariantDTO[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

export const INVARIANT_CLASS_CONFIG: Record<InvariantClass, {
  label: string;
  description: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  'S-INV': {
    label: 'Structural',
    description: 'Schema validation, required fields',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    icon: '🏗️',
  },
  'M-INV': {
    label: 'Semantic',
    description: 'Meaning/intent validation',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30',
    icon: '🧠',
  },
  'X-INV': {
    label: 'Cross-Artifact',
    description: 'Inter-document consistency',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/30',
    icon: '🔗',
  },
  'T-INV': {
    label: 'Temporal',
    description: 'Ordering, timestamps, sequences',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
    icon: '⏱️',
  },
  'A-INV': {
    label: 'Authority',
    description: 'GID/lane authorization',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/30',
    icon: '🔐',
  },
  'F-INV': {
    label: 'Finality',
    description: 'BER/settlement eligibility',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    icon: '✅',
  },
  'C-INV': {
    label: 'Training',
    description: 'Signal emission compliance',
    color: 'text-pink-400',
    bgColor: 'bg-pink-900/30',
    icon: '📡',
  },
};

export const ENFORCEMENT_POINT_CONFIG: Record<EnforcementPoint, {
  label: string;
  icon: string;
  order: number;
}> = {
  'PAC_ADMISSION': {
    label: 'PAC Admission',
    icon: '📥',
    order: 1,
  },
  'WRAP_INGESTION': {
    label: 'WRAP Ingestion',
    icon: '📦',
    order: 2,
  },
  'RG01_EVALUATION': {
    label: 'RG-01 Evaluation',
    icon: '🔍',
    order: 3,
  },
  'BER_ELIGIBILITY': {
    label: 'BER Eligibility',
    icon: '📄',
    order: 4,
  },
  'SETTLEMENT_READINESS': {
    label: 'Settlement Readiness',
    icon: '💰',
    order: 5,
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface LintV2PanelProps {
  pacId?: string;
  onRefresh?: () => void;
}

/**
 * Main Lint v2 Invariant Panel
 */
export const LintV2Panel: React.FC<LintV2PanelProps> = ({ pacId, onRefresh }) => {
  const [registry, setRegistry] = useState<InvariantRegistryDTO | null>(null);
  const [reports, setReports] = useState<EvaluationReportDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'registry' | 'reports' | 'matrix'>('registry');

  useEffect(() => {
    fetchData();
  }, [pacId]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch registry
      const registryRes = await fetch('/api/oc/lintv2/registry');
      if (registryRes.ok) {
        const registryData = await registryRes.json();
        setRegistry(registryData);
      }
      
      // Fetch reports
      const reportsRes = await fetch('/api/oc/lintv2/reports?limit=10');
      if (reportsRes.ok) {
        const reportsData = await reportsRes.json();
        setReports(reportsData.reports || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch Lint v2 data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">Loading Lint v2 data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-red-700">
        <div className="text-red-400 flex items-center gap-2">
          <span>⚠️</span>
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gray-700/50 border-b border-gray-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚖️</span>
            <div>
              <h3 className="text-lg font-semibold text-white">
                Lint v2 Invariant Engine
              </h3>
              <p className="text-sm text-gray-400">
                PAC-JEFFREY-P06R · Runtime Enforcement · FAIL_CLOSED
              </p>
            </div>
          </div>
          
          {/* Stats */}
          <div className="flex gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">
                {registry?.total_invariants || 0}
              </div>
              <div className="text-xs text-gray-400">Invariants</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {Object.keys(registry?.by_class || {}).length}
              </div>
              <div className="text-xs text-gray-400">Classes</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400">
                {reports.length}
              </div>
              <div className="text-xs text-gray-400">Reports</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {(['registry', 'reports', 'matrix'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-700/30'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab === 'registry' && '📋 Registry'}
            {tab === 'reports' && '📊 Reports'}
            {tab === 'matrix' && '🔢 Matrix'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === 'registry' && registry && (
          <InvariantRegistryView registry={registry} />
        )}
        {activeTab === 'reports' && (
          <EvaluationReportsView reports={reports} />
        )}
        {activeTab === 'matrix' && registry && (
          <EnforcementMatrixView registry={registry} />
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-4 bg-gray-700/30 border-t border-gray-600">
        <div className="flex justify-between items-center">
          <div className="text-xs text-gray-500">
            Schema: {registry?.schema_version || 'N/A'}
          </div>
          <button
            onClick={() => {
              fetchData();
              onRefresh?.();
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg 
                       transition-colors flex items-center gap-2 text-sm"
          >
            <span>🔄</span>
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * Invariant Registry View
 */
const InvariantRegistryView: React.FC<{ registry: InvariantRegistryDTO }> = ({ registry }) => {
  const [selectedClass, setSelectedClass] = useState<InvariantClass | 'ALL'>('ALL');
  
  const filteredInvariants = selectedClass === 'ALL'
    ? registry.invariants
    : registry.invariants.filter(inv => inv.invariant_class === selectedClass);

  return (
    <div className="space-y-6">
      {/* Class Summary */}
      <div className="grid grid-cols-7 gap-2">
        {(Object.keys(INVARIANT_CLASS_CONFIG) as InvariantClass[]).map((cls) => {
          const config = INVARIANT_CLASS_CONFIG[cls];
          const count = registry.by_class[cls] || 0;
          return (
            <button
              key={cls}
              onClick={() => setSelectedClass(selectedClass === cls ? 'ALL' : cls)}
              className={`p-3 rounded-lg border transition-all ${
                selectedClass === cls
                  ? `${config.bgColor} border-current ${config.color}`
                  : 'bg-gray-700/30 border-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="text-xl mb-1">{config.icon}</div>
              <div className={`text-xs font-medium ${selectedClass === cls ? config.color : 'text-gray-300'}`}>
                {cls}
              </div>
              <div className="text-lg font-bold text-white">{count}</div>
            </button>
          );
        })}
      </div>

      {/* Invariant List */}
      <div className="space-y-2">
        {filteredInvariants.map((inv) => (
          <InvariantCard key={inv.invariant_id} invariant={inv} />
        ))}
      </div>
    </div>
  );
};

/**
 * Individual Invariant Card
 */
const InvariantCard: React.FC<{ invariant: InvariantDTO }> = ({ invariant }) => {
  const config = INVARIANT_CLASS_CONFIG[invariant.invariant_class];
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`rounded-lg border ${config.bgColor} border-gray-600`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{config.icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className={`font-mono font-bold ${config.color}`}>
                {invariant.invariant_id}
              </span>
              <span className="text-white font-medium">
                {invariant.name}
              </span>
            </div>
            <div className="text-sm text-gray-400">
              {invariant.description}
            </div>
          </div>
        </div>
        <span className="text-gray-400">{expanded ? '▼' : '▶'}</span>
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-gray-600/50">
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex gap-2">
              <span className="text-gray-400">Enforcement Points:</span>
              <div className="flex flex-wrap gap-1">
                {invariant.enforcement_points.map((ep) => (
                  <span
                    key={ep}
                    className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300"
                  >
                    {ENFORCEMENT_POINT_CONFIG[ep]?.icon} {ENFORCEMENT_POINT_CONFIG[ep]?.label}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <span className="text-gray-400">Severity:</span>
              <span className="text-red-400 font-medium">{invariant.severity}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Evaluation Reports View
 */
const EvaluationReportsView: React.FC<{ reports: EvaluationReportDTO[] }> = ({ reports }) => {
  if (reports.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <div className="text-4xl mb-2">📊</div>
        <div>No evaluation reports yet</div>
        <div className="text-sm">Reports will appear after lint evaluations</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {reports.map((report) => (
        <EvaluationReportCard key={report.report_id} report={report} />
      ))}
    </div>
  );
};

/**
 * Individual Report Card
 */
const EvaluationReportCard: React.FC<{ report: EvaluationReportDTO }> = ({ report }) => {
  const [expanded, setExpanded] = useState(false);
  const isPassing = report.is_pass;

  return (
    <div className={`rounded-lg border ${
      isPassing ? 'bg-green-900/20 border-green-700' : 'bg-red-900/20 border-red-700'
    }`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{isPassing ? '✅' : '❌'}</span>
            <div>
              <div className="flex items-center gap-2">
                <span className={`font-bold ${isPassing ? 'text-green-400' : 'text-red-400'}`}>
                  {report.result}
                </span>
                <span className="text-gray-400">•</span>
                <span className="text-white">{report.artifact_id}</span>
              </div>
              <div className="text-sm text-gray-400">
                {ENFORCEMENT_POINT_CONFIG[report.enforcement_point]?.icon}{' '}
                {ENFORCEMENT_POINT_CONFIG[report.enforcement_point]?.label}
                {' • '}{report.invariants_count} invariants evaluated
                {report.violation_count > 0 && ` • ${report.violation_count} violations`}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">
              {formatTimestamp(report.evaluation_started_at)}
            </div>
            {report.evaluation_duration_ms && (
              <div className="text-xs text-gray-500">
                {report.evaluation_duration_ms}ms
              </div>
            )}
          </div>
        </div>
      </button>
      
      {expanded && report.violations.length > 0 && (
        <div className="px-4 pb-4 border-t border-gray-600/50">
          <div className="mt-3 space-y-2">
            {report.violations.map((v) => (
              <div key={v.violation_id} className="bg-red-900/30 rounded p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-red-400 text-sm">{v.invariant_id}</span>
                  <span className="text-white">{v.description}</span>
                </div>
                <div className="text-xs text-gray-400">
                  Hash: {v.violation_hash}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Enforcement Matrix View
 */
const EnforcementMatrixView: React.FC<{ registry: InvariantRegistryDTO }> = ({ registry }) => {
  const classes = Object.keys(INVARIANT_CLASS_CONFIG) as InvariantClass[];
  const points = (Object.keys(ENFORCEMENT_POINT_CONFIG) as EnforcementPoint[])
    .sort((a, b) => ENFORCEMENT_POINT_CONFIG[a].order - ENFORCEMENT_POINT_CONFIG[b].order);

  // Build matrix
  const matrix: Record<EnforcementPoint, Record<InvariantClass, string[]>> = {} as any;
  points.forEach(ep => {
    matrix[ep] = {} as any;
    classes.forEach(cls => {
      matrix[ep][cls] = [];
    });
  });

  registry.invariants.forEach(inv => {
    inv.enforcement_points.forEach(ep => {
      if (matrix[ep] && matrix[ep][inv.invariant_class]) {
        matrix[ep][inv.invariant_class].push(inv.invariant_id);
      }
    });
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="text-left p-2 text-gray-400">Enforcement Point</th>
            {classes.map(cls => (
              <th key={cls} className="p-2">
                <div className={`${INVARIANT_CLASS_CONFIG[cls].color}`}>
                  {INVARIANT_CLASS_CONFIG[cls].icon}
                </div>
                <div className="text-xs text-gray-400">{cls}</div>
              </th>
            ))}
            <th className="p-2 text-gray-400">Total</th>
          </tr>
        </thead>
        <tbody>
          {points.map(ep => {
            const total = classes.reduce((sum, cls) => sum + matrix[ep][cls].length, 0);
            return (
              <tr key={ep} className="border-t border-gray-700">
                <td className="p-2">
                  <span className="mr-2">{ENFORCEMENT_POINT_CONFIG[ep].icon}</span>
                  <span className="text-gray-300">{ENFORCEMENT_POINT_CONFIG[ep].label}</span>
                </td>
                {classes.map(cls => (
                  <td key={cls} className="p-2 text-center">
                    {matrix[ep][cls].length > 0 ? (
                      <span className={`font-bold ${INVARIANT_CLASS_CONFIG[cls].color}`}>
                        {matrix[ep][cls].length}
                      </span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                ))}
                <td className="p-2 text-center font-bold text-white">{total}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default LintV2Panel;
