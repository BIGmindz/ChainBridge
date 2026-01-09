/**
 * Review Gate RG-01 Panel — Control Plane UI
 * PAC-JEFFREY-P01: SECTION 8 — Review Gate Visualization
 *
 * Displays RG-01 Review Gate status per PAC-JEFFREY-P01:
 * - Reviewer identity (BENSON)
 * - Pass conditions status
 * - Fail reasons if applicable
 * - Fail action indicator
 *
 * INVARIANTS:
 * - Reviewer: BENSON
 * - Pass conditions: WRAP schema valid, all mandatory blocks, no forbidden actions
 * - Fail action: emit corrective PAC
 *
 * Author: Benson Execution Orchestrator (GID-00)
 * Frontend Lane: SONNY (GID-02)
 */

import React from 'react';
import { ReviewGateRG01DTO, RG01PassCondition } from '../../types/controlPlane';

// ═══════════════════════════════════════════════════════════════════════════════
// CONDITION LABELS
// ═══════════════════════════════════════════════════════════════════════════════

const CONDITION_LABELS: Record<string, { label: string; description: string }> = {
  wrap_schema_valid: {
    label: 'WRAP Schema Valid',
    description: 'All WRAPs conform to CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.0.0',
  },
  all_mandatory_blocks: {
    label: 'All Mandatory Blocks Present',
    description: 'Required blocks: Identity, PAG-01 ACK, Task Receipt, Determinism, Output, Violations, Training, Closure',
  },
  no_forbidden_actions: {
    label: 'No Forbidden Actions',
    description: 'No agent executed forbidden actions per PAG-01 constraints',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// PASS CONDITION ROW
// ═══════════════════════════════════════════════════════════════════════════════

interface PassConditionRowProps {
  condition: RG01PassCondition;
}

const PassConditionRow: React.FC<PassConditionRowProps> = ({ condition }) => {
  const config = CONDITION_LABELS[condition.condition] || {
    label: condition.condition,
    description: '',
  };

  const getStatusDisplay = () => {
    if (condition.status === null) {
      return {
        icon: '⏳',
        color: 'text-gray-400',
        bg: 'bg-gray-800',
        label: 'Pending',
      };
    }
    if (condition.status) {
      return {
        icon: '✅',
        color: 'text-green-400',
        bg: 'bg-green-900/30',
        label: 'Pass',
      };
    }
    return {
      icon: '❌',
      color: 'text-red-400',
      bg: 'bg-red-900/30',
      label: 'Fail',
    };
  };

  const status = getStatusDisplay();

  return (
    <div className={`${status.bg} rounded-lg p-4 border border-gray-700`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={status.color}>{status.icon}</span>
          <span className="text-sm font-medium text-gray-200">{config.label}</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded ${status.bg} ${status.color}`}>
          {status.label}
        </span>
      </div>
      <p className="text-xs text-gray-500">{config.description}</p>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// RESULT BANNER
// ═══════════════════════════════════════════════════════════════════════════════

interface ResultBannerProps {
  result: 'PASS' | 'FAIL' | null;
  evaluatedAt: string | null;
}

const ResultBanner: React.FC<ResultBannerProps> = ({ result, evaluatedAt }) => {
  if (result === null) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-gray-700 flex items-center justify-center">
          <span className="text-2xl">⏳</span>
        </div>
        <div>
          <div className="text-lg font-semibold text-gray-300">Pending Evaluation</div>
          <div className="text-xs text-gray-500">
            RG-01 review gate has not been evaluated yet
          </div>
        </div>
      </div>
    );
  }

  if (result === 'PASS') {
    return (
      <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-green-900/50 flex items-center justify-center">
          <span className="text-2xl">✅</span>
        </div>
        <div>
          <div className="text-lg font-semibold text-green-400">PASS</div>
          <div className="text-xs text-green-500/70">
            {evaluatedAt ? `Evaluated at ${new Date(evaluatedAt).toLocaleString()}` : 'All conditions met'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
      <div className="w-12 h-12 rounded-full bg-red-900/50 flex items-center justify-center">
        <span className="text-2xl">❌</span>
      </div>
      <div>
        <div className="text-lg font-semibold text-red-400">FAIL</div>
        <div className="text-xs text-red-500/70">
          {evaluatedAt ? `Evaluated at ${new Date(evaluatedAt).toLocaleString()}` : 'Conditions not met'}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface ReviewGateRG01PanelProps {
  data: ReviewGateRG01DTO;
  className?: string;
}

export const ReviewGateRG01Panel: React.FC<ReviewGateRG01PanelProps> = ({
  data,
  className = '',
}) => {
  return (
    <div className={`bg-gray-900 rounded-lg p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span>🔍</span>
            <span>RG-01 Review Gate</span>
          </h2>
          <p className="text-xs text-gray-500 mt-1">
            PAC-JEFFREY-P01 Section 8 · Gate ID: {data.gate_id}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">Reviewer</div>
          <div className="text-sm font-medium text-blue-400">{data.reviewer}</div>
        </div>
      </div>

      {/* Result Banner */}
      <ResultBanner result={data.result} evaluatedAt={data.evaluated_at} />

      {/* Pass Conditions */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-400">Pass Conditions</h3>
        <div className="space-y-3">
          {data.pass_conditions.map((condition, idx) => (
            <PassConditionRow key={idx} condition={condition} />
          ))}
        </div>
      </div>

      {/* Fail Reasons */}
      {data.fail_reasons.length > 0 && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2 text-red-400 text-sm font-medium">
            <span>❌</span>
            <span>Fail Reasons ({data.fail_reasons.length})</span>
          </div>
          <ul className="space-y-2">
            {data.fail_reasons.map((reason, idx) => (
              <li key={idx} className="text-xs text-red-300 flex items-start gap-2">
                <span className="text-red-500 mt-0.5">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Fail Action */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          <span className="font-medium">Fail Action: </span>
          <span className="text-orange-400">{data.fail_action}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>
            WRAP Set Complete:{' '}
            <span className={data.wrap_set_complete ? 'text-green-400' : 'text-yellow-400'}>
              {data.wrap_set_complete ? '✅' : '⏳'}
            </span>
          </span>
          <span>
            All Valid:{' '}
            <span className={data.wrap_set_valid ? 'text-green-400' : 'text-red-400'}>
              {data.wrap_set_valid ? '✅' : '❌'}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default ReviewGateRG01Panel;
