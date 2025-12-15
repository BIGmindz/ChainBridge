/**
 * OCLayout - Mission Control Style Layout for The OC
 *
 * Provides the main container structure with CIA ops-center aesthetic.
 * Dark mode compatible with clean, professional design.
 * ADHD-optimized with Focus Mode integration.
 */

import type { OperatorLayoutMode } from "../../lib/layoutConfig";
import { useFocusMode } from "../../core/focus/FocusModeContext";
import { classNames } from "../../utils/classNames";
import { APIHealthIndicator } from "../settlements/APIHealthIndicator";

import { FocusModeSwitcher } from "./FocusModeSwitcher";
import { KeyboardHintsFooter } from "./KeyboardHintsFooter";
import { SLAWidget } from "./SLAWidget";

interface OCLayoutProps {
  children: React.ReactNode;
  layoutModeToggle?: React.ReactNode; // Optional layout toggle control
  currentMode?: OperatorLayoutMode; // For display purposes
}

export function OCLayout({ children, layoutModeToggle }: OCLayoutProps) {
  const { mode, config } = useFocusMode();

  // Focus mode-based styles
  const focusModeStyles = {
    NEUROCALM: {
      bg: "bg-slate-950",
      headerBg: "bg-slate-900/60",
      border: "border-slate-800/50",
    },
    SIGNAL_INTENSITY: {
      bg: "bg-slate-950",
      headerBg: "bg-slate-900/80",
      border: "border-slate-800",
    },
    BATTLE: {
      bg: "bg-black",
      headerBg: "bg-slate-900/95",
      border: "border-red-900/30",
    },
  };

  const styles = focusModeStyles[mode];

  return (
    <div
      className={classNames(
        "h-screen flex flex-col overflow-hidden transition-colors duration-300",
        styles.bg
      )}
      style={{
        filter: `saturate(${config.saturation})`,
      }}
    >
      {/* Header — Calm, authoritative, breathing room */}
      <div
        className={classNames(
          "border-b px-6 py-5 flex items-center justify-between",
          "transition-colors duration-500 ease-out", // Slower, calmer transitions
          styles.headerBg,
          styles.border
        )}
      >
        <div className="space-y-1">
          <h1 className="text-xl font-semibold text-white tracking-tight">Operator Console</h1>
          <p className="text-sm text-slate-400/80">You have control. Take your time.</p>
        </div>
        <div className="flex items-center gap-5">
          <SLAWidget />
          <FocusModeSwitcher />
          {layoutModeToggle}
          <APIHealthIndicator />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col flex-1 overflow-hidden gap-4 p-6">
        {children}
      </div>

      {/* Keyboard Shortcuts Footer */}
      <KeyboardHintsFooter />
    </div>
  );
}
