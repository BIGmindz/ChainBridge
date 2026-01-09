/**
 * TracePage Component
 * PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
 * 
 * Main page for end-to-end trace visualization.
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-TRACE-004: OC renders full chain without inference
 * - INV-TRACE-005: Missing links are explicit and non-silent
 */

import React, { useState, useEffect } from 'react';
import type { OCTraceView, OCTraceTimeline, TraceDomain } from '../../types/trace';
import { traceApi } from '../../api/traceApi';
import { TraceView } from './TraceView';
import { TraceTimeline } from './TraceTimeline';
import { TraceGapIndicators } from './TraceGapIndicators';

// ═══════════════════════════════════════════════════════════════════════════════
// PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface TracePageProps {
  pdoId?: string;
  pacId?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════════════════════════════════════════

type TabId = 'overview' | 'timeline' | 'gaps';

interface Tab {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'timeline', label: 'Timeline', icon: '📅' },
  { id: 'gaps', label: 'Gaps', icon: '⚠️' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const TracePage: React.FC<TracePageProps> = ({ pdoId: initialPdoId, pacId }) => {
  // State
  const [pdoId, setPdoId] = useState(initialPdoId || '');
  const [searchInput, setSearchInput] = useState(initialPdoId || '');
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [traceView, setTraceView] = useState<OCTraceView | null>(null);
  const [timeline, setTimeline] = useState<OCTraceTimeline | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load trace data when PDO ID changes
  useEffect(() => {
    if (!pdoId) {
      setTraceView(null);
      setTimeline(null);
      return;
    }

    const loadTraceData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [viewResult, timelineResult] = await Promise.all([
          traceApi.getPDOTraceView(pdoId),
          traceApi.getPDOTraceTimeline(pdoId),
        ]);
        setTraceView(viewResult);
        setTimeline(timelineResult);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trace data');
        setTraceView(null);
        setTimeline(null);
      } finally {
        setLoading(false);
      }
    };

    loadTraceData();
  }, [pdoId]);

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPdoId(searchInput.trim());
  };

  // Handle node click (navigation)
  const handleNodeClick = (domain: TraceDomain, nodeId: string) => {
    console.log('Navigate to:', domain, nodeId);
    // Future: Implement click-through navigation
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                End-to-End Trace
              </h1>
              <p className="text-sm text-gray-500">
                PDO → Agent → Settlement → Ledger
              </p>
            </div>

            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Enter PDO ID..."
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
              >
                Search
              </button>
            </form>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* No PDO Selected */}
        {!pdoId && !loading && (
          <div className="text-center py-16">
            <span className="text-6xl">🔍</span>
            <h2 className="mt-4 text-lg font-medium text-gray-900">
              Enter a PDO ID to view trace
            </h2>
            <p className="mt-2 text-gray-500">
              Search for a PDO to see its complete trace chain
            </p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            <p className="mt-4 text-gray-500">Loading trace data...</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <span className="text-2xl">❌</span>
            <p className="mt-2 text-red-800">{error}</p>
          </div>
        )}

        {/* Trace Data */}
        {traceView && !loading && (
          <div className="space-y-6">
            {/* Tabs */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <nav className="flex border-b border-gray-200">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex-1 px-4 py-3 text-sm font-medium ${
                      activeTab === tab.id
                        ? 'border-b-2 border-blue-500 text-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <span className="mr-2">{tab.icon}</span>
                    {tab.label}
                    {tab.id === 'gaps' && traceView.gaps.length > 0 && (
                      <span className="ml-2 px-1.5 py-0.5 text-xs bg-amber-100 text-amber-800 rounded-full">
                        {traceView.gaps.length}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <TraceView
                    traceView={traceView}
                    onNodeClick={handleNodeClick}
                  />
                </div>
                <div>
                  <TraceGapIndicators
                    gaps={traceView.gaps}
                    completenessScore={traceView.completeness_score}
                    status={traceView.status}
                    pdoId={traceView.pdo_id}
                  />
                </div>
              </div>
            )}

            {activeTab === 'timeline' && timeline && (
              <TraceTimeline
                timeline={timeline}
                onEventClick={(event) => console.log('Event clicked:', event)}
              />
            )}

            {activeTab === 'gaps' && (
              <TraceGapIndicators
                gaps={traceView.gaps}
                completenessScore={traceView.completeness_score}
                status={traceView.status}
                pdoId={traceView.pdo_id}
              />
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-xs text-gray-400">
          PAC-009: End-to-End Traceability • INV-TRACE-004 / INV-TRACE-005
        </div>
      </footer>
    </div>
  );
};

export default TracePage;
