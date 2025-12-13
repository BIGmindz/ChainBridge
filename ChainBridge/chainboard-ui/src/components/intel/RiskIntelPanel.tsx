/**
 * RiskIntelPanel Component
 *
 * Shows risk intelligence summary: high-risk corridors and risk meter.
 * TODO: Wire to ChainIQ risk engine when available.
 */

import { AlertTriangle, TrendingUp } from "lucide-react";
import { CardSkeleton, InlineError } from "../ui/LoadingStates";

interface RiskIntelPanelProps {
  emphasize?: boolean;
  isLoading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
}

export default function RiskIntelPanel({ emphasize = false, isLoading, error, onRetry }: RiskIntelPanelProps): JSX.Element {
  // TODO: Replace with actual risk data from ChainIQ
  const highRiskCorridors = [
    { route: "Shanghai → LA", score: 82, trend: "up" },
    { route: "Rotterdam → NY", score: 68, trend: "stable" },
    { route: "Singapore → Vancouver", score: 54, trend: "down" },
  ];

  const overallRiskScore = 67; // Mock overall risk score

  const emphasisClass = emphasize
    ? "border-red-500/50 bg-red-500/5"
    : "border-slate-800/70 bg-slate-900/50";

  if (isLoading) {
    return <CardSkeleton className={`rounded-xl border ${emphasisClass}`} />;
  }

  if (error) {
    return (
      <div className={`rounded-xl border ${emphasisClass} p-6`}>
        <div className="mb-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-100">Risk Intelligence</h3>
        </div>
        <InlineError
          message="Risk data temporarily unavailable"
          onRetry={onRetry}
        />
      </div>
    );
  }

  return (
    <div className={`rounded-xl border ${emphasisClass} p-6`}>
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 text-slate-400" />
        <h3 className="text-base font-semibold text-slate-100">Risk Intelligence</h3>
      </div>

      {/* Risk Meter */}
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Overall Risk</span>
          <span className="text-2xl font-bold text-amber-400">{overallRiskScore}</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 transition-all"
            style={{ width: `${overallRiskScore}%` }}
            aria-label={`Risk level: ${overallRiskScore}%`}
          />
        </div>
        <div className="mt-1 flex justify-between text-[9px] uppercase tracking-wide text-slate-600">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>

      {/* High-Risk Corridors */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          High-Risk Corridors
        </h4>
        <div className="space-y-2">
          {highRiskCorridors.map((corridor, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between rounded-lg border border-slate-800/50 bg-slate-950/50 p-2"
            >
              <div className="flex-1">
                <p className="text-xs font-medium text-slate-200">{corridor.route}</p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-sm font-bold ${
                    corridor.score >= 70
                      ? "text-red-400"
                      : corridor.score >= 50
                        ? "text-amber-400"
                        : "text-emerald-400"
                  }`}
                >
                  {corridor.score}
                </span>
                <TrendingUp
                  className={`h-3.5 w-3.5 ${
                    corridor.trend === "up"
                      ? "text-red-400"
                      : corridor.trend === "down"
                        ? "text-emerald-400 rotate-180"
                        : "text-slate-500"
                  }`}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* TODO Comment */}
      <p className="mt-3 text-[9px] text-slate-600">TODO: Wire ChainIQ risk engine data.</p>
    </div>
  );
}
