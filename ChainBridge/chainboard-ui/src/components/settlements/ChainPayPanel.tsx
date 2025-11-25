import { AlertTriangle, CheckCircle2, DollarSign, RefreshCw } from "lucide-react";
import { useMemo } from "react";

import { useChainPayPlan } from "../../hooks/useChainPay";
import { formatUSD } from "../../lib/formatters";
import type { ChainPayPlan } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

interface ChainPayPanelProps {
  shipmentId: string;
}

const milestoneVariantMap: Record<ChainPayPlan["milestones"][number]["status"], Parameters<typeof Badge>[0]["variant"]> = {
  PAID: "success",
  PENDING: "info",
  HELD: "warning",
};

const alertVariantMap = {
  info: "info",
  warning: "warning",
  critical: "danger",
} as const;

export function ChainPayPanel({ shipmentId }: ChainPayPanelProps): JSX.Element {
  const { data, isLoading, isError, error, refetch, isFetching } = useChainPayPlan(shipmentId);

  const { releasedPercent, releasedSegments } = useMemo(() => {
    if (!data) {
      return { releasedPercent: 0, releasedSegments: 0 };
    }
    const paidPercent = data.milestones
      .filter((milestone) => milestone.status === "PAID")
      .reduce((sum, milestone) => sum + milestone.payoutPercent, 0);

    const percent = Math.min(100, Math.max(0, Math.round(paidPercent)));
    return {
      releasedPercent: percent,
      releasedSegments: Math.min(20, Math.max(0, Math.round(percent / 5))),
    };
  }, [data]);

  return (
    <Card className="h-full">
      <CardHeader className="flex items-start justify-between gap-4">
        <div>
          <CardTitle>ChainPay Settlement Plan</CardTitle>
          <CardDescription>Template-driven payouts for {shipmentId || "—"}</CardDescription>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={classNames("h-3.5 w-3.5", isFetching && "animate-spin")} />
          Refresh
        </button>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {isError && !isLoading && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            <p className="font-semibold">Unable to load ChainPay settlement data. Check backend availability.</p>
            {error && (
              <p className="mt-1 text-xs text-rose-200">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            )}
          </div>
        )}

        {data && !isError && (
          <div className="space-y-5">
            <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-emerald-400" />
                  <div>
                    <p className="text-xs uppercase tracking-wider text-slate-500">Template</p>
                    <p className="text-sm font-semibold text-slate-100">{data.templateId}</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500">Coverage</p>
                  <p className="text-sm font-semibold text-slate-100">{data.coveragePercent}% advanced</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500">Float reduction</p>
                  <p className="text-sm font-semibold text-slate-100">{data.floatReductionEstimate}%</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500">Credit terms</p>
                  <p className="text-sm font-semibold text-slate-100">{data.creditTermsDays} days</p>
                </div>
              </div>
              <div className="mt-4">
                <p className="text-xs uppercase tracking-wider text-slate-500">Release progress</p>
                <div className="mt-2 flex gap-1">
                  {Array.from({ length: 20 }).map((_, idx) => (
                    <span
                      key={idx}
                      className={classNames(
                        "h-2 flex-1 rounded-full",
                        idx < releasedSegments ? "bg-emerald-500" : "bg-slate-800"
                      )}
                      aria-hidden="true"
                    />
                  ))}
                </div>
                <p className="mt-1 text-[11px] text-slate-500">{releasedPercent}% of milestones released</p>
              </div>
            </div>

            <div className="space-y-3">
              {data.milestones.map((milestone) => (
                <div
                  key={milestone.id}
                  className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-100">{milestone.label}</p>
                      <p className="text-[11px] text-slate-500">
                        {milestone.payoutPercent}% · {formatUSD(milestone.amountUsd)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={milestoneVariantMap[milestone.status]}>
                        {milestone.status}
                      </Badge>
                      {(data?.docRisk?.missingBlockingDocs.length ?? 0) > 0 && milestone.status !== "PAID" && (
                        <div className="flex items-center gap-1 text-[10px] text-amber-400">
                          <AlertTriangle className="h-3 w-3" />
                          <span>Docs gating</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-4 text-[11px] text-slate-500">
                    <span>Expected: {new Date(milestone.expectedRelease).toLocaleString()}</span>
                    {milestone.paidAt && <span>Paid: {new Date(milestone.paidAt).toLocaleString()}</span>}
                    {milestone.holdReason && (
                      <span className="text-amber-300">Hold: {milestone.holdReason}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {data?.docRisk && (
              <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-orange-400" />
                    <div>
                      <p className="text-xs uppercase tracking-wider text-slate-500">Document Risk</p>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            data.docRisk.level === "LOW"
                              ? "success"
                              : data.docRisk.level === "MEDIUM"
                              ? "warning"
                              : "danger"
                          }
                          className="text-[10px]"
                        >
                          {data.docRisk.level}
                        </Badge>
                        <span className="text-sm font-semibold text-slate-100">
                          {data.docRisk.score}/100
                        </span>
                      </div>
                    </div>
                  </div>
                  {data.docRisk.missingBlockingDocs.length > 0 && (
                    <div className="flex-1">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Blocking Documents</p>
                      <p className="text-[11px] text-rose-300 mt-1">
                        {data.docRisk.missingBlockingDocs.join(", ")}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {data.alerts.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    ChainPay Alerts
                  </p>
                </div>
                {data.alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="rounded-lg border border-slate-800/60 bg-slate-950/50 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant={alertVariantMap[alert.severity]}>{alert.severity}</Badge>
                      <span className="text-[10px] text-slate-600">
                        {new Date(alert.createdAt).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-200">{alert.message}</p>
                  </div>
                ))}
              </div>
            )}

            {data.alerts.length === 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-100">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                No active ChainPay alerts
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
