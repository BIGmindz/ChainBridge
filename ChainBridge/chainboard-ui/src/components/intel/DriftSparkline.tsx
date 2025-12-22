/**
 * DriftSparkline - Real-time drift visualization component
 *
 * Visualizes drift scores over time with animated sparkline chart.
 * Integrates with Maggie+Cody /iq/drift/* endpoints.
 *
 * WCAG AA compliant with proper contrast and ARIA labels.
 * ADHD-friendly: clear visual feedback, minimal distraction.
 *
 * @module components/intel/DriftSparkline
 */

import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useMemo } from "react";

import { classNames } from "../../utils/classNames";

// =============================================================================
// TYPES
// =============================================================================

export interface DriftDataPoint {
  timestamp: string;
  score: number;
  corridor?: string;
}

export interface DriftSparklineProps {
  /** Array of drift data points to visualize */
  data: DriftDataPoint[];
  /** Width of the sparkline in pixels */
  width?: number;
  /** Height of the sparkline in pixels */
  height?: number;
  /** Show trend arrow indicator */
  showTrend?: boolean;
  /** Show current value label */
  showValue?: boolean;
  /** Drift threshold for warning state (default 0.15) */
  warningThreshold?: number;
  /** Drift threshold for critical state (default 0.25) */
  criticalThreshold?: number;
  /** Additional CSS classes */
  className?: string;
  /** Accessible label for screen readers */
  ariaLabel?: string;
  /** Compact mode for inline usage */
  compact?: boolean;
}

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Calculate trend direction from data points.
 */
function calculateTrend(data: DriftDataPoint[]): "up" | "down" | "stable" {
  if (data.length < 2) return "stable";

  const recentSlice = data.slice(-5);
  const firstHalf = recentSlice.slice(0, Math.ceil(recentSlice.length / 2));
  const secondHalf = recentSlice.slice(Math.floor(recentSlice.length / 2));

  const firstAvg = firstHalf.reduce((sum, d) => sum + d.score, 0) / firstHalf.length;
  const secondAvg = secondHalf.reduce((sum, d) => sum + d.score, 0) / secondHalf.length;

  const delta = secondAvg - firstAvg;
  if (Math.abs(delta) < 0.02) return "stable";
  return delta > 0 ? "up" : "down";
}

/**
 * Get severity level based on drift score.
 */
function getSeverity(
  score: number,
  warningThreshold: number,
  criticalThreshold: number
): "good" | "warning" | "critical" {
  if (score >= criticalThreshold) return "critical";
  if (score >= warningThreshold) return "warning";
  return "good";
}

/**
 * Build SVG path from data points.
 */
function buildSparklinePath(
  data: DriftDataPoint[],
  width: number,
  height: number,
  padding = 4
): string {
  if (data.length === 0) return "";

  const scores = data.map((d) => d.score);
  const minScore = Math.min(...scores, 0);
  const maxScore = Math.max(...scores, 0.4);
  const range = maxScore - minScore || 1;

  const effectiveWidth = width - padding * 2;
  const effectiveHeight = height - padding * 2;
  const stepX = effectiveWidth / Math.max(data.length - 1, 1);

  const points = data.map((d, i) => {
    const x = padding + i * stepX;
    const y = padding + effectiveHeight - ((d.score - minScore) / range) * effectiveHeight;
    return { x, y };
  });

  if (points.length === 1) {
    return `M ${points[0].x} ${points[0].y} L ${points[0].x + 1} ${points[0].y}`;
  }

  // Smooth curve using quadratic bezier
  let path = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const midX = (prev.x + curr.x) / 2;
    path += ` Q ${prev.x + (midX - prev.x) / 2} ${prev.y}, ${midX} ${(prev.y + curr.y) / 2}`;
    path += ` T ${curr.x} ${curr.y}`;
  }

  return path;
}

/**
 * Build filled area path for gradient background.
 */
function buildAreaPath(
  data: DriftDataPoint[],
  width: number,
  height: number,
  padding = 4
): string {
  if (data.length === 0) return "";

  const linePath = buildSparklinePath(data, width, height, padding);
  const lastPoint = data.length - 1;
  const effectiveWidth = width - padding * 2;
  const stepX = effectiveWidth / Math.max(data.length - 1, 1);
  const lastX = padding + lastPoint * stepX;

  return `${linePath} L ${lastX} ${height - padding} L ${padding} ${height - padding} Z`;
}

// =============================================================================
// COMPONENT
// =============================================================================

