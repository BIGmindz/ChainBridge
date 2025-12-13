/**
 * CorridorOverviewAnimation - Animated corridor status visualization
 *
 * Displays corridor health with framer-motion animations.
 * WCAG AA compliant, ADHD-friendly with reduced motion support.
 *
 * @module components/intel/CorridorOverviewAnimation
 */

import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Activity, AlertTriangle, CheckCircle, ChevronRight, MapPin } from "lucide-react";
import { useState } from "react";

import { classNames } from "../../utils/classNames";

// =============================================================================
// TYPES
// =============================================================================

export interface CorridorStatus {
  corridor: string;
  eventCount: number;
  driftScore: number;
  driftFlag: boolean;
  healthScore: number; // 0-100
  lastUpdated: string;
}

export interface CorridorOverviewAnimationProps {
  corridors: CorridorStatus[];
  onCorridorSelect?: (corridor: string) => void;
  selectedCorridor?: string | null;
  className?: string;
  compact?: boolean;
  maxVisible?: number;
}

// =============================================================================
// HELPERS
// =============================================================================

function getHealthLevel(score: number): "healthy" | "warning" | "critical" {
  if (score >= 80) return "healthy";
  if (score >= 50) return "warning";
  return "critical";
}

const healthColors = {
  healthy: {
    bg: "bg-emerald-500",
    bgLight: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-400",
    glow: "shadow-emerald-500/20",
  },
  warning: {
    bg: "bg-amber-500",
    bgLight: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    glow: "shadow-amber-500/20",
  },
  critical: {
    bg: "bg-red-500",
    bgLight: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
    glow: "shadow-red-500/20",
  },
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

interface CorridorCardProps {
  corridor: CorridorStatus;
  isSelected: boolean;
  onClick: () => void;
  index: number;
  reducedMotion: boolean | null;
}

function CorridorCard({
  corridor,
  isSelected,
  onClick,
  index,
  reducedMotion,
}: CorridorCardProps): JSX.Element {
  const healthLevel = getHealthLevel(corridor.healthScore);
  const colors = healthColors[healthLevel];

  // Animation variants
  const cardVariants = {
    hidden: {
      opacity: 0,
      y: reducedMotion ? 0 : 20,
      scale: reducedMotion ? 1 : 0.95,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        duration: reducedMotion ? 0.1 : 0.4,
        delay: reducedMotion ? 0 : index * 0.05,
        ease: "easeOut" as const,
      },
    },
    exit: {
      opacity: 0,
      scale: reducedMotion ? 1 : 0.95,
      transition: { duration: 0.2 },
    },
    hover: {
      scale: reducedMotion ? 1 : 1.02,
      transition: { duration: 0.2 },
    },
    tap: {
      scale: reducedMotion ? 1 : 0.98,
    },
  };

  return (
    <motion.button
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      whileHover="hover"
      whileTap="tap"
      onClick={onClick}
      className={classNames(
        "relative w-full rounded-xl border p-3 text-left transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-indigo-500/50",
        isSelected
          ? "border-indigo-500/50 bg-indigo-500/10"
          : `border-slate-700/50 bg-slate-900/50 hover:bg-slate-800/70`,
        corridor.driftFlag && "ring-1 ring-red-500/30"
      )}
      role="option"
      aria-selected={isSelected}
    >
      {/* Health indicator bar */}
      <motion.div
        className={classNames(
          "absolute left-0 top-0 bottom-0 w-1 rounded-l-xl",
          colors.bg
        )}
        initial={{ scaleY: 0 }}
        animate={{ scaleY: 1 }}
        transition={{ duration: 0.5, delay: index * 0.05 + 0.2 }}
        style={{ originY: 0 }}
      />

      {/* Content */}
      <div className="flex items-center gap-3 pl-2">
        {/* Icon */}
        <div className={classNames("flex-shrink-0 rounded-lg p-2", colors.bgLight)}>
          <MapPin className={classNames("h-4 w-4", colors.text)} />
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-200 truncate">
              {corridor.corridor}
            </span>
            {corridor.driftFlag && (
              <motion.span
                className="rounded bg-red-500/20 px-1.5 py-0.5 text-[9px] font-bold text-red-400"
                animate={
                  reducedMotion
                    ? {}
                    : { opacity: [1, 0.6, 1] }
                }
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                DRIFT
              </motion.span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-slate-500">
              {corridor.eventCount} events
            </span>
            <span className={classNames("text-xs font-mono", colors.text)}>
              {(corridor.driftScore * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Health badge */}
        <div className="flex-shrink-0 flex items-center gap-2">
          <div className={classNames("text-right", colors.text)}>
            <div className="text-sm font-bold">{corridor.healthScore}</div>
            <div className="text-[10px] text-slate-500">health</div>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-600" />
        </div>
      </div>

      {/* Health bar */}
      <div className="mt-2 pl-2">
        <div className="h-1 w-full rounded-full bg-slate-800 overflow-hidden">
          <motion.div
            className={classNames("h-full rounded-full", colors.bg)}
            initial={{ width: 0 }}
            animate={{ width: `${corridor.healthScore}%` }}
            transition={{
              duration: reducedMotion ? 0.1 : 0.8,
              delay: index * 0.05 + 0.3,
              ease: "easeOut",
            }}
          />
        </div>
      </div>
    </motion.button>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function CorridorOverviewAnimation({
  corridors,
  onCorridorSelect,
  selectedCorridor,
  className,
  compact = false,
  maxVisible = 6,
}: CorridorOverviewAnimationProps): JSX.Element {
  const reducedMotion = useReducedMotion();
  const [showAll, setShowAll] = useState(false);

  // Sort by drift flag (drifting first), then by health score
  const sortedCorridors = [...corridors].sort((a, b) => {
    if (a.driftFlag !== b.driftFlag) return a.driftFlag ? -1 : 1;
    return a.healthScore - b.healthScore;
  });

  const visibleCorridors = showAll
    ? sortedCorridors
    : sortedCorridors.slice(0, maxVisible);

  const hiddenCount = sortedCorridors.length - maxVisible;
  const driftingCount = corridors.filter((c) => c.driftFlag).length;
  const healthyCount = corridors.filter((c) => c.healthScore >= 80).length;

  // Container animation
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: reducedMotion ? 0 : 0.05,
      },
    },
  };

  return (
    <div
      className={classNames(
        "rounded-2xl border border-slate-800/70 bg-slate-900/50 overflow-hidden",
        className
      )}
      role="listbox"
      aria-label="Corridor overview"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-indigo-400" />
          <span className="text-sm font-semibold text-slate-200">
            Corridor Overview
          </span>
        </div>

        {/* Summary badges */}
        <div className="flex items-center gap-2">
          {driftingCount > 0 && (
            <motion.div
              className="flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 border border-red-500/30"
              animate={
                reducedMotion
                  ? {}
                  : { scale: [1, 1.05, 1] }
              }
              transition={{ duration: 2, repeat: Infinity }}
            >
              <AlertTriangle className="h-3 w-3 text-red-400" />
              <span className="text-[10px] font-bold text-red-400">
                {driftingCount} DRIFTING
              </span>
            </motion.div>
          )}
          <div className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 border border-emerald-500/30">
            <CheckCircle className="h-3 w-3 text-emerald-400" />
            <span className="text-[10px] font-bold text-emerald-400">
              {healthyCount} HEALTHY
            </span>
          </div>
        </div>
      </div>

      {/* Corridor grid */}
      <motion.div
        className={classNames(
          "p-3 space-y-2",
          compact ? "max-h-64 overflow-y-auto" : ""
        )}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <AnimatePresence mode="popLayout">
          {visibleCorridors.map((corridor, index) => (
            <CorridorCard
              key={corridor.corridor}
              corridor={corridor}
              isSelected={selectedCorridor === corridor.corridor}
              onClick={() => onCorridorSelect?.(corridor.corridor)}
              index={index}
              reducedMotion={reducedMotion}
            />
          ))}
        </AnimatePresence>

        {/* Show more button */}
        {hiddenCount > 0 && !showAll && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            onClick={() => setShowAll(true)}
            className={classNames(
              "w-full rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2",
              "text-xs text-slate-400 hover:bg-slate-700/50 hover:text-slate-200",
              "transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            )}
          >
            Show {hiddenCount} more corridors
          </motion.button>
        )}

        {/* Collapse button */}
        {showAll && hiddenCount > 0 && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => setShowAll(false)}
            className={classNames(
              "w-full rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2",
              "text-xs text-slate-400 hover:bg-slate-700/50 hover:text-slate-200",
              "transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            )}
          >
            Show less
          </motion.button>
        )}

        {/* Empty state */}
        {corridors.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-8"
          >
            <MapPin className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No corridors available</p>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export default CorridorOverviewAnimation;
