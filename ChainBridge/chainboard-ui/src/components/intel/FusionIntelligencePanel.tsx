/**
 * Fusion Intelligence Panel v1
 *
 * The central intelligence hub for the Operator Console.
 * Aggregates multi-signal data, corridor stress, and system status.
 *
 * Features:
 * - Fusion Score display
 * - Corridor Stress Bars
 * - Intelligent Animations (reduced motion support)
 * - Focus Mode Integration (Neurocalm, Signal, Battle)
 * - WCAG AA Compliant
 *
 * @module components/intel/FusionIntelligencePanel
 */

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Brain,
  Zap,
  TrendingUp,
  ShieldCheck,
  AlertOctagon,
  CheckCircle2,
} from "lucide-react";
import { useFusionOverview, useCorridorStress } from "../../hooks/useFusion";
import { useFocusMode } from "../../core/focus/FocusModeContext";
import clsx from "clsx";

// =============================================================================
// COMPONENT
// =============================================================================

export const FusionIntelligencePanel: React.FC = () => {
  const { mode, reducedMotion } = useFocusMode();
  const { data: overview, isLoading: isOverviewLoading, error: overviewError } = useFusionOverview();
  const { data: stressData, isLoading: isStressLoading } = useCorridorStress();

  // ---------------------------------------------------------------------------
  // STYLES & VARIANTS
  // ---------------------------------------------------------------------------

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: reducedMotion ? 0 : 0.5,
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: reducedMotion ? 0 : 0.3 },
    },
  };

  // Dynamic colors based on Focus Mode
  const getStatusColor = (status: string) => {
    if (mode === "NEUROCALM") {
      switch (status) {
        case "critical": return "text-rose-400";
        case "warning": return "text-amber-400";
        case "optimal": return "text-emerald-400";
        default: return "text-slate-400";
      }
    }
    // BATTLE & SIGNAL_INTENSITY
    switch (status) {
      case "critical": return reducedMotion ? "text-red-500" : "text-red-500 animate-pulse";
      case "warning": return "text-yellow-500";
      case "optimal": return "text-green-500";
      default: return "text-gray-400";
    }
  };

  const getProgressBarColor = (score: number) => {
    if (mode === "NEUROCALM") {
      if (score > 80) return "bg-rose-300";
      if (score > 50) return "bg-amber-300";
      return "bg-emerald-300";
    }
    if (score > 80) return "bg-red-600";
    if (score > 50) return "bg-yellow-500";
    return "bg-green-500";
  };

  // ---------------------------------------------------------------------------
  // RENDER HELPERS
  // ---------------------------------------------------------------------------

  if (isOverviewLoading || isStressLoading) {
    return (
      <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800 animate-pulse h-64 flex items-center justify-center">
        <span className="text-slate-400">Initializing Fusion Core...</span>
      </div>
    );
  }

  if (overviewError) {
    return (
      <div className="p-6 rounded-xl bg-red-900/20 border border-red-800 text-red-400 flex items-center gap-3">
        <AlertOctagon className="w-6 h-6" />
        <span>Fusion System Offline: {overviewError.message}</span>
      </div>
    );
  }

  const fusionScore = overview?.fusion_score || 0;
  const status = overview?.status || "stable";

  return (
    <motion.section
      className={clsx(
        "rounded-xl border overflow-hidden backdrop-blur-sm transition-colors duration-500",
        mode === "NEUROCALM"
          ? "bg-slate-900/80 border-slate-800"
          : "bg-black/60 border-slate-700",
        mode === "BATTLE" && "border-red-900/50 bg-black/90"
      )}
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      aria-label="Fusion Intelligence Panel"
    >
      {/* HEADER */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {mode === "NEUROCALM" ? (
            <Brain className="w-5 h-5 text-emerald-400" />
          ) : mode === "BATTLE" ? (
            <Zap className="w-5 h-5 text-red-500" />
          ) : (
            <Activity className="w-5 h-5 text-blue-400" />
          )}
          <h2 className="font-semibold text-slate-100 tracking-wide">
            FUSION INTELLIGENCE
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx("text-sm font-mono", getStatusColor(status))}>
            {status.toUpperCase()}
          </span>
          {!reducedMotion && (
            <div className="w-2 h-2 rounded-full bg-current opacity-75 animate-ping" />
          )}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* LEFT: FUSION SCORE & SIGNALS */}
        <div className="space-y-6">
          {/* Score Display */}
          <motion.div variants={itemVariants} className="flex items-center gap-4">
            <div className="relative w-24 h-24 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="48"
                  cy="48"
                  r="40"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="transparent"
                  className="text-slate-800"
                />
                <circle
                  cx="48"
                  cy="48"
                  r="40"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="transparent"
                  strokeDasharray={251.2}
                  strokeDashoffset={251.2 - (251.2 * fusionScore) / 100}
                  className={clsx(
                    "transition-all duration-1000 ease-out",
                    getStatusColor(status)
                  )}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white">{fusionScore}</span>
                <span className="text-[10px] text-slate-400 uppercase">Score</span>
              </div>
            </div>

            <div className="flex-1">
              <h3 className="text-sm font-medium text-slate-300 mb-1">System Status</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {overview?.active_signals.length || 0} active signals detected across market, logistics, and risk vectors.
                {mode === "BATTLE" && " Immediate attention required."}
              </p>
            </div>
          </motion.div>

          {/* Active Signals List */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Active Signals
            </h4>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
              <AnimatePresence>
                {overview?.active_signals.map((signal) => (
                  <motion.div
                    key={signal.id}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className={clsx(
                      "p-3 rounded-lg border text-sm flex items-start gap-3",
                      mode === "NEUROCALM"
                        ? "bg-slate-800/50 border-slate-700"
                        : "bg-slate-900/80 border-slate-800"
                    )}
                  >
                    {signal.severity === "critical" ? (
                      <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="text-slate-200">{signal.message}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {signal.source}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(signal.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              {(!overview?.active_signals || overview.active_signals.length === 0) && (
                <div className="text-center py-4 text-slate-500 text-sm italic">
                  No active signals. Systems nominal.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT: CORRIDOR STRESS BARS */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-slate-400" />
              Corridor Stress
            </h3>
            <span className="text-xs text-slate-500">
              Global Index: {stressData?.global_stress_index || 0}
            </span>
          </div>

          <div className="space-y-3">
            {stressData?.corridors.map((corridor, index) => (
              <motion.div
                key={corridor.corridor_id}
                variants={itemVariants}
                custom={index}
                className="group"
              >
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">{corridor.name}</span>
                  <span className={clsx(
                    "font-mono",
                    corridor.stress_score > 80 ? "text-red-400" : "text-slate-400"
                  )}>
                    {corridor.stress_score}%
                  </span>
                </div>
                {/* Stress Bar Background */}
                <div
                  className="h-2 w-full bg-slate-800 rounded-full overflow-hidden"
                  role="progressbar"
                  aria-valuenow={corridor.stress_score}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`Stress level for ${corridor.name}`}
                >
                  {/* Stress Bar Fill */}
                  <motion.div
                    className={clsx("h-full rounded-full", getProgressBarColor(corridor.stress_score))}
                    initial={{ width: 0 }}
                    animate={{ width: `${corridor.stress_score}%` }}
                    transition={{ duration: reducedMotion ? 0 : 1, ease: "easeOut" }}
                  />
                </div>

                {/* Details (visible on hover or if critical) */}
                <div className="mt-1 flex justify-between opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  <span className="text-[10px] text-slate-500">
                    {corridor.active_shipments} active shipments
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {corridor.trend}
                  </span>
                </div>
              </motion.div>
            ))}

            {(!stressData?.corridors || stressData.corridors.length === 0) && (
              <div className="flex flex-col items-center justify-center py-8 text-slate-500">
                <CheckCircle2 className="w-8 h-8 mb-2 opacity-20" />
                <span className="text-sm">No corridor stress data available</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.section>
  );
};

export default FusionIntelligencePanel;
