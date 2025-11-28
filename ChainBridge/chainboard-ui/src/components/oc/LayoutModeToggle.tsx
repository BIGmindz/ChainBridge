/**
 * LayoutModeToggle
 *
 * 3-way segmented control for switching between layout modes.
 * - FULL_INTEL: Balanced intelligence cockpit
 * - HYBRID: Operator triage mode
 * - CASH_OPS: Payment operations focus
 */

import type { OperatorLayoutMode } from "../../lib/layoutConfig";

interface LayoutModeToggleProps {
  currentMode: OperatorLayoutMode;
  onModeChange: (mode: OperatorLayoutMode) => void;
}

const MODE_CONFIG: Record<OperatorLayoutMode, { label: string; icon: string; description: string }> = {
  FULL_INTEL: {
    label: "Full Intel",
    icon: "🎯",
    description: "Balanced settlement intelligence",
  },
  HYBRID: {
    label: "Hybrid",
    icon: "⚡",
    description: "Operator triage mode",
  },
  CASH_OPS: {
    label: "Cash Ops",
    icon: "💰",
    description: "Payment operations focus",
  },
};

export function LayoutModeToggle({ currentMode, onModeChange }: LayoutModeToggleProps) {
  const modes: OperatorLayoutMode[] = ["FULL_INTEL", "HYBRID", "CASH_OPS"];

  return (
    <div className="flex items-center gap-1 bg-slate-800/50 rounded-md p-1 border border-slate-700">
      {modes.map((mode) => {
        const config = MODE_CONFIG[mode];
        const isActive = currentMode === mode;

        return (
          <button
            key={mode}
            onClick={() => onModeChange(mode)}
            className={`
              px-3 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5
              ${
                isActive
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/50"
                  : "text-slate-400 hover:text-slate-300 hover:bg-slate-700/50"
              }
            `}
            aria-pressed={isActive}
            title={config.description}
          >
            <span>{config.icon}</span>
            <span>{config.label}</span>
          </button>
        );
      })}
    </div>
  );
}
