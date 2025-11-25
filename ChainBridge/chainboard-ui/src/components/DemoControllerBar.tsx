/**
 * DemoControllerBar Component
 *
 * Fixed top-right control bar for starting/navigating demo walkthroughs.
 */

import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useDemo } from "../core/demo/DemoContext";
import { DEMO_SCENARIOS } from "../core/demo/registry";

export const DemoControllerBar: React.FC = () => {
  const { state, startScenario, stop, next, prev } = useDemo();
  const location = useLocation();
  const navigate = useNavigate();

  const active = state.isRunning && state.activeScenario && state.currentStep;

  // Only render on main console pages
  const isConsoleRoute =
    location.pathname === "/" ||
    location.pathname.startsWith("/shipments") ||
    location.pathname.startsWith("/exceptions");

  if (!isConsoleRoute) return null;

  const scenario = state.activeScenario ?? DEMO_SCENARIOS[0];
  const step = state.currentStep;

  const handleStart = () => {
    startScenario(scenario.id);
    // Navigate to first step route
    if (scenario.steps[0]?.targetRoute) {
      navigate(scenario.steps[0].targetRoute);
    }
  };

  const handleNext = () => {
    if (!step || !scenario) return;
    next();
    const nextStep =
      scenario.steps[Math.min(state.currentIndex + 1, scenario.steps.length - 1)];
    if (nextStep?.targetRoute) {
      navigate(nextStep.targetRoute);
    }
  };

  const handlePrev = () => {
    if (!scenario) return;
    prev();
    const prevStep = scenario.steps[Math.max(state.currentIndex - 1, 0)];
    if (prevStep?.targetRoute) {
      navigate(prevStep.targetRoute);
    }
  };

  return (
    <div className="pointer-events-auto fixed right-4 top-4 z-40 flex items-center gap-2 rounded-full bg-slate-900/90 px-3 py-1.5 text-xs text-slate-50 shadow-lg backdrop-blur">
      {!state.isRunning && (
        <>
          <span className="hidden sm:inline text-[10px] uppercase tracking-wide text-slate-300">
            Demo mode
          </span>
          <button
            type="button"
            className="rounded-full bg-emerald-500 px-3 py-1 text-[11px] font-semibold hover:bg-emerald-400 transition-colors"
            onClick={handleStart}
          >
            Start Investor Demo
          </button>
        </>
      )}

      {active && (
        <>
          <span className="hidden md:inline text-[10px] uppercase tracking-wide text-slate-300">
            Demo: {scenario.name}
          </span>
          <span className="text-[11px] font-medium">
            {state.currentIndex + 1}/{scenario.steps.length}
          </span>
          <button
            type="button"
            className="rounded-full border border-slate-500 px-2 py-0.5 text-[10px] hover:bg-slate-800 transition-colors disabled:opacity-50"
            onClick={handlePrev}
            disabled={state.currentIndex === 0}
          >
            Prev
          </button>
          <button
            type="button"
            className="rounded-full border border-slate-500 px-2 py-0.5 text-[10px] hover:bg-slate-800 transition-colors disabled:opacity-50"
            onClick={handleNext}
            disabled={state.currentIndex === scenario.steps.length - 1}
          >
            Next
          </button>
          <button
            type="button"
            className="rounded-full border border-rose-500 px-2 py-0.5 text-[10px] text-rose-200 hover:bg-rose-600 transition-colors"
            onClick={stop}
          >
            Exit
          </button>
        </>
      )}
    </div>
  );
};
