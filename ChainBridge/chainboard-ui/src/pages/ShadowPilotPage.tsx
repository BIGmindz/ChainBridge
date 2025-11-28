/**
 * Shadow Pilot Cockpit Page
 *
 * CHAINBRIDGE PAC FORMAT (Enterprise-Grade)
 * - Objective: Force-render GlobalOpsMap as immersive background layer
 * - Architecture: Z-index layered stack (Map → Effects → HUD)
 * - Type-safe: Strict TypeScript compliance
 * - Visual Fidelity: Dark mode command center aesthetic
 *
 * @author Sonny, Senior Frontend Engineer
 */

import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

import GlobalOpsMap from '../components/GlobalOpsMap';

export default function ShadowPilotPage(): JSX.Element {
  // State to handle entrance animations (800ms boot sequence)
  const [isSystemReady, setIsSystemReady] = useState<boolean>(false);

  useEffect(() => {
    // Simulate system boot sequence for cinematic effect
    const timer = setTimeout(() => setIsSystemReady(true), 800);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="relative w-full h-screen bg-[#020617] overflow-hidden flex flex-col">
      {/* ---------------------------------------------------------------------------
          LAYER 0: THE "GOD VIEW" MAP (Forced Render - No Conditional Blocker)
          Type-safe props: onVesselClick, selectedVesselId, flyToVessel, mapStyle
          This bypasses any "Select Run" empty state logic.
         --------------------------------------------------------------------------- */}
      <div className="absolute inset-0 z-0">
        <GlobalOpsMap
          onVesselClick={() => {
            // Future: Could trigger vessel detail modal
          }}
          selectedVesselId={null}
          flyToVessel={null}
          mapStyle="dark"
        />
      </div>

      {/* ---------------------------------------------------------------------------
          LAYER 1: CINEMATIC VIGNETTE & EFFECTS
          Command center aesthetic with vignette, noise grain, and scanlines
         --------------------------------------------------------------------------- */}
      <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-[#020617]/90 via-transparent to-[#020617]/40" />
      <div className="absolute inset-0 z-10 pointer-events-none opacity-[0.05] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />

      {/* CRT Scanline Effect */}
      <div
        className="absolute inset-0 z-20 pointer-events-none"
        style={{
          background:
            'linear-gradient(rgba(18,16,16,0) 50%, rgba(0,0,0,0.25) 50%), linear-gradient(90deg, rgba(255,0,0,0.06), rgba(0,255,0,0.02), rgba(0,0,255,0.06))',
          backgroundSize: '100% 2px, 3px 100%',
        }}
      />

      {/* ---------------------------------------------------------------------------
          LAYER 2: GLASS-MORPHISM HUD (Floating UI)
          Interactive elements with backdrop blur that float above the map
         --------------------------------------------------------------------------- */}
      <div className="relative z-30 flex flex-col h-full p-6 pointer-events-none">
        {/* Top Bar HUD */}
        <header className="flex items-center justify-between pointer-events-auto">
          <div className="backdrop-blur-md bg-slate-900/40 border border-slate-700/30 p-3 rounded-lg flex items-center gap-4">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"
                  style={{ boxShadow: '0 0 10px #10b981' }}
                />
                SHADOW PILOT
              </h1>
              <p className="text-xs text-emerald-400 font-mono uppercase tracking-widest">
                Live Surveillance // Node: US-EAST-1
              </p>
            </div>
          </div>

          {/* Run Selector (Visual Only - No Blocking Logic) */}
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-700/50 rounded-lg p-1">
            <select
              className="bg-transparent text-white text-sm px-4 py-2 outline-none font-mono"
              aria-label="Simulation selector"
            >
              <option>SIMULATION: ACME Logistics</option>
              <option>SIMULATION: Global Freight Corp</option>
              <option>SIMULATION: Stark Industries</option>
            </select>
          </div>
        </header>

        {/* Spacer to push stats to bottom */}
        <div className="flex-1" />

        {/* Bottom HUD Stats - Motion.div for entrance animation */}
        <div className="w-full pointer-events-auto">
          <div className="grid grid-cols-4 gap-4 w-full max-w-5xl mx-auto">
            {/* Stat Card 1: Active Vessels */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: isSystemReady ? 1 : 0, y: isSystemReady ? 0 : 20 }}
              transition={{ delay: 0.2 }}
              className="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 p-4 rounded-xl group hover:border-emerald-500/50 transition-colors cursor-pointer"
            >
              <div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1 font-mono">
                Active Vessels
              </div>
              <div className="text-2xl font-bold text-white font-mono group-hover:text-emerald-400 transition-colors">
                54 <span className="text-xs text-emerald-500 ml-1">▲ 2</span>
              </div>
            </motion.div>

            {/* Stat Card 2: Critical Risks */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: isSystemReady ? 1 : 0, y: isSystemReady ? 0 : 20 }}
              transition={{ delay: 0.3 }}
              className="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 p-4 rounded-xl group hover:border-amber-500/50 transition-colors cursor-pointer"
            >
              <div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1 font-mono">
                Critical Risks
              </div>
              <div className="text-2xl font-bold text-white font-mono group-hover:text-amber-400 transition-colors">
                03 <span className="text-xs text-amber-500 ml-1">!</span>
              </div>
            </motion.div>

            {/* Stat Card 3: Est. Yield Impact */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: isSystemReady ? 1 : 0, y: isSystemReady ? 0 : 20 }}
              transition={{ delay: 0.4 }}
              className="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 p-4 rounded-xl"
            >
              <div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1 font-mono">
                Est. Yield Impact
              </div>
              <div className="text-2xl font-bold text-white font-mono">+12.4%</div>
            </motion.div>

            {/* Stat Card 4: System Latency */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: isSystemReady ? 1 : 0, y: isSystemReady ? 0 : 20 }}
              transition={{ delay: 0.5 }}
              className="bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 p-4 rounded-xl"
            >
              <div className="text-slate-400 text-[10px] uppercase tracking-wider mb-1 font-mono">
                System Latency
              </div>
              <div className="text-2xl font-bold text-white font-mono">24ms</div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
