/**
 * DemoSidebar Component
 *
 * Floating sidebar with current step instructions and context.
 */

import React from "react";

import { useDemo } from "../core/demo/DemoContext";

export const DemoSidebar: React.FC = () => {
  const { state } = useDemo();
  const { isRunning, activeScenario, currentStep, currentIndex } = state;

  if (!isRunning || !activeScenario || !currentStep) return null;

  return (
    <aside className="pointer-events-auto fixed left-4 bottom-4 z-40 w-80 max-w-[80vw] rounded-xl border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        Demo: {activeScenario.name}
      </div>
      <h2 className="mb-2 text-sm font-semibold text-slate-900">
        {currentStep.title}
      </h2>
      <p className="mb-3 text-xs text-slate-600 leading-relaxed">
        {currentStep.description}
      </p>
      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <span>
          Step {currentIndex + 1} of {activeScenario.steps.length}
        </span>
        <span className="text-emerald-600 font-medium">
          {currentIndex === activeScenario.steps.length - 1 ? "Final Step" : "In Progress"}
        </span>
      </div>
    </aside>
  );
};
