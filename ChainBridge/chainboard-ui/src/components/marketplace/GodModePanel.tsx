/**
 * GodModePanel - Hidden Demo Control Panel
 *
 * Activation: Cmd + Shift + . (hidden hotkey)
 * Appears as a floating semi-transparent HUD in bottom-right
 *
 * Controls:
 * - [Reset World] - Restore all listings to initial state
 * - [📉 Crash Market] - Trigger critical breach event
 * - [⏩ FF 1 Hour] - Fast-forward auction by 1 hour
 */

import { AnimatePresence, motion } from "framer-motion";
import { RotateCcw, TrendingDown, X, Zap } from "lucide-react";
import { memo, useEffect, useState } from "react";

import { demoReset, demoTriggerBreach, demoWarpTime, type DemoBreach, type DemoWarpTime } from "../../api/marketplace";
import { classNames } from "../../utils/classNames";

interface GodModePanelProps {
  listingId?: string;
  onResetComplete?: () => void;
  onBreachTriggered?: () => void;
  onTimeWarped?: (hours: number) => void;
}

function GodModePanelComponent({
  listingId,
  onResetComplete,
  onBreachTriggered,
  onTimeWarped,
}: GodModePanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Hidden hotkey detection: Cmd + Shift + .
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // On Mac: Cmd (metaKey), On Windows/Linux: Ctrl (ctrlKey)
      const isMeta = e.metaKey || e.ctrlKey;
      const isShift = e.shiftKey;
      const isDot = e.key === "." || e.code === "Period";

      if (isMeta && isShift && isDot) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const showFeedback = (message: string, duration = 2000) => {
    setFeedback(message);
    setTimeout(() => setFeedback(null), duration);
  };

  const handleReset = async () => {
    setIsLoading(true);
    try {
      await demoReset();
      showFeedback("✓ World reset to initial state");
      onResetComplete?.();
    } catch {
      showFeedback("✗ Reset failed", 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCrashMarket = async () => {
    setIsLoading(true);
    try {
      const breach: DemoBreach = {
        listingId: listingId || "",
        breachType: "TEMPERATURE",
        severity: "CRITICAL",
      };
      await demoTriggerBreach(breach);
      showFeedback("📉 Market crashed: CRITICAL breach detected");
      onBreachTriggered?.();
    } catch {
      showFeedback("✗ Breach trigger failed", 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWarpTime = async (hours: number) => {
    setIsLoading(true);
    try {
      const warp: DemoWarpTime = {
        listingId: listingId || "",
        hoursToAdvance: hours,
      };
      await demoWarpTime(warp);
      showFeedback(`⏩ Time warped +${hours}h`);
      onTimeWarped?.(hours);
    } catch {
      showFeedback("✗ Time warp failed", 3000);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ duration: 0.2 }}
          className="fixed bottom-6 right-6 z-50 max-w-sm"
        >
          {/* Panel Container */}
          <div className="backdrop-blur-md bg-slate-950/80 border-2 border-violet-500/50 rounded-lg p-6 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-violet-400 rounded-full animate-pulse" />
                <h3 className="text-sm font-bold text-violet-400 tracking-widest">
                  GOD MODE
                </h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                title="Close God Mode panel"
                className="text-slate-500 hover:text-slate-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Controls Grid */}
            <div className="space-y-3 mb-4">
              {/* Reset World */}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleReset}
                disabled={isLoading}
                className={classNames(
                  "w-full px-4 py-2 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-all",
                  isLoading
                    ? "bg-slate-800/50 text-slate-600 cursor-wait"
                    : "bg-gradient-to-r from-slate-700 to-slate-600 hover:from-slate-600 hover:to-slate-500 text-slate-100"
                )}
              >
                <RotateCcw className="w-4 h-4" />
                Reset World
              </motion.button>

              {/* Crash Market */}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleCrashMarket}
                disabled={isLoading}
                className={classNames(
                  "w-full px-4 py-2 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-all",
                  isLoading
                    ? "bg-slate-800/50 text-slate-600 cursor-wait"
                    : "bg-gradient-to-r from-red-700/80 to-orange-700/80 hover:from-red-600 hover:to-orange-600 text-red-50 border border-red-500/30"
                )}
              >
                <TrendingDown className="w-4 h-4" />
                📉 Crash Market
              </motion.button>

              {/* Time Warp Buttons */}
              <div className="grid grid-cols-2 gap-2">
                {[1, 6].map((hours) => (
                  <motion.button
                    key={hours}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleWarpTime(hours)}
                    disabled={isLoading}
                    className={classNames(
                      "px-4 py-2 rounded-lg text-sm font-semibold flex items-center justify-center gap-1 transition-all",
                      isLoading
                        ? "bg-slate-800/50 text-slate-600 cursor-wait"
                        : "bg-gradient-to-r from-cyan-700 to-blue-700 hover:from-cyan-600 hover:to-blue-600 text-cyan-50"
                    )}
                  >
                    <Zap className="w-3 h-3" />
                    FF +{hours}h
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Feedback Message */}
            <AnimatePresence>
              {feedback && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="p-3 bg-slate-900/80 rounded-lg border border-slate-700/50 text-center text-xs text-slate-300"
                >
                  {feedback}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Instructions */}
            <div className="mt-4 pt-4 border-t border-slate-700/50 text-xs text-slate-500 space-y-1">
              <p>🎯 <span className="text-slate-400">Demo-only controls</span></p>
              <p>🔒 <span className="text-slate-400">Hidden hotkey: Cmd+Shift+.</span></p>
              <p>⚡ <span className="text-slate-400">Production data unaffected</span></p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Floating Indicator (When Closed) */}
      {!isOpen && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          whileHover={{ scale: 1.1 }}
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 w-10 h-10 rounded-full bg-gradient-to-br from-violet-600/20 to-violet-500/20 border border-violet-500/30 backdrop-blur-sm flex items-center justify-center text-violet-400 hover:text-violet-300 transition-all opacity-30 hover:opacity-100 cursor-help"
          title="God Mode (Cmd+Shift+.)"
        >
          <Zap className="w-5 h-5" />
        </motion.button>
      )}
    </AnimatePresence>
  );
}

export const GodModePanel = memo(GodModePanelComponent);
