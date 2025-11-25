import { AlertTriangle, Brain, FileText, TrendingUp } from "lucide-react";

import { useShipmentHealth } from "../../hooks/useShipmentHealth";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

interface ShipmentIntelligencePanelProps {
  shipmentId: string;
}

const riskLevelVariantMap = {
  LOW: "success",
  MODERATE: "warning",
  HIGH: "danger",
} as const;

export function ShipmentIntelligencePanel({ shipmentId }: ShipmentIntelligencePanelProps): JSX.Element {
  const { data, isLoading, isError } = useShipmentHealth(shipmentId);

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-purple-400" />
          <div>
            <CardTitle>Shipment Intelligence</CardTitle>
            <CardDescription>AI-powered insights for {shipmentId || "—"}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {isError && !isLoading && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            <p className="font-semibold">Unable to load shipment intelligence data.</p>
            <p className="mt-1 text-xs text-rose-200">Check ChainIQ backend availability.</p>
          </div>
        )}

        {data && !isError && (
          <div className="space-y-4">
            {/* Risk Section */}
            <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-orange-400" />
                <h3 className="text-sm font-semibold text-slate-100">Risk Assessment</h3>
              </div>

              <div className="flex items-center gap-4 mb-3">
                <div className="text-center">
                  <div className="text-3xl font-bold text-slate-100">{data.risk.score}</div>
                  <div className="text-xs text-slate-500">Risk Score</div>
                </div>
                <Badge
                  variant={riskLevelVariantMap[data.risk.level as keyof typeof riskLevelVariantMap] || "info"}
                  className="text-xs"
                >
                  {data.risk.level}
                </Badge>
              </div>

              {data.risk.drivers.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Risk Drivers</p>
                  <ul className="space-y-1">
                    {data.risk.drivers.slice(0, 3).map((driver, index) => (
                      <li key={index} className="text-xs text-slate-300 flex items-start gap-2">
                        <span className="text-orange-400">•</span>
                        <span>{driver}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Document Health Section */}
            <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
              <div className="flex items-center gap-2 mb-3">
                <FileText className="h-4 w-4 text-blue-400" />
                <h3 className="text-sm font-semibold text-slate-100">Document Health</h3>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <div className="text-lg font-semibold text-slate-100">
                    {data.documentHealth.completenessPct}%
                  </div>
                  <div className="text-xs text-slate-500">Completeness</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-slate-100">
                    {data.documentHealth.blockingGapCount}
                  </div>
                  <div className="text-xs text-slate-500">Blocking Gaps</div>
                </div>
              </div>

              {/* Mini progress bar */}
              <div className="relative h-1 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={classNames(
                    "h-full bg-blue-500 transition-all duration-300",
                    data.documentHealth.completenessPct === 0 && "w-0",
                    data.documentHealth.completenessPct > 0 && data.documentHealth.completenessPct <= 25 && "w-1/4",
                    data.documentHealth.completenessPct > 25 && data.documentHealth.completenessPct <= 50 && "w-1/2",
                    data.documentHealth.completenessPct > 50 && data.documentHealth.completenessPct <= 75 && "w-3/4",
                    data.documentHealth.completenessPct > 75 && "w-full"
                  )}
                />
              </div>
            </div>

            {/* Settlement Health Section */}
            <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-100">Settlement Health</h3>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-lg font-semibold text-slate-100">
                    {data.settlementHealth.completionPct}%
                  </div>
                  <div className="text-xs text-slate-500">Completion</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-slate-100">
                    {data.settlementHealth.milestonesPaid}/{data.settlementHealth.milestonesTotal}
                  </div>
                  <div className="text-xs text-slate-500">Milestones Paid</div>
                </div>
              </div>

              {data.settlementHealth.nextMilestone && (
                <div className="mt-2">
                  <p className="text-xs text-slate-500">Next: {data.settlementHealth.nextMilestone}</p>
                </div>
              )}
            </div>

            {/* Recommended Actions */}
            {data.recommendedActions.length > 0 && (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
                <h3 className="text-sm font-semibold text-emerald-100 mb-2">Recommended Actions</h3>
                <ul className="space-y-1">
                  {data.recommendedActions.slice(0, 4).map((action, index) => (
                    <li key={index} className="text-xs text-emerald-200 flex items-start gap-2">
                      <span className="text-emerald-400">▶</span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
