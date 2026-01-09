/**
 * RegulatorySummaryView — Regulatory metrics dashboard for auditors
 * ════════════════════════════════════════════════════════════════════════════════
 *
 * PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
 * Agent: Sonny (GID-02) — Audit UI
 * Order: ORDER 3
 * Effective Date: 2025-12-30
 *
 * ════════════════════════════════════════════════════════════════════════════════
 */

import React from "react";
import { RegulatorySummary, RegulatoryMetrics } from "../../types/audit";

// ═══════════════════════════════════════════════════════════════════════════════
// METRIC CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface MetricCardProps {
  label: string;
  value: number | string;
  subtext?: string;
  color?: "blue" | "green" | "yellow" | "red" | "gray";
}

function MetricCard({
  label,
  value,
  subtext,
  color = "blue",
}: MetricCardProps): JSX.Element {
  const colorClasses = {
    blue: "bg-blue-50 border-blue-200",
    green: "bg-green-50 border-green-200",
    yellow: "bg-yellow-50 border-yellow-200",
    red: "bg-red-50 border-red-200",
    gray: "bg-gray-50 border-gray-200",
  };

  const textClasses = {
    blue: "text-blue-700",
    green: "text-green-700",
    yellow: "text-yellow-700",
    red: "text-red-700",
    gray: "text-gray-700",
  };

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <div className="text-sm text-gray-600 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${textClasses[color]}`}>{value}</div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// RATE INDICATOR COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface RateIndicatorProps {
  label: string;
  rate: number; // 0-1
  threshold?: number;
}

function RateIndicator({
  label,
  rate,
  threshold = 0.95,
}: RateIndicatorProps): JSX.Element {
  const percentage = (rate * 100).toFixed(1);
  const isHealthy = rate >= threshold;

  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <div className="flex items-center gap-2">
        <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              isHealthy ? "bg-green-500" : "bg-yellow-500"
            }`}
            style={{ width: `${Math.min(rate * 100, 100)}%` }}
          />
        </div>
        <span
          className={`text-sm font-bold ${
            isHealthy ? "text-green-600" : "text-yellow-600"
          }`}
        >
          {percentage}%
        </span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface RegulatorySummaryViewProps {
  summary: RegulatorySummary;
  onRefresh?: () => void;
}

export default function RegulatorySummaryView({
  summary,
  onRefresh,
}: RegulatorySummaryViewProps): JSX.Element {
  const { metrics } = summary;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Regulatory Summary
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Summary ID: {summary.summary_id}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Governance Mode Badge */}
          <span className="px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full">
            {summary.governance_mode}
          </span>

          {onRefresh && (
            <button
              onClick={onRefresh}
              className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
            >
              ↻ Refresh
            </button>
          )}
        </div>
      </div>

      {/* Period */}
      <div className="mb-6 p-3 bg-gray-50 rounded-lg">
        <div className="text-sm text-gray-600">
          <span className="font-medium">Reporting Period:</span>{" "}
          {new Date(metrics.period_start).toLocaleDateString()} —{" "}
          {new Date(metrics.period_end).toLocaleDateString()}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Generated: {new Date(summary.generated_at).toLocaleString()}
        </div>
      </div>

      {/* Volume Metrics */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Volume Metrics</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Total PDOs" value={metrics.total_pdos} color="blue" />
          <MetricCard
            label="Decisions"
            value={metrics.total_decisions}
            color="blue"
          />
          <MetricCard label="Outcomes" value={metrics.total_outcomes} color="green" />
          <MetricCard
            label="Settlements"
            value={metrics.total_settlements}
            color="green"
          />
        </div>
      </div>

      {/* Verification Metrics */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Verification Status
        </h4>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <MetricCard
            label="Verified Chains"
            value={metrics.verified_chains}
            color="green"
          />
          <MetricCard
            label="Unverified"
            value={metrics.unverified_chains}
            color="yellow"
          />
          <MetricCard
            label="Failed"
            value={metrics.failed_verifications}
            color={metrics.failed_verifications > 0 ? "red" : "gray"}
          />
        </div>

        {/* Rate Indicators */}
        <div className="space-y-2">
          <RateIndicator
            label="Verification Rate"
            rate={metrics.verification_rate}
            threshold={0.95}
          />
          <RateIndicator
            label="Chain Completeness"
            rate={metrics.chain_completeness_rate}
            threshold={0.9}
          />
        </div>
      </div>

      {/* Governance Metrics */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Governance Activity
        </h4>
        <div className="grid grid-cols-3 gap-4">
          <MetricCard
            label="Violations"
            value={metrics.governance_violations}
            color={metrics.governance_violations > 0 ? "red" : "green"}
            subtext={metrics.governance_violations === 0 ? "No violations" : "Review required"}
          />
          <MetricCard
            label="Human Interventions"
            value={metrics.human_interventions}
            color="yellow"
            subtext="HITL events"
          />
          <MetricCard
            label="Fail-Closed"
            value={metrics.fail_closed_triggers}
            color={metrics.fail_closed_triggers > 0 ? "red" : "gray"}
            subtext="Triggers"
          />
        </div>
      </div>

      {/* Attestations */}
      <div className="border-t border-gray-200 pt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Attestations</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2">
            <span
              className={`w-4 h-4 rounded-full ${
                summary.data_complete ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-sm text-gray-700">
              Data Complete: {summary.data_complete ? "Yes" : "No"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-4 h-4 rounded-full ${
                summary.no_hidden_state ? "bg-green-500" : "bg-red-500"
              }`}
            />
            <span className="text-sm text-gray-700">
              No Hidden State (INV-AUDIT-005): {summary.no_hidden_state ? "Yes" : "No"}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-gray-200 flex justify-between items-center text-xs text-gray-500">
        <span>System Version: {summary.system_version}</span>
        <span>API Version: {summary.api_version}</span>
      </div>
    </div>
  );
}
