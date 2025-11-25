import { FileText, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { useMemo } from "react";

import { useChainDocsDossier, useSeedDemoDocuments } from "../../hooks/useChainDocs";
import { useShipmentHealth } from "../../hooks/useShipmentHealth";
import type { ChainDocRecord } from "../../types/chainbridge";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

interface ChainDocsPanelProps {
  shipmentId: string;
}

const statusVariantMap: Record<ChainDocRecord["status"], Parameters<typeof Badge>[0]["variant"]> = {
  VERIFIED: "success",
  PRESENT: "info",
  MISSING: "danger",
  FLAGGED: "warning",
};

function hashPreview(hash: string): string {
  if (hash.length <= 10) return hash;
  return `${hash.slice(0, 6)}…${hash.slice(-4)}`;
}

export function ChainDocsPanel({ shipmentId }: ChainDocsPanelProps): JSX.Element {
  const { data, isLoading, isError, error, refetch, isFetching } = useChainDocsDossier(shipmentId);
  const { data: health } = useShipmentHealth(shipmentId);
  const seedMutation = useSeedDemoDocuments(shipmentId);
  const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

  const { confidencePercent, filledSegments, readinessMetrics } = useMemo(() => {
    if (!data) {
      return { confidencePercent: 0, filledSegments: 0, readinessMetrics: { totalRequired: 0, presentCount: 0, completenessPct: 0, blockingGapCount: 0 } };
    }
    const percent = Math.round(data.aiConfidenceScore * 100);

    // Use health data if available, otherwise fallback to dossier calculation
    let readinessMetrics = {
      totalRequired: data.documents.length + data.missingDocuments.length,
      presentCount: data.documents.length,
      completenessPct: 0,
      blockingGapCount: 0,
    };

    if (health?.documentHealth) {
      readinessMetrics = {
        totalRequired: health.documentHealth.requiredTotal,
        presentCount: health.documentHealth.presentCount,
        completenessPct: health.documentHealth.completenessPct,
        blockingGapCount: health.documentHealth.blockingGapCount,
      };
    } else {
      readinessMetrics.completenessPct = readinessMetrics.totalRequired > 0
        ? Math.round((readinessMetrics.presentCount / readinessMetrics.totalRequired) * 100)
        : 0;
    }

    return {
      confidencePercent: percent,
      filledSegments: Math.min(10, Math.max(0, Math.round(percent / 10))),
      readinessMetrics,
    };
  }, [data, health]);

  return (
    <Card className="h-full">
      <CardHeader className="flex items-start justify-between gap-4">
        <div>
          <CardTitle>ChainDocs Dossier</CardTitle>
          <CardDescription>
            Policy-anchored documents for {shipmentId || "—"}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {isDemoMode && shipmentId && (
            <button
              type="button"
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending || isFetching}
              className="inline-flex items-center gap-1 rounded-lg border border-blue-600 bg-blue-600/20 px-3 py-1.5 text-xs font-medium text-blue-200 transition-colors hover:border-blue-500 hover:bg-blue-600/30 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {seedMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FileText className="h-3.5 w-3.5" />
              )}
              Seed Demo Documents
            </button>
          )}
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={classNames("h-3.5 w-3.5", isFetching && "animate-spin")} />
            Refresh
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {seedMutation.isError && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-100">
            <p>Failed to seed demo documents. Please try again.</p>
            {seedMutation.error && (
              <p className="mt-1 text-[11px] text-rose-200">
                {seedMutation.error.message}
              </p>
            )}
          </div>
        )}

        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        )}

        {isError && !isLoading && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
            <p className="font-semibold">Unable to load ChainDocs data. Check backend availability.</p>
            {error && (
              <p className="mt-1 text-xs text-rose-200">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            )}
          </div>
        )}

        {data && !isError && (
          <div className="space-y-4">
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-emerald-400" />
                    <div>
                      <p className="text-xs uppercase tracking-wider text-slate-500">AI Confidence</p>
                      <p className="text-lg font-semibold text-slate-100">{confidencePercent}%</p>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex gap-1">
                      {Array.from({ length: 10 }).map((_, idx) => (
                        <span
                          key={idx}
                          className={classNames(
                            "h-2 flex-1 rounded-full",
                            idx < filledSegments ? "bg-emerald-500" : "bg-slate-800"
                          )}
                          aria-hidden="true"
                        />
                      ))}
                    </div>
                    <p className="mt-1 text-[11px] text-slate-500">
                      Last policy review: {new Date(data.lastPolicyReview).toLocaleString()}
                    </p>
                  </div>
                  {data.missingDocuments.length > 0 && (
                    <Badge variant="warning" className="whitespace-nowrap">
                      {data.missingDocuments.length} missing
                    </Badge>
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-slate-800/70 bg-slate-900/60 p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-400" />
                    <div>
                      <p className="text-xs uppercase tracking-wider text-slate-500">Document Readiness</p>
                      <p className="text-lg font-semibold text-slate-100">{readinessMetrics.completenessPct}%</p>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="relative h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={classNames(
                          "h-full bg-blue-500 transition-all duration-300",
                          readinessMetrics.completenessPct === 0 && "w-0",
                          readinessMetrics.completenessPct > 0 && readinessMetrics.completenessPct <= 25 && "w-1/4",
                          readinessMetrics.completenessPct > 25 && readinessMetrics.completenessPct <= 50 && "w-1/2",
                          readinessMetrics.completenessPct > 50 && readinessMetrics.completenessPct <= 75 && "w-3/4",
                          readinessMetrics.completenessPct > 75 && "w-full"
                        )}
                      />
                    </div>
                    <p className="mt-1 text-[11px] text-slate-500">
                      {readinessMetrics.presentCount} of {readinessMetrics.totalRequired} required documents present ({readinessMetrics.completenessPct}%)
                    </p>
                  </div>
                  {readinessMetrics.blockingGapCount > 0 && (
                    <Badge variant="danger" className="whitespace-nowrap">
                      {readinessMetrics.blockingGapCount} blocking
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {(data.missingDocuments.length > 0 || (health?.documentHealth.missingDocuments.length ?? 0) > 0) && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3">
                <p className="text-xs font-semibold text-rose-100 mb-1">
                  {readinessMetrics.blockingGapCount > 0 ? "Blocking Gaps" : "Missing Documents"}
                </p>
                <p className="text-xs text-rose-200">
                  {health?.documentHealth.missingDocuments.length
                    ? health.documentHealth.missingDocuments.join(", ")
                    : data.missingDocuments.join(", ")
                  }
                </p>
                {readinessMetrics.blockingGapCount > 0 && (
                  <p className="text-[11px] text-rose-300 mt-1">
                    {readinessMetrics.blockingGapCount} document(s) are blocking settlement
                  </p>
                )}
              </div>
            )}

            <div className="space-y-3">
              {data.documents.map((doc) => (
                <div
                  key={doc.documentId}
                  className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-slate-100">{doc.type}</p>
                      <p className="text-[11px] text-slate-500">{doc.documentId} · v{doc.version}</p>
                    </div>
                    <Badge variant={statusVariantMap[doc.status]}>{doc.status}</Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-4 text-[11px] text-slate-500">
                    <span className="font-mono text-slate-400">{hashPreview(doc.hash)}</span>
                    <span>{doc.issuedBy}</span>
                    <span>{doc.storageLocation.split("/").slice(-1)}</span>
                    {doc.complianceTags.length > 0 && (
                      <span className="text-slate-400">
                        {doc.complianceTags.join(" · ")}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
