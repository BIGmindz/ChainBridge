/**
 * ShadowIntelligencePanelV2 - Enhanced Shadow Mode Intelligence Component
 *
 * Upgraded panel with:
 * - Drift sparkline visualization
 * - Top 3 drifting features display
 * - Corridor-level drift badges
 * - Trend arrow animations
 * - Focus mode integration
 *
 * WCAG AA compliant, ADHD-friendly with focus mode support.
 *
 * @module components/intel/ShadowIntelligencePanelV2
 */

import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  RefreshCw,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
} from "lucide-react";
import { useState } from "react";

import { useShouldReduceMotion } from "../../core/focus/FocusModeContext";
import { useDriftIntelligence, useDriftSparklineData, useTopDriftingFeatures } from "../../hooks/useDrift";
import { useShadowIntelligence, useShadowEvents } from "../../hooks/useShadowMode";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

import { CorridorOverviewAnimation } from "./CorridorOverviewAnimation";
import { CorridorSelector } from "./CorridorSelector";
import { DriftSignalBadge } from "./DriftSignalBadge";
import { DriftSparkline } from "./DriftSparkline";
import { ShadowEventTimeline } from "./ShadowEventTimeline";
import { ShadowKPICards } from "./ShadowKPICards";

// =============================================================================
// TYPES
// =============================================================================

interface ShadowIntelligencePanelV2Props {
  className?: string;
  compact?: boolean;
  showCorridorAnimation?: boolean;
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

/**
 * Panel-level loading skeleton.
 */
function PanelSkeleton(): JSX.Element {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="h-6 w-6 rounded" />
          <Skeleton className="h-6 w-40" />
        </div>
        <Skeleton className="h-8 w-24 rounded-full" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    </div>
  );
}

/**
 * Trend arrow with animation.
 */
function TrendArrow({
  trend,
  size = "md",
}: {
  trend: "rising" | "falling" | "stable";
  size?: "sm" | "md" | "lg";
}): JSX.Element {
  const reducedMotion = useShouldReduceMotion();

  const sizeClasses = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  const trendConfig = {
    rising: {
      Icon: TrendingUp,
      color: "text-red-400",
      label: "Rising",
      bgColor: "bg-red-500/10",
    },
    falling: {
      Icon: TrendingDown,
      color: "text-emerald-400",
      label: "Falling",
      bgColor: "bg-emerald-500/10",
    },
    stable: {
      Icon: Minus,
      color: "text-slate-400",
      label: "Stable",
      bgColor: "bg-slate-500/10",
    },
  };

  const config = trendConfig[trend];
  const Icon = config.Icon;

  return (
    <motion.div
      className={classNames(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
        config.bgColor
      )}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: reducedMotion ? 0 : 0.3 }}
    >
      <motion.div
        animate={
          reducedMotion || trend === "stable"
            ? {}
            : { y: trend === "rising" ? [-1, 1, -1] : [1, -1, 1] }
        }
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        <Icon className={classNames(sizeClasses[size], config.color)} />
      </motion.div>
      <span className={classNames("text-[10px] font-semibold uppercase", config.color)}>
        {config.label}
      </span>
    </motion.div>
  );
}

/**
 * Top drifting features card.
 */
