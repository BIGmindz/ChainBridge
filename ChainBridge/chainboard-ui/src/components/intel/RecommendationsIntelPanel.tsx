/**
 * RecommendationsIntelPanel Component
 *
 * Shows actionable intelligence recommendations derived from alerts,
 * IoT issues, and payment states.
 * TODO: Wire to real recommendation engine when available.
 */

import { ChevronRight, Lightbulb } from "lucide-react";

interface RecommendationsIntelPanelProps {
  emphasize?: boolean;
}

interface Recommendation {
  id: string;
  title: string;
  category: "risk" | "iot" | "payment" | "ops";
  priority: "high" | "medium" | "low";
  action?: string;
}

export default function RecommendationsIntelPanel({
  emphasize = false,
}: RecommendationsIntelPanelProps): JSX.Element {
  // TODO: Replace with real recommendation engine data
  const recommendations: Recommendation[] = [
    {
      id: "1",
      title: "Escalate corridor risk for Shanghai → LA shipments",
      category: "risk",
      priority: "high",
      action: "/triage?filter=risk",
    },
    {
      id: "2",
      title: "Review temperature anomalies for pharma containers",
      category: "iot",
      priority: "high",
      action: "/exceptions?source=iot",
    },
    {
      id: "3",
      title: "Clear overdue payment milestones for SHP-2025-027",
      category: "payment",
      priority: "medium",
      action: "/shipments?payment_status=blocked",
    },
    {
      id: "4",
      title: "Optimize sensor deployment in Asia-Pacific region",
      category: "iot",
      priority: "medium",
    },
    {
      id: "5",
      title: "Update risk models for Q4 seasonal patterns",
      category: "risk",
      priority: "low",
    },
  ];

  const highPriorityCount = recommendations.filter((r) => r.priority === "high").length;

  const emphasisClass = emphasize
    ? "border-amber-500/50 bg-amber-500/5"
    : "border-slate-800/70 bg-slate-900/50";

  const categoryColors = {
    risk: "text-red-400",
    iot: "text-blue-400",
    payment: "text-emerald-400",
    ops: "text-amber-400",
  };

  const priorityBadgeClass = {
    high: "border-red-500/50 bg-red-500/10 text-red-300",
    medium: "border-amber-500/50 bg-amber-500/10 text-amber-300",
    low: "border-slate-500/50 bg-slate-500/10 text-slate-300",
  };

  return (
    <div className={`rounded-xl border ${emphasisClass} p-6`}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Lightbulb className="h-5 w-5 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-100">Recommendations & Insights</h3>
        </div>
        {highPriorityCount > 0 && (
          <div className="rounded-full border border-red-500/50 bg-red-500/10 px-2 py-0.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-red-300">
              {highPriorityCount} High Priority
            </span>
          </div>
        )}
      </div>

      {/* Recommendations List */}
      <div className="space-y-2">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="group flex items-start gap-2 rounded-lg border border-slate-800/50 bg-slate-950/50 p-3 transition-colors hover:border-slate-700 hover:bg-slate-900/50"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[9px] font-semibold uppercase tracking-wider ${categoryColors[rec.category]}`}
                >
                  {rec.category}
                </span>
                <span
                  className={`rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${priorityBadgeClass[rec.priority]}`}
                >
                  {rec.priority}
                </span>
              </div>
              <p className="mt-1 text-xs font-medium text-slate-200">{rec.title}</p>
            </div>
            {rec.action && (
              <ChevronRight className="h-4 w-4 flex-shrink-0 text-slate-600 transition-colors group-hover:text-slate-400" />
            )}
          </div>
        ))}
      </div>

      {/* TODO Comment */}
      <p className="mt-3 text-[9px] text-slate-600">
        TODO: Wire real recommendation engine with ML-powered insights.
      </p>
    </div>
  );
}