export function DriftSparkline({
  data,
  width = 120,
  height = 40,
  showTrend = true,
  showValue = true,
  warningThreshold = 0.15,
  criticalThreshold = 0.25,
  className,
  ariaLabel,
  compact = false,
}: DriftSparklineProps): JSX.Element {
  // Compute derived values
  const { trend, currentScore, severity, linePath, areaPath, gradientId } = useMemo(() => {
    const currentScore = data.length > 0 ? data[data.length - 1].score : 0;
    const trend = calculateTrend(data);
    const severity = getSeverity(currentScore, warningThreshold, criticalThreshold);
    const linePath = buildSparklinePath(data, width, height);
    const areaPath = buildAreaPath(data, width, height);
    const gradientId = `drift-gradient-${Math.random().toString(36).slice(2, 9)}`;

    return { trend, currentScore, severity, linePath, areaPath, gradientId };
  }, [data, width, height, warningThreshold, criticalThreshold]);

  // Color schemes per severity
  const colorSchemes = {
    good: {
      stroke: "#10b981", // emerald-500
      fill: "#10b981",
      text: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
    },
    warning: {
      stroke: "#f59e0b", // amber-500
      fill: "#f59e0b",
      text: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
    },
    critical: {
      stroke: "#ef4444", // red-500
      fill: "#ef4444",
      text: "text-red-400",
      bg: "bg-red-500/10",
      border: "border-red-500/30",
    },
  };

  const colors = colorSchemes[severity];

  // Trend icon
  const TrendIcon = {
    up: TrendingUp,
    down: TrendingDown,
    stable: Minus,
  }[trend];

  // Trend colors (up is bad for drift, down is good)
  const trendColors = {
    up: "text-red-400",
    down: "text-emerald-400",
    stable: "text-slate-400",
  };

  // Compact mode
  if (compact) {
    return (
      <div
        className={classNames("inline-flex items-center gap-1.5", className)}
        role="img"
        aria-label={ariaLabel || `Drift score: ${(currentScore * 100).toFixed(1)}%`}
      >
        <svg
          width={60}
          height={20}
          className="overflow-visible"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id={`${gradientId}-compact`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={colors.fill} stopOpacity={0.3} />
              <stop offset="100%" stopColor={colors.fill} stopOpacity={0} />
            </linearGradient>
          </defs>
          <path
            d={buildAreaPath(data, 60, 20, 2)}
            fill={`url(#${gradientId}-compact)`}
          />
          <motion.path
            d={buildSparklinePath(data, 60, 20, 2)}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </svg>
        <span className={classNames("text-xs font-mono font-medium", colors.text)}>
          {(currentScore * 100).toFixed(0)}%
        </span>
      </div>
    );
  }

  // Full mode
  return (
    <div
      className={classNames(
        "rounded-lg border p-3 transition-all",
        colors.bg,
        colors.border,
        className
      )}
      role="img"
      aria-label={ariaLabel || `Drift sparkline showing current score of ${(currentScore * 100).toFixed(1)}% with ${trend} trend`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Drift Score
        </span>
        {showTrend && (
          <AnimatePresence mode="wait">
            <motion.div
              key={trend}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className={classNames("flex items-center gap-1", trendColors[trend])}
            >
              <TrendIcon className="h-3.5 w-3.5" />
              <span className="text-[10px] font-semibold uppercase">
                {trend === "up" ? "Rising" : trend === "down" ? "Falling" : "Stable"}
              </span>
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Sparkline chart */}
      <div className="relative">
        <svg
          width={width}
          height={height}
          className="overflow-visible w-full"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={colors.fill} stopOpacity={0.4} />
              <stop offset="100%" stopColor={colors.fill} stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Threshold lines */}
          <line
            x1={0}
            y1={height - 4 - (warningThreshold / 0.4) * (height - 8)}
            x2={width}
            y2={height - 4 - (warningThreshold / 0.4) * (height - 8)}
            stroke="#f59e0b"
            strokeOpacity={0.3}
            strokeWidth={1}
            strokeDasharray="3 3"
          />
          <line
            x1={0}
            y1={height - 4 - (criticalThreshold / 0.4) * (height - 8)}
            x2={width}
            y2={height - 4 - (criticalThreshold / 0.4) * (height - 8)}
            stroke="#ef4444"
            strokeOpacity={0.3}
            strokeWidth={1}
            strokeDasharray="3 3"
          />

          {/* Area fill */}
          <motion.path
            d={areaPath}
            fill={`url(#${gradientId})`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          />

          {/* Line */}
          <motion.path
            d={linePath}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 1, ease: "easeOut" }}
          />

          {/* Current point indicator */}
          {data.length > 0 && (
            <motion.circle
              cx={width - 4}
              cy={4 + (height - 8) - (currentScore / 0.4) * (height - 8)}
              r={4}
              fill={colors.stroke}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.8, type: "spring", stiffness: 300 }}
            />
          )}
        </svg>

        {/* Pulsing indicator for critical */}
        {severity === "critical" && (
          <motion.div
            className="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-500"
            animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </div>

      {/* Value display */}
      {showValue && (
        <div className="mt-2 flex items-baseline gap-2">
          <motion.span
            key={currentScore}
            className={classNames("text-xl font-bold font-mono", colors.text)}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {(currentScore * 100).toFixed(1)}%
          </motion.span>
          <span className="text-xs text-slate-500">
            P95 delta
          </span>
        </div>
      )}

      {/* Data point count */}
      <div className="mt-1 text-[10px] text-slate-600">
        {data.length} samples
      </div>
    </div>
  );
}

export default DriftSparkline;
