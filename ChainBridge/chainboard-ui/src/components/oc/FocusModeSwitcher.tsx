/**
 * FocusModeSwitcher - UI Control for ADHD-Optimized Focus Modes
 *
 * Keyboard accessible (Cmd/Ctrl+Shift+F to cycle).
 * WCAG AA compliant with clear visual feedback.
 *
 * @module components/oc/FocusModeSwitcher
 */

import { motion, AnimatePresence } from "framer-motion";
import { Brain, Activity, Zap, ChevronDown, Check, Eye } from "lucide-react";
import { useState, useEffect, useRef, useCallback } from "react";

import {
  useFocusMode,
  FOCUS_MODE_CONFIGS,
  type FocusModeType,
} from "../../core/focus/FocusModeContext";
import { classNames } from "../../utils/classNames";

// =============================================================================
// TYPES
// =============================================================================

interface FocusModeSwitcherProps {
  className?: string;
  compact?: boolean;
  showReducedMotionToggle?: boolean;
}

// =============================================================================
// ICONS
// =============================================================================

const ModeIcons: Record<FocusModeType, typeof Brain> = {
  NEUROCALM: Brain,
  SIGNAL_INTENSITY: Activity,
  BATTLE: Zap,
};

const ModeColors: Record<FocusModeType, { bg: string; text: string; border: string; glow: string }> = {
  NEUROCALM: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/30",
    glow: "shadow-blue-500/20",
  },
  SIGNAL_INTENSITY: {
    bg: "bg-indigo-500/10",
    text: "text-indigo-400",
    border: "border-indigo-500/30",
    glow: "shadow-indigo-500/20",
  },
  BATTLE: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
    glow: "shadow-red-500/20",
  },
};

// =============================================================================
// COMPONENT
// =============================================================================

export function FocusModeSwitcher({
  className,
  compact = false,
  showReducedMotionToggle = true,
}: FocusModeSwitcherProps): JSX.Element {
  const {
    mode,
    config,
    reducedMotion,
    availableModes,
    setMode,
    cycleMode,
    toggleReducedMotion,
  } = useFocusMode();

  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const CurrentIcon = ModeIcons[mode];
  const colors = ModeColors[mode];

  // Keyboard shortcut handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Cmd/Ctrl + Shift + F to cycle modes
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "F") {
        e.preventDefault();
        cycleMode();
      }
      // Escape to close dropdown
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    },
    [cycleMode, isOpen]
  );

  // Register keyboard listener
  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Compact mode - just the icon button
  if (compact) {
    return (
      <button
        onClick={cycleMode}
        className={classNames(
          "flex items-center justify-center rounded-lg p-2 transition-all",
          "border",
          colors.bg,
          colors.border,
          "hover:shadow-lg",
          colors.glow,
          className
        )}
        aria-label={`Current mode: ${config.label}. Press to cycle modes.`}
        title={`${config.label} - Press Cmd+Shift+F to cycle`}
      >
        <CurrentIcon className={classNames("h-5 w-5", colors.text)} />
      </button>
    );
  }

  return (
    <div ref={containerRef} className={classNames("relative", className)}>
      {/* Main button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={classNames(
          "flex items-center gap-2 rounded-lg px-3 py-2 transition-all",
          "border",
          colors.bg,
          colors.border,
          isOpen && "ring-2 ring-indigo-500/50",
          "hover:shadow-lg",
          colors.glow
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={`Focus mode: ${config.label}`}
      >
        <div className={classNames("flex items-center gap-2", colors.text)}>
          <CurrentIcon className="h-4 w-4" />
          <span className="text-sm font-medium">{config.label}</span>
        </div>
        <ChevronDown
          className={classNames(
            "h-4 w-4 text-slate-500 transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: reducedMotion ? 0 : 0.15 }}
            className={classNames(
              "absolute right-0 z-50 mt-2 w-72 rounded-xl overflow-hidden",
              "border border-slate-700/50 bg-slate-900/95 shadow-2xl backdrop-blur-md"
            )}
            role="listbox"
            aria-label="Select focus mode"
          >
            {/* Mode options */}
            <div className="p-2">
              {availableModes.map((modeOption) => {
                const ModeIcon = ModeIcons[modeOption];
                const modeConfig = FOCUS_MODE_CONFIGS[modeOption];
                const modeColors = ModeColors[modeOption];
                const isSelected = mode === modeOption;

                return (
                  <button
                    key={modeOption}
                    onClick={() => {
                      setMode(modeOption);
                      setIsOpen(false);
                    }}
                    className={classNames(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
                      isSelected
                        ? `${modeColors.bg} ${modeColors.border} border`
                        : "hover:bg-slate-800/70 border border-transparent"
                    )}
                    role="option"
                    aria-selected={isSelected}
                  >
                    {/* Icon */}
                    <div
                      className={classNames(
                        "flex h-9 w-9 items-center justify-center rounded-lg",
                        modeColors.bg
                      )}
                    >
                      <ModeIcon className={classNames("h-5 w-5", modeColors.text)} />
                    </div>

                    {/* Label and description */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={classNames(
                            "text-sm font-medium",
                            isSelected ? modeColors.text : "text-slate-200"
                          )}
                        >
                          {modeConfig.label}
                        </span>
                        {isSelected && (
                          <Check className={classNames("h-3.5 w-3.5", modeColors.text)} />
                        )}
                      </div>
                      <p className="text-xs text-slate-500 truncate">
                        {modeConfig.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Reduced motion toggle */}
            {showReducedMotionToggle && (
              <>
                <div className="border-t border-slate-700/50" />
                <div className="p-2">
                  <button
                    onClick={toggleReducedMotion}
                    className={classNames(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
                      "hover:bg-slate-800/70"
                    )}
                    role="switch"
                    aria-checked={reducedMotion}
                  >
                    <div
                      className={classNames(
                        "flex h-9 w-9 items-center justify-center rounded-lg",
                        reducedMotion ? "bg-emerald-500/10" : "bg-slate-800"
                      )}
                    >
                      <Eye
                        className={classNames(
                          "h-5 w-5",
                          reducedMotion ? "text-emerald-400" : "text-slate-500"
                        )}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-200">
                          Reduced Motion
                        </span>
                        {/* Toggle indicator */}
                        <div
                          className={classNames(
                            "w-8 h-4 rounded-full transition-colors",
                            reducedMotion ? "bg-emerald-500" : "bg-slate-700"
                          )}
                        >
                          <motion.div
                            className="w-3 h-3 rounded-full bg-white mt-0.5"
                            animate={{ x: reducedMotion ? 17 : 2 }}
                            transition={{ type: "spring", stiffness: 500, damping: 30 }}
                          />
                        </div>
                      </div>
                      <p className="text-xs text-slate-500">
                        Minimize animations for accessibility
                      </p>
                    </div>
                  </button>
                </div>
              </>
            )}

            {/* Keyboard hint */}
            <div className="border-t border-slate-700/50 px-3 py-2 bg-slate-800/30">
              <p className="text-[10px] text-slate-500 text-center">
                Press <kbd className="px-1 py-0.5 rounded bg-slate-700 text-slate-400 font-mono">⌘⇧F</kbd> to cycle modes
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default FocusModeSwitcher;
