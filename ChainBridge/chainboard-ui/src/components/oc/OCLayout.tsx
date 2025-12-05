/**
 * OCLayout - Mission Control Style Layout for The OC
 *
 * Provides the main container structure with CIA ops-center aesthetic.
 * Dark mode compatible with clean, professional design.
 */

import type { OperatorLayoutMode } from "../../lib/layoutConfig";
import { APIHealthIndicator } from "../settlements/APIHealthIndicator";

import { KeyboardHintsFooter } from "./KeyboardHintsFooter";
import { SLAWidget } from "./SLAWidget";

interface OCLayoutProps {
  children: React.ReactNode;
  layoutModeToggle?: React.ReactNode; // Optional layout toggle control
  currentMode?: OperatorLayoutMode; // For display purposes
}

export function OCLayout({ children, layoutModeToggle }: OCLayoutProps) {
  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-slate-900/80 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">The OC — Operator Console</h1>
          <p className="text-sm text-slate-400">Action queue for at-risk shipments</p>
        </div>
        <div className="flex items-center gap-4">
          <SLAWidget />
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
