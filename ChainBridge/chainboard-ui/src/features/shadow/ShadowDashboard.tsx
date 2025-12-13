/**
 * Shadow Mode Dashboard Component
 *
 * Main dashboard for visualizing shadow mode analytics:
 * - Summary statistics (events, deltas, percentiles)
 * - Per-corridor breakdown
 * - Recent event stream
 *
 * ⚠️ REALITY GUARDRAIL: Backend endpoints not yet available.
 * This component is scaffolding only - API calls will fail gracefully
 * with clear messaging until Cody adds shadow REST endpoints.
 *
 * TODO: Remove error states once backend is ready.
 *
 * @module features/shadow/ShadowDashboard
 */

import { useState, useEffect } from "react";

import type { ShadowStats, ShadowEvent, CorridorStats } from "../../api/shadow";
import {
  fetchShadowStats,
  fetchShadowEvents,
  fetchCorridorStats,
} from "../../api/shadow";

import ShadowCorridorTable from "./ShadowCorridorTable";
import ShadowEventsTable from "./ShadowEventsTable";
import ShadowStatsCard from "./ShadowStatsCard";

export default function ShadowDashboard(): JSX.Element {
  // Stats state
  const [stats, setStats] = useState<ShadowStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Events state
  const [events, setEvents] = useState<ShadowEvent[] | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

  // Corridors state
  const [corridors, setCorridors] = useState<CorridorStats[] | null>(null);
  const [corridorsLoading, setCorridorsLoading] = useState(false);
  const [corridorsError, setCorridorsError] = useState<string | null>(null);

  /**
   * Load shadow statistics.
   * TODO: Remove try/catch once backend endpoints exist.
   */
  const loadStats = async () => {
    try {
      setStatsLoading(true);
      setStatsError(null);
      const data = await fetchShadowStats(24);
      setStats(data);
    } catch (error) {
      console.warn("Shadow stats not available:", error);
      setStatsError(
        error instanceof Error
          ? error.message
          : "Shadow stats endpoint not yet implemented"
      );
    } finally {
      setStatsLoading(false);
    }
  };

  /**
   * Load shadow events.
   * TODO: Remove try/catch once backend endpoints exist.
   */
  const loadEvents = async () => {
    try {
      setEventsLoading(true);
      setEventsError(null);
      const data = await fetchShadowEvents(50);
      setEvents(data);
    } catch (error) {
      console.warn("Shadow events not available:", error);
      setEventsError(
        error instanceof Error
          ? error.message
          : "Shadow events endpoint not yet implemented"
      );
    } finally {
      setEventsLoading(false);
    }
  };

  /**
   * Load corridor statistics.
   * TODO: Remove try/catch once backend endpoints exist.
   */
  const loadCorridors = async () => {
    try {
      setCorridorsLoading(true);
      setCorridorsError(null);
      const data = await fetchCorridorStats(24);
      setCorridors(data);
    } catch (error) {
      console.warn("Shadow corridor stats not available:", error);
      setCorridorsError(
        error instanceof Error
          ? error.message
          : "Shadow corridor stats endpoint not yet implemented"
      );
    } finally {
      setCorridorsLoading(false);
    }
  };

  // Load data on mount
  useEffect(() => {
    void loadStats();
    void loadEvents();
    void loadCorridors();
  }, []);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-white">
          Shadow Mode Dashboard
        </h1>
        <p className="text-slate-400 text-lg">
          Real-time model performance comparison and drift detection
        </p>
      </div>

      {/* Backend Status Notice */}
      <div className="p-4 bg-amber-900/10 border border-amber-700/50 rounded-xl">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <p className="text-amber-400 font-semibold text-sm">
              Backend Endpoints Not Yet Available
            </p>
            <p className="text-amber-300 text-xs mt-1">
              This dashboard is scaffolding only. Shadow mode functionality exists in
              the backend (database, repo, analysis), but REST API endpoints have not
              been exposed yet.
            </p>
            <p className="text-slate-400 text-xs mt-2">
              <strong>TODO:</strong> Cody/Dan to add{" "}
              <code className="bg-slate-800 px-1 py-0.5 rounded">
                /iq/ml/shadow/*
              </code>{" "}
              endpoints. Once available, remove this notice and uncomment API calls in{" "}
              <code className="bg-slate-800 px-1 py-0.5 rounded">
                api/shadow.ts
              </code>
              .
            </p>
          </div>
        </div>
      </div>

      {/* Stats Card */}
      <ShadowStatsCard
        stats={stats}
        isLoading={statsLoading}
        error={statsError}
      />

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Corridor Breakdown */}
        <ShadowCorridorTable
          corridors={corridors}
          isLoading={corridorsLoading}
          error={corridorsError}
        />

        {/* Recent Events */}
        <ShadowEventsTable
          events={events}
          isLoading={eventsLoading}
          error={eventsError}
        />
      </div>

      {/* Refresh Button (for manual testing) */}
      <div className="flex justify-center">
        <button
          onClick={() => {
            void loadStats();
            void loadEvents();
            void loadCorridors();
          }}
          disabled={statsLoading || eventsLoading || corridorsLoading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors text-sm"
        >
          {statsLoading || eventsLoading || corridorsLoading
            ? "Loading..."
            : "Refresh Data"}
        </button>
      </div>
    </div>
  );
}
