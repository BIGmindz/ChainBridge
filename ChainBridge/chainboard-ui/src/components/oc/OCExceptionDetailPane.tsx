/**
 * OCExceptionDetailPane - Right Pane Detail View for The OC
 *
 * Displays detailed information for a selected exception:
 * - Exception header with severity and status
 * - Shipment overview link
 * - Risk summary panel (ChainIQ - LIVE)
 * - Settlement summary panel (ChainPay stub)
 * - Playbook section with action buttons
 *
 * "Deep dive when the radar blip demands attention."
 */

import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle,
  Clock,
  DollarSign,
  ExternalLink,
  Loader2,
  PlayCircle,
  Shield,
  Truck,
} from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import {
  useExceptionDetail,
  useShipmentSettlement,
  useUpdateExceptionStatus,
} from "../../hooks/useExceptions";
import { useShipmentRisk } from "../../hooks/useRisk";
import type { ExceptionSeverity, PlaybookStepStatus } from "../../types/exceptions";
import type { ShipmentRiskContext, RiskDecision } from "../../types/risk";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import { Skeleton } from "../ui/Skeleton";

interface OCExceptionDetailPaneProps {
  selectedExceptionId: string | null;
}

// Severity badge variant mapping
const severityVariant: Record<ExceptionSeverity, "danger" | "warning" | "info" | "default"> = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "info",
  LOW: "default",
};

