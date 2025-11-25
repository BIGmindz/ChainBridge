import { useEffect, useState } from 'react';

import { SystemStatus } from '../components/debug/SystemStatus';
import GlobalOpsMap from '../components/GlobalOpsMap';

export default function OperatorConsolePage() {
  const [isCinematic, setIsCinematic] = useState(false);
  const [time, setTime] = useState(new Date());
  const [mounted, setMounted] = useState(false);

  // Clock & Hydration Timer
  useEffect(() => {
    setMounted(true);
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (!mounted)
    return (
      <div className="bg-slate-950 h-screen w-full text-white flex items-center justify-center">
        Initializing Uplink...
      </div>
    );

  return (
    <div className="relative w-full h-screen bg-slate-950 overflow-hidden font-sans text-slate-200 selection:bg-emerald-500/30">
      {/* LAYER 0: THE MAP */}
      <div className="absolute inset-0 z-0 layer-map">
        <GlobalOpsMap mapStyle="dark" />
      </div>

      {/* LAYER 1: CINEMATIC TOGGLE */}
      <div className="absolute top-4 right-4 z-50">
        <button
          onClick={() => setIsCinematic(!isCinematic)}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-full border backdrop-blur-md transition-all duration-300 shadow-lg cursor-pointer group
            ${
              isCinematic
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/30'
                : 'bg-slate-900/80 border-slate-700/50 text-slate-300 hover:text-white hover:bg-slate-800'
            }
          `}
        >
          {/* SVG Eye Icon */}
          <svg
            className="w-4 h-4 group-hover:scale-110 transition-transform"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            {isCinematic ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
              />
            )}
          </svg>
          <span className="text-xs font-bold tracking-wider">
            {isCinematic ? 'SHOW HUD' : 'HIDE UI'}
          </span>
        </button>
      </div>

      {/* LAYER 2: THE UI OVERLAYS */}
      <div
        className={`
          absolute inset-0 z-10 pointer-events-none transition-all duration-500 ease-in-out layer-ui
          ${isCinematic ? 'opacity-0 translate-y-4' : 'opacity-100 translate-y-0'}
        `}
      >
        {/* HEADER BAR - Now with LIVE DATA TRUST INDICATOR */}
        <div className="absolute top-0 left-0 w-full p-4 layer-interactive">
          <div className="flex items-center gap-4">
            {/* Main Title Badge */}
            <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/50 flex items-center gap-4 px-6 py-3 rounded-xl shadow-2xl">
              <h1 className="text-xl font-bold tracking-tight text-white">OPERATOR CONSOLE</h1>

              {/* The "Data Trust" Divider */}
              <div className="h-4 w-px bg-slate-700" />

              {/* Live Pulse & Clock */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
                  </span>
                  <span className="text-xs font-bold text-red-400 tracking-widest">LIVE FEED</span>
                </div>
                <div className="text-xs font-mono text-slate-400 tabular-nums">
                  {time.toLocaleTimeString()} UTC
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* LEFT SIDEBAR - Shipment List with Stats */}
        <div className="absolute top-24 left-4 bottom-8 w-96 flex flex-col gap-4 layer-interactive">
          {/* KPI STRIP - With HOVER DRILL-DOWN on RISK */}
          <div className="grid grid-cols-3 gap-2">
            {/* Metric 1: Total */}
            <div className="bg-slate-900/80 border border-slate-700/50 p-3 rounded-lg text-center backdrop-blur-sm">
              <div className="text-[10px] text-slate-500 uppercase font-bold">Total</div>
              <div className="text-xl font-mono text-white">12</div>
            </div>

            {/* Metric 2: Critical (Standard) */}
            <div className="bg-slate-900/80 border border-red-900/30 p-3 rounded-lg text-center backdrop-blur-sm">
              <div className="text-[10px] text-red-500 uppercase font-bold">Critical</div>
              <div className="text-xl font-mono text-red-400">3</div>
            </div>

            {/* Metric 3: RISK SCORE (Interactive Drill-Down) */}
            <div className="relative group bg-slate-900/80 border border-amber-900/30 p-3 rounded-lg text-center backdrop-blur-sm cursor-help transition-colors hover:bg-slate-800 hover:border-amber-500/50">
              <div className="text-[10px] text-amber-500 uppercase font-bold flex justify-center items-center gap-1">
                Risk Score
                <svg
                  className="w-3 h-3 opacity-50 group-hover:opacity-100"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="text-xl font-mono text-amber-400">7.2</div>

              {/* THE DRILL-DOWN POPOVER */}
              <div className="absolute left-full top-0 ml-3 w-48 bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50">
                <div className="text-xs font-bold text-slate-200 mb-2 text-left">Risk Factors</div>
                <div className="space-y-2 text-left">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-slate-400">Red Sea Conflict</span>
                    <span className="text-red-400 font-mono">+4.1</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-slate-400">Port Congestion</span>
                    <span className="text-amber-400 font-mono">+2.0</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-slate-400">Weather (Pacific)</span>
                    <span className="text-emerald-400 font-mono">+1.1</span>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-slate-800 text-[10px] text-slate-500 text-left">
                  Last updated: 2s ago
                </div>
              </div>
            </div>
          </div>

          {/* LIST */}
          <div className="flex-1 bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-xl overflow-hidden flex flex-col shadow-2xl">
            <div className="p-3 border-b border-slate-700/50 bg-slate-800/30 flex justify-between items-center">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Active Shipments
              </h3>
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/30 hover:border-emerald-500/50 cursor-pointer transition-all hover:bg-slate-800 group"
                >
                  <div className="flex justify-between mb-1">
                    <span className="font-mono text-xs text-white group-hover:text-emerald-400 transition-colors">
                      SHP-2025-00{i}
                    </span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${i === 2 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}
                    >
                      {i === 2 ? 'CRITICAL' : 'ON TIME'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="text-xs text-slate-500">CN-SHANGHAI → US-LAX</div>
                    <div className="text-[10px] text-slate-600 font-mono">ETA: 4d</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT PANEL - Telemetry */}
        <div className="absolute top-24 right-4 bottom-8 w-80 bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-xl p-4 layer-interactive shadow-2xl">
          <div className="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-widest mb-1">
                Selected Link
              </div>
              <h2 className="text-lg font-bold text-white">SHP-2025-002</h2>
            </div>
            <div className="h-8 w-8 rounded bg-red-500/20 flex items-center justify-center border border-red-500/50 text-red-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
          </div>

          <div className="space-y-4">
            <div className="p-3 bg-black/40 rounded-lg border border-slate-800">
              <div className="text-xs text-slate-400 mb-1 flex justify-between">
                <span>Signal Strength</span>
                <span className="text-emerald-500">98%</span>
              </div>
              <div className="w-full bg-slate-800 h-1 rounded-full mt-2 overflow-hidden">
                <div className="bg-emerald-500 h-full w-[98%] shadow-[0_0_10px_#10b981]" />
              </div>
            </div>

            <div className="p-4 bg-slate-800/30 rounded-lg border border-slate-700/50">
              <div className="text-xs text-slate-500 uppercase mb-2">Live Telemetry</div>
              <div className="font-mono text-sm text-emerald-400 space-y-1">
                <p>&gt; LATITUDE: 34.0522 N</p>
                <p>&gt; LONGITUDE: 118.2437 W</p>
                <p>&gt; HEADING: 084° EAST</p>
                <p>&gt; SPEED: 22 KNOTS</p>
              </div>
            </div>
          </div>

          <div className="mt-auto pt-6">
            <button className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold text-sm transition-all shadow-lg shadow-indigo-500/20 border border-indigo-400/20">
              ESTABLISH COMMS
            </button>
          </div>
        </div>
      </div>
      <SystemStatus />
    </div>
  );
}