function TopDriftingFeaturesCard({
  isLoading,
}: {
  isLoading: boolean;
}): JSX.Element {
  const reducedMotion = useShouldReduceMotion();
  const { features, totalDrifting } = useTopDriftingFeatures(3);

  if (isLoading) {
    return <Skeleton className="h-40 rounded-xl" />;
  }

  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-950/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-amber-400" />
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Top Drifting Features
          </span>
        </div>
        {totalDrifting > 3 && (
          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-bold text-amber-400">
            +{totalDrifting - 3} MORE
          </span>
        )}
      </div>

      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {features.map((feature, index) => (
            <motion.div
              key={feature.feature_name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{
                duration: reducedMotion ? 0 : 0.3,
                delay: reducedMotion ? 0 : index * 0.1,
              }}
              className={classNames(
                "flex items-center justify-between rounded-lg px-3 py-2",
                feature.is_drifting
                  ? "bg-red-500/10 border border-red-500/20"
                  : "bg-slate-800/30"
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                {/* Rank badge */}
                <span
                  className={classNames(
                    "flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold",
                    feature.is_drifting
                      ? "bg-red-500/20 text-red-400"
                      : "bg-slate-700 text-slate-400"
                  )}
                >
                  {index + 1}
                </span>
                <span className="text-sm text-slate-200 truncate">
                  {feature.feature_name}
                </span>
              </div>

              <div className="flex items-center gap-3">
                {/* Delta percentage */}
                <span
                  className={classNames(
                    "text-xs font-mono",
                    feature.delta_pct > 0.15
                      ? "text-red-400"
                      : feature.delta_pct > 0.1
                        ? "text-amber-400"
                        : "text-slate-400"
                  )}
                >
                  {feature.delta_pct > 0 ? "+" : ""}
                  {(feature.delta_pct * 100).toFixed(1)}%
                </span>

                {/* Drift indicator */}
                {feature.is_drifting && (
                  <motion.span
                    className="h-2 w-2 rounded-full bg-red-500"
                    animate={reducedMotion ? {} : { scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {features.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-slate-500">No drifting features detected</p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Drift sparkline card.
 */
function DriftSparklineCard({
  isLoading,
}: {
  isLoading: boolean;
}): JSX.Element {
  const { data: sparklineData, isLoading: sparklineLoading } = useDriftSparklineData(24);

  if (isLoading || sparklineLoading) {
    return <Skeleton className="h-40 rounded-xl" />;
  }

  return (
    <DriftSparkline
      data={sparklineData}
      width={200}
      height={60}
      showTrend
      showValue
    />
  );
}

/**
 * Corridor drift badge - inline indicator.
 */
function CorridorDriftBadge({
  corridor,
  driftScore,
  isDrifting,
}: {
  corridor: string;
  driftScore: number;
  isDrifting: boolean;
}): JSX.Element {
  const reducedMotion = useShouldReduceMotion();

  return (
    <motion.div
      className={classNames(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 border",
        isDrifting
          ? "border-red-500/30 bg-red-500/10"
          : "border-slate-700/50 bg-slate-800/50"
      )}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: reducedMotion ? 1 : 1.05 }}
    >
      <span
        className={classNames(
          "h-1.5 w-1.5 rounded-full",
          isDrifting ? "bg-red-500" : "bg-emerald-500",
          isDrifting && !reducedMotion && "animate-pulse"
        )}
      />
      <span className="text-[10px] font-medium text-slate-300">{corridor}</span>
      <span
        className={classNames(
          "text-[10px] font-mono",
          isDrifting ? "text-red-400" : "text-slate-500"
        )}
      >
        {(driftScore * 100).toFixed(0)}%
      </span>
    </motion.div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function ShadowIntelligencePanelV2({
  className,
  compact = false,
  showCorridorAnimation = true,
}: ShadowIntelligencePanelV2Props): JSX.Element {
  const reducedMotion = useShouldReduceMotion();
  const [selectedCorridor, setSelectedCorridor] = useState<string | null>(null);
  const [timeWindow] = useState(24);

  // Fetch shadow intelligence data
  const { stats, drift, corridors, isLoading, isError, error } = useShadowIntelligence(timeWindow);

  // Fetch drift intelligence data
  const driftIntel = useDriftIntelligence(timeWindow);

  // Fetch events with corridor filter
  const eventsQuery = useShadowEvents(50, selectedCorridor ?? undefined, timeWindow);

  // Handle refresh
  const handleRefresh = () => {
    stats.refetch();
    drift.refetch();
    corridors.refetch();
    eventsQuery.refetch();
    driftIntel.refetchAll();
  };

  // Error state
  if (isError) {
    return (
      <div className={classNames("rounded-2xl border border-red-500/30 bg-red-500/5 p-6", className)}>
        <div className="flex items-start gap-4">
          <AlertTriangle className="h-6 w-6 text-red-400 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-base font-semibold text-red-400">Shadow Intelligence Unavailable</h3>
            <p className="mt-1 text-sm text-slate-400">
              {error?.message || "Failed to connect to ChainIQ shadow endpoints."}
            </p>
            <button
              onClick={handleRefresh}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className={classNames("rounded-2xl border border-slate-800/70 bg-slate-900/50 p-6", className)}>
        <PanelSkeleton />
      </div>
    );
  }

  // Prepare corridor options for selector
  const corridorOptions = corridors.data?.corridors.map((c) => ({
    corridor: c.corridor,
    eventCount: c.event_count,
    driftFlag: c.drift_flag,
    p95Delta: c.p95_delta,
  })) ?? [];

  // Prepare corridor data for animation component
  const corridorStatuses = driftIntel.corridors.data?.corridors.map((c) => ({
    corridor: c.corridor,
    eventCount: c.event_count,
    driftScore: c.drift_score,
    driftFlag: c.is_drifting,
    healthScore: c.health_score,
    lastUpdated: c.last_updated,
  })) ?? [];

  return (
    <motion.div
      className={classNames("rounded-2xl border border-slate-800/70 bg-slate-900/50", className)}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: reducedMotion ? 0 : 0.3 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/50 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10">
            <Zap className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Shadow Intelligence</h2>
            <p className="text-xs text-slate-500">Model comparison & drift detection</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Drift trend arrow */}
          {driftIntel.score.data && (
            <TrendArrow trend={driftIntel.score.data.trend} size="md" />
          )}
          {/* Drift badge */}
          {drift.data && (
            <DriftSignalBadge
              driftDetected={drift.data.drift_detected}
              p95Delta={drift.data.p95_delta}
              size="md"
            />
          )}
          <button
            onClick={handleRefresh}
            disabled={stats.isFetching}
            className={classNames(
              "rounded-lg border border-slate-700/50 bg-slate-800/50 p-2 text-slate-400 transition-all",
              "hover:bg-slate-700/70 hover:text-slate-200",
              "focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
              stats.isFetching && "animate-spin"
            )}
            aria-label="Refresh data"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className={classNames("space-y-6 p-6", compact && "space-y-4 p-4")}>
        {/* Top row: Sparkline + Top Features */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <DriftSparklineCard isLoading={driftIntel.isLoading} />
          <TopDriftingFeaturesCard isLoading={driftIntel.isLoading} />
        </div>

        {/* KPI Cards */}
        <ShadowKPICards
          stats={stats.data ?? null}
          isLoading={stats.isLoading}
        />

        {/* Corridor badges strip */}
        {corridorStatuses.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {corridorStatuses.slice(0, 8).map((c) => (
              <CorridorDriftBadge
                key={c.corridor}
                corridor={c.corridor}
                driftScore={c.driftScore}
                isDrifting={c.driftFlag}
              />
            ))}
            {corridorStatuses.length > 8 && (
              <span className="rounded-full bg-slate-800/50 px-2 py-0.5 text-[10px] text-slate-400">
                +{corridorStatuses.length - 8} more
              </span>
            )}
          </div>
        )}

        {/* Corridor Selector + Timeline Grid */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Left: Corridor Analysis */}
          <div className="space-y-4">
            {showCorridorAnimation ? (
              <CorridorOverviewAnimation
                corridors={corridorStatuses}
                selectedCorridor={selectedCorridor}
                onCorridorSelect={setSelectedCorridor}
                compact
                maxVisible={4}
              />
            ) : (
              <>
                <CorridorSelector
                  corridors={corridorOptions}
                  selectedCorridor={selectedCorridor}
                  onSelect={setSelectedCorridor}
                  isLoading={corridors.isLoading}
                />

                {/* Corridor summary */}
                {corridors.data && (
                  <div className="rounded-xl border border-slate-800/50 bg-slate-950/50 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Corridor Analysis
                      </span>
                      {corridors.data.drifting_count > 0 && (
                        <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] font-bold text-red-400">
                          {corridors.data.drifting_count} DRIFTING
                        </span>
                      )}
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-2xl font-bold text-slate-100">
                          {corridors.data.total_corridors}
                        </span>
                        <p className="text-xs text-slate-500">Active Corridors</p>
                      </div>
                      <div>
                        <span className="text-2xl font-bold text-emerald-400">
                          {corridors.data.total_corridors - corridors.data.drifting_count}
                        </span>
                        <p className="text-xs text-slate-500">Healthy</p>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right: Event Timeline */}
          <ShadowEventTimeline
            events={eventsQuery.data?.events ?? []}
            isLoading={eventsQuery.isLoading}
            maxItems={compact ? 5 : 10}
          />
        </div>
      </div>
    </motion.div>
  );
}

export default ShadowIntelligencePanelV2;