// Format relative time
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function formatCurrency(amount: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center text-center p-8">
      <div>
        <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-slate-600" />
        <p className="text-slate-400 font-medium">Select an exception</p>
        <p className="text-xs text-slate-500 mt-1">
          Click on an item in the queue to view details
        </p>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="p-4 space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

// Risk Summary Panel Component - LIVE ChainIQ Integration
// Decision chip color/label mapping
const decisionStyles: Record<RiskDecision, { bg: string; text: string; label: string }> = {
  APPROVE: { bg: "bg-emerald-900/50", text: "text-emerald-400", label: "Approve" },
  HOLD: { bg: "bg-amber-900/50", text: "text-amber-400", label: "Hold" },
  TIGHTEN_TERMS: { bg: "bg-orange-900/50", text: "text-orange-400", label: "Tighten Terms" },
  ESCALATE: { bg: "bg-rose-900/50", text: "text-rose-400", label: "Escalate" },
};

interface RiskSummaryPanelProps {
  shipmentId: string;
  /** Optional additional context from exception metadata */
  context?: Partial<Omit<ShipmentRiskContext, "shipmentId">>;
}

function RiskSummaryPanel({ shipmentId, context }: RiskSummaryPanelProps) {
  // Build the full risk context
  const riskContext: ShipmentRiskContext | undefined = useMemo(() => {
    if (!shipmentId) return undefined;
    return {
      shipmentId,
      origin: context?.origin,
      destination: context?.destination,
      carrierId: context?.carrierId,
      carrierName: context?.carrierName,
      mode: context?.mode,
      valueUsd: context?.valueUsd,
      commodityType: context?.commodityType,
    };
  }, [shipmentId, context]);

  const { data: riskData, isLoading, error } = useShipmentRisk(riskContext);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="border-b border-slate-800/50">
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-sky-400" />
            Risk Summary
            <Loader2 className="h-3 w-3 animate-spin text-slate-500 ml-auto" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !riskData) {
    return (
      <Card>
        <CardHeader className="border-b border-slate-800/50">
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-sky-400" />
            Risk Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-slate-500">
            {error ? "Unable to load risk data" : "No risk data available"}
          </p>
          {error && (
            <p className="text-[10px] text-rose-400/70 mt-1">
              {error.message}
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  const riskScore = riskData.riskScore;
  const riskColor =
    riskScore >= 80 ? "text-rose-400" :
    riskScore >= 60 ? "text-amber-400" :
    riskScore >= 40 ? "text-sky-400" : "text-emerald-400";

  const decisionStyle = decisionStyles[riskData.decision] ?? {
    bg: "bg-slate-800",
    text: "text-slate-400",
    label: riskData.decision,
  };

  return (
    <Card>
      <CardHeader className="border-b border-slate-800/50">
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-sky-400" />
          Risk Summary
          <span className="text-[10px] text-slate-500 font-normal ml-auto">
            ChainIQ {riskData.modelVersion ? `v${riskData.modelVersion}` : ""}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Score + Decision Row */}
        <div className="flex items-center gap-3">
          {/* Risk Score Gauge */}
          <div className="text-center p-3 bg-slate-800/50 rounded-lg flex-shrink-0">
            <div className={classNames("text-2xl font-mono font-bold", riskColor)}>
              {riskScore}
            </div>
            <div className="text-[10px] text-slate-500 uppercase">Risk Score</div>
          </div>

          {/* Decision Chip */}
          <div
            className={classNames(
              "flex-1 py-2 px-3 rounded-lg text-center",
              decisionStyle.bg
            )}
          >
            <div className={classNames("text-sm font-semibold", decisionStyle.text)}>
              {decisionStyle.label}
            </div>
            <div className="text-[10px] text-slate-500">Recommendation</div>
          </div>
        </div>

        {/* Top Factors */}
        {riskData.topFactors && riskData.topFactors.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wide">
              Top Risk Factors
            </div>
            {riskData.topFactors.slice(0, 3).map((factor, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {/* Direction arrow */}
                {factor.direction === "UP" ? (
                  <ArrowUpRight className="h-3 w-3 text-rose-400 flex-shrink-0" />
                ) : (
                  <ArrowDownRight className="h-3 w-3 text-emerald-400 flex-shrink-0" />
                )}
                {/* Factor name */}
                <span className="text-slate-300 flex-1 truncate">{factor.name}</span>
                {/* Weight badge */}
                <span
                  className={classNames(
                    "font-mono text-[10px] px-1.5 py-0.5 rounded",
                    factor.weight >= 0.3
                      ? "bg-rose-900/50 text-rose-400"
                      : factor.weight >= 0.15
                      ? "bg-amber-900/50 text-amber-400"
                      : "bg-slate-800 text-slate-400"
                  )}
                >
                  {(factor.weight * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Tags */}
        {riskData.tags && riskData.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {riskData.tags.map((tag) => (
              <span
                key={tag}
                className="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <p className="text-[10px] text-slate-500 italic">
          Risk scoring by ChainIQ • {riskData.scoredAt ? new Date(riskData.scoredAt).toLocaleString() : "Live"}
        </p>
      </CardContent>
    </Card>
  );
}

// Settlement Summary Panel Component
function SettlementSummaryPanel({ shipmentId }: { shipmentId: string }) {
  const { data: settlementData, isLoading, error } = useShipmentSettlement(shipmentId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="border-b border-slate-800/50">
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-400" />
            Settlement Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !settlementData) {
    return (
      <Card>
        <CardHeader className="border-b border-slate-800/50">
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-400" />
            Settlement Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-slate-500">Unable to load settlement data</p>
        </CardContent>
      </Card>
    );
  }

  const releasePercent = (settlementData.released_amount / settlementData.total_amount) * 100;

  return (
    <Card>
      <CardHeader className="border-b border-slate-800/50">
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-emerald-400" />
          Settlement Summary
          <span className="text-[10px] text-slate-500 font-normal ml-auto">
            ChainPay
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Policy Name */}
        <div className="text-xs text-slate-400">
          Policy: <span className="text-slate-200">{settlementData.policy_name ?? "N/A"}</span>
        </div>

        {/* Amount Summary */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Released</span>
          <span className="font-mono text-emerald-400">
            {formatCurrency(settlementData.released_amount, settlementData.currency)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Held</span>
          <span className="font-mono text-amber-400">
            {formatCurrency(settlementData.held_amount, settlementData.currency)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm border-t border-slate-700 pt-2">
          <span className="text-slate-300">Total</span>
          <span className="font-mono text-slate-200 font-bold">
            {formatCurrency(settlementData.total_amount, settlementData.currency)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-slate-500">
            <span>Release Progress</span>
            <span>{releasePercent.toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden relative">
            <div
              className={classNames(
                "h-full bg-emerald-500 rounded-full transition-all absolute left-0 top-0",
                releasePercent >= 100 ? "w-full" :
                releasePercent >= 75 ? "w-3/4" :
                releasePercent >= 50 ? "w-1/2" :
                releasePercent >= 25 ? "w-1/4" :
                releasePercent > 0 ? "w-[10%]" : "w-0"
              )}
              aria-label={`${releasePercent.toFixed(0)}% released`}
            />
          </div>
        </div>

        {/* Milestones */}
        <div className="space-y-1">
          <div className="text-[10px] font-bold uppercase text-slate-500">Milestones</div>
          <div className="flex items-center gap-1">
            {settlementData.milestones.map((milestone, i) => (
              <div
                key={i}
                className={classNames(
                  "flex-1 h-2 rounded",
                  milestone.status === "COMPLETED" ? "bg-emerald-500" :
                  milestone.status === "HELD" ? "bg-amber-500" : "bg-slate-700"
                )}
                title={`${milestone.name} (${milestone.percentage}%)`}
              />
            ))}
          </div>
          <div className="flex justify-between text-[9px] text-slate-500">
            {settlementData.milestones.map((milestone, i) => (
              <span key={i} className="truncate flex-1 text-center" title={milestone.name}>
                {milestone.name}
              </span>
            ))}
          </div>
        </div>

        <p className="text-[10px] text-slate-500 italic">
          Settlement provided by ChainPay
        </p>
      </CardContent>
    </Card>
  );
}

// Playbook Section Component
function PlaybookSection({
  playbook,
  exceptionId,
  exceptionStatus,
}: {
  playbook?: {
    id: string;
    name: string;
    steps: Array<{ id: string; title: string; status: PlaybookStepStatus }>;
  };
  exceptionId: string;
  exceptionStatus: string;
}) {
  const updateStatus = useUpdateExceptionStatus();

  const handleMarkInProgress = () => {
    updateStatus.mutate({ exceptionId, status: "IN_PROGRESS" });
  };

  const handleMarkResolved = () => {
    updateStatus.mutate({ exceptionId, status: "RESOLVED" });
  };

  return (
    <Card>
      <CardHeader className="border-b border-slate-800/50">
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-violet-400" />
          Playbook & Actions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {playbook ? (
          <>
            <div className="text-xs text-slate-400">
              Active Playbook: <span className="text-slate-200">{playbook.name}</span>
            </div>

            {/* Steps Progress */}
            <div className="space-y-2">
              {playbook.steps.slice(0, 4).map((step, i) => (
                <div key={step.id} className="flex items-center gap-2">
                  <div className={classNames(
                    "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold",
                    step.status === "COMPLETED" ? "bg-emerald-500/20 text-emerald-400" :
                    step.status === "IN_PROGRESS" ? "bg-amber-500/20 text-amber-400" :
                    "bg-slate-700 text-slate-500"
                  )}>
                    {step.status === "COMPLETED" ? <CheckCircle className="h-3 w-3" /> : i + 1}
                  </div>
                  <span className={classNames(
                    "text-xs",
                    step.status === "COMPLETED" ? "text-slate-500 line-through" :
                    step.status === "IN_PROGRESS" ? "text-amber-300" : "text-slate-400"
                  )}>
                    {step.title}
                  </span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="text-xs text-slate-500">
            No playbook assigned. Manual resolution required.
          </p>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2 border-t border-slate-800">
          <button
            onClick={handleMarkInProgress}
            disabled={exceptionStatus === "IN_PROGRESS" || exceptionStatus === "RESOLVED" || updateStatus.isPending}
            className={classNames(
              "flex-1 px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors",
              exceptionStatus === "IN_PROGRESS" || exceptionStatus === "RESOLVED"
                ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                : "bg-amber-600/20 text-amber-300 hover:bg-amber-600/30"
            )}
          >
            {updateStatus.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <PlayCircle className="h-3 w-3" />
            )}
            Mark In Progress
          </button>
          <button
            onClick={handleMarkResolved}
            disabled={exceptionStatus === "RESOLVED" || updateStatus.isPending}
            className={classNames(
              "flex-1 px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors",
              exceptionStatus === "RESOLVED"
                ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                : "bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30"
            )}
          >
            {updateStatus.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle className="h-3 w-3" />
            )}
            Mark Resolved
          </button>
        </div>

        {playbook && (
          <button
            disabled
            className="w-full px-3 py-2 rounded-lg text-xs font-medium bg-violet-600/10 text-violet-400 opacity-50 cursor-not-allowed flex items-center justify-center gap-1.5"
          >
            <BookOpen className="h-3 w-3" />
            Open Full Playbook
            <span className="text-[9px] text-slate-500">(coming soon)</span>
          </button>
        )}
      </CardContent>
    </Card>
  );
}

export function OCExceptionDetailPane({ selectedExceptionId }: OCExceptionDetailPaneProps) {
  const { data, isLoading, error } = useExceptionDetail(selectedExceptionId);

  if (!selectedExceptionId) {
    return <EmptyState />;
  }

  if (isLoading) {
    return <LoadingState />;
  }

  if (error || !data) {
    return (
      <div className="p-4">
        <div className="bg-rose-950/30 border border-rose-900/50 rounded-lg px-4 py-3 text-rose-300 text-sm">
          <AlertTriangle className="h-4 w-4 inline mr-2" />
          Unable to load exception details
        </div>
      </div>
    );
  }

  const { exception, playbook } = data;
  const isResolved = exception.status === "RESOLVED" || exception.status === "DISMISSED";

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={severityVariant[exception.severity]}>
            {exception.severity}
          </Badge>
          <Badge variant={isResolved ? "success" : exception.status === "IN_PROGRESS" ? "warning" : "outline"}>
            {exception.status}
          </Badge>
          <span className="text-xs font-mono text-slate-500">
            {exception.id}
          </span>
        </div>

        <h2 className="text-lg font-semibold text-white">
          {exception.summary}
        </h2>

        {exception.description && (
          <p className="text-sm text-slate-400">
            {exception.description}
          </p>
        )}

        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Created {formatRelativeTime(exception.created_at)}
          </span>
          {exception.owner_name && (
            <span>
              Owner: <span className="text-slate-300">{exception.owner_name}</span>
            </span>
          )}
        </div>
      </div>

      {/* Shipment Overview */}
      <Card>
        <CardHeader className="border-b border-slate-800/50">
          <CardTitle className="flex items-center gap-2">
            <Truck className="h-4 w-4 text-slate-400" />
            Shipment Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono text-slate-200">
                {exception.shipment_reference ?? exception.shipment_id}
              </div>
              <div className="text-xs text-slate-500">
                ID: {exception.shipment_id}
              </div>
            </div>
            <Link
              to={`/shipments?id=${exception.shipment_id}`}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition-colors"
            >
              View Shipment
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Risk Summary - LIVE ChainIQ Integration */}
      <RiskSummaryPanel
        shipmentId={exception.shipment_id}
        context={{
          origin: exception.metadata?.origin as string | undefined,
          destination: exception.metadata?.destination as string | undefined,
          carrierId: exception.metadata?.carrier_id as string | undefined,
          carrierName: exception.metadata?.carrier_name as string | undefined,
          mode: exception.metadata?.mode as string | undefined,
          valueUsd: exception.metadata?.value_usd as number | undefined,
          commodityType: exception.metadata?.commodity_type as string | undefined,
        }}
      />

      {/* Settlement Summary - ChainPay Stub */}
      <SettlementSummaryPanel shipmentId={exception.shipment_id} />

      {/* Playbook & Actions */}
      <PlaybookSection
        playbook={playbook}
        exceptionId={exception.id}
        exceptionStatus={exception.status}
      />
    </div>
  );
}
