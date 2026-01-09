/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Timeline View — PAC → WRAP → BER Lifecycle Visualization
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Main timeline component displaying:
 * - Complete PAC lifecycle from admission to BER
 * - Segmented phases with progress tracking
 * - Filterable events by category, severity, agent
 * - Evidence hashes for immutability proof
 * 
 * INVARIANTS:
 * - INV-OCC-004: Timeline completeness (all transitions visible)
 * - INV-OCC-005: Evidence immutability (no retroactive edits)
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState, useCallback, useMemo } from 'react';
import type {
  PACTimelineState,
  TimelineEvent,
  TimelineFilterOptions,
  TimelineDisplayOptions,
  TimelineEventCategory,
  TimelineSegment as SegmentType,
} from './types';
import { TimelineSegment } from './TimelineSegment';

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const DEFAULT_DISPLAY_OPTIONS: TimelineDisplayOptions = {
  density: 'normal',
  groupByCategory: false,
  showEvidenceHashes: true,
  showArtifactLinks: true,
  autoScroll: true,
};

const LIFECYCLE_PHASES = [
  { id: 'admission', label: 'PAC Admission', categories: ['pac_lifecycle'] as TimelineEventCategory[] },
  { id: 'runtime', label: 'Runtime Activation', categories: ['pac_lifecycle', 'governance'] as TimelineEventCategory[] },
  { id: 'agent_activation', label: 'Agent Activation', categories: ['agent_activation'] as TimelineEventCategory[] },
  { id: 'execution', label: 'Execution', categories: ['execution', 'decision'] as TimelineEventCategory[] },
  { id: 'wrap', label: 'WRAP Collection', categories: ['wrap'] as TimelineEventCategory[] },
  { id: 'review', label: 'Review Gates', categories: ['review_gate'] as TimelineEventCategory[] },
  { id: 'ber', label: 'BER Issuance', categories: ['ber'] as TimelineEventCategory[] },
];

// ═══════════════════════════════════════════════════════════════════════════════
// FILTER BAR COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface FilterBarProps {
  filters: TimelineFilterOptions;
  onFilterChange: (filters: TimelineFilterOptions) => void;
  availableAgents: { agentId: string; agentName: string }[];
}

const FilterBar: React.FC<FilterBarProps> = ({ filters, onFilterChange, availableAgents }) => {
  const categoryOptions: TimelineEventCategory[] = [
    'pac_lifecycle', 'agent_activation', 'execution', 'decision',
    'wrap', 'review_gate', 'ber', 'governance', 'error',
  ];

  const handleCategoryToggle = (category: TimelineEventCategory) => {
    const current = filters.categories || [];
    const updated = current.includes(category)
      ? current.filter(c => c !== category)
      : [...current, category];
    onFilterChange({ ...filters, categories: updated.length > 0 ? updated : undefined });
  };

  const handleAgentToggle = (agentId: string) => {
    const current = filters.agentIds || [];
    const updated = current.includes(agentId)
      ? current.filter(a => a !== agentId)
      : [...current, agentId];
    onFilterChange({ ...filters, agentIds: updated.length > 0 ? updated : undefined });
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, searchText: e.target.value || undefined });
  };

  const clearFilters = () => {
    onFilterChange({});
  };

  const hasFilters = filters.categories?.length || filters.agentIds?.length || filters.searchText;

  return (
    <div className="bg-gray-800 rounded-lg p-3 mb-4" role="search" aria-label="Timeline filters">
      {/* Search */}
      <div className="mb-3">
        <input
          type="text"
          placeholder="Search events..."
          value={filters.searchText || ''}
          onChange={handleSearchChange}
          className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Search timeline events"
        />
      </div>

      {/* Category filters */}
      <div className="mb-3">
        <span className="text-xs text-gray-500 block mb-2">Categories:</span>
        <div className="flex flex-wrap gap-1">
          {categoryOptions.map((category) => (
            <button
              key={category}
              onClick={() => handleCategoryToggle(category)}
              className={`
                px-2 py-1 text-xs rounded transition-colors
                ${filters.categories?.includes(category)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }
              `}
              aria-pressed={filters.categories?.includes(category)}
            >
              {category.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Agent filters */}
      {availableAgents.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-500 block mb-2">Agents:</span>
          <div className="flex flex-wrap gap-1">
            {availableAgents.map((agent) => (
              <button
                key={agent.agentId}
                onClick={() => handleAgentToggle(agent.agentId)}
                className={`
                  px-2 py-1 text-xs rounded transition-colors
                  ${filters.agentIds?.includes(agent.agentId)
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }
                `}
                aria-pressed={filters.agentIds?.includes(agent.agentId)}
              >
                {agent.agentName}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Clear filters */}
      {hasFilters && (
        <button
          onClick={clearFilters}
          className="text-xs text-blue-400 hover:text-blue-300"
        >
          Clear all filters
        </button>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE HEADER
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineHeaderProps {
  state: PACTimelineState;
  displayOptions: TimelineDisplayOptions;
  onDisplayOptionsChange: (options: TimelineDisplayOptions) => void;
}

const TimelineHeader: React.FC<TimelineHeaderProps> = ({
  state,
  displayOptions,
  onDisplayOptionsChange,
}) => {
  const statusColor = {
    ADMISSION: 'text-blue-400',
    RUNTIME_ACTIVATION: 'text-blue-400',
    AGENT_ACTIVATION: 'text-purple-400',
    EXECUTING: 'text-cyan-400',
    WRAP_COLLECTION: 'text-yellow-400',
    REVIEW_GATE: 'text-orange-400',
    BER_ISSUED: 'text-green-400',
    SETTLED: 'text-green-400',
    FAILED: 'text-red-400',
    CANCELLED: 'text-gray-400',
  }[state.lifecycleState];

  return (
    <header className="bg-gray-800 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">📊</span>
            <h2 className="text-lg font-bold text-gray-100">
              PAC Timeline
            </h2>
          </div>
          <div className="mt-1 text-sm">
            <span className="font-mono text-blue-400">{state.pacId}</span>
            <span className="text-gray-500 mx-2">•</span>
            <span className={statusColor}>{state.lifecycleState.replace('_', ' ')}</span>
          </div>
          <p className="mt-1 text-sm text-gray-400">{state.title}</p>
        </div>

        {/* Display options */}
        <div className="flex items-center gap-2">
          <select
            value={displayOptions.density}
            onChange={(e) => onDisplayOptionsChange({
              ...displayOptions,
              density: e.target.value as 'compact' | 'normal' | 'expanded',
            })}
            className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
            aria-label="Display density"
          >
            <option value="compact">Compact</option>
            <option value="normal">Normal</option>
            <option value="expanded">Expanded</option>
          </select>

          <label className="flex items-center gap-1 text-xs text-gray-400">
            <input
              type="checkbox"
              checked={displayOptions.showEvidenceHashes}
              onChange={(e) => onDisplayOptionsChange({
                ...displayOptions,
                showEvidenceHashes: e.target.checked,
              })}
              className="rounded bg-gray-700 border-gray-600"
            />
            Hashes
          </label>
        </div>
      </div>

      {/* Summary stats */}
      <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
        <span>{state.events.length} events</span>
        <span>{state.agentAcks.length} agent ACKs</span>
        <span>{state.wrapMilestones.length} WRAPs</span>
        <span>{state.reviewGates.length} review gates</span>
        <span>{state.berRecords.length} BERs</span>
      </div>
    </header>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN TIMELINE VIEW COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface TimelineViewProps {
  pacId: string;
  state: PACTimelineState | null;
  loading?: boolean;
  error?: string | null;
  onEventSelect?: (event: TimelineEvent) => void;
  onRefresh?: () => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
  pacId,
  state,
  loading = false,
  error = null,
  onEventSelect,
  onRefresh,
}) => {
  const [filters, setFilters] = useState<TimelineFilterOptions>({});
  const [displayOptions, setDisplayOptions] = useState<TimelineDisplayOptions>(DEFAULT_DISPLAY_OPTIONS);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  // Extract unique agents from events
  const availableAgents = useMemo(() => {
    if (!state) return [];
    const agentMap = new Map<string, { agentId: string; agentName: string }>();
    state.events.forEach(event => {
      if (event.agentId && event.agentName) {
        agentMap.set(event.agentId, { agentId: event.agentId, agentName: event.agentName });
      }
    });
    return Array.from(agentMap.values());
  }, [state]);

  // Filter events
  const filteredEvents = useMemo(() => {
    if (!state) return [];
    let events = [...state.events];

    if (filters.categories?.length) {
      events = events.filter(e => filters.categories!.includes(e.category));
    }
    if (filters.agentIds?.length) {
      events = events.filter(e => e.agentId && filters.agentIds!.includes(e.agentId));
    }
    if (filters.searchText) {
      const search = filters.searchText.toLowerCase();
      events = events.filter(e =>
        e.title.toLowerCase().includes(search) ||
        e.description.toLowerCase().includes(search)
      );
    }

    return events;
  }, [state, filters]);

  // Build segments from filtered events
  const segments = useMemo((): SegmentType[] => {
    if (!state) return [];

    return LIFECYCLE_PHASES.map((phase, index) => {
      const phaseEvents = filteredEvents.filter(e => phase.categories.includes(e.category));
      const firstEvent = phaseEvents[0];
      const lastEvent = phaseEvents[phaseEvents.length - 1];

      // Determine status based on lifecycle state
      let status: 'pending' | 'active' | 'complete' | 'failed' = 'pending';
      const phaseIndex = LIFECYCLE_PHASES.findIndex(p => p.id === phase.id);
      const currentIndex = {
        ADMISSION: 0,
        RUNTIME_ACTIVATION: 1,
        AGENT_ACTIVATION: 2,
        EXECUTING: 3,
        WRAP_COLLECTION: 4,
        REVIEW_GATE: 5,
        BER_ISSUED: 6,
        SETTLED: 6,
        FAILED: -1,
        CANCELLED: -1,
      }[state.lifecycleState];

      if (state.lifecycleState === 'FAILED' || state.lifecycleState === 'CANCELLED') {
        status = phaseEvents.length > 0 ? 'failed' : 'pending';
      } else if (phaseIndex < currentIndex) {
        status = 'complete';
      } else if (phaseIndex === currentIndex) {
        status = 'active';
      }

      // Calculate progress for active phase
      let progress = 0;
      if (status === 'complete') progress = 100;
      else if (status === 'active' && phaseEvents.length > 0) {
        progress = Math.min(90, phaseEvents.length * 15); // Rough estimate
      }

      return {
        segmentId: phase.id,
        label: phase.label,
        startTime: firstEvent?.timestamp || state.startedAt,
        endTime: status === 'complete' ? lastEvent?.timestamp : undefined,
        status,
        events: phaseEvents,
        progress,
      };
    });
  }, [state, filteredEvents]);

  // Handle event selection
  const handleEventSelect = useCallback((event: TimelineEvent) => {
    setSelectedEventId(event.eventId);
    onEventSelect?.(event);
  }, [onEventSelect]);

  // Error state
  if (error) {
    return (
      <div
        className="bg-gray-800 border border-red-700 rounded-lg p-4"
        role="alert"
        aria-live="assertive"
      >
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span aria-hidden="true">🛑</span>
          <span className="font-medium">Timeline Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="mt-2 text-sm text-blue-400 hover:text-blue-300"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  // Loading state
  if (loading && !state) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
          <p className="mt-2 text-sm text-gray-400">Loading timeline for {pacId}...</p>
        </div>
      </div>
    );
  }

  // No state
  if (!state) {
    return (
      <div className="bg-gray-800 rounded-lg p-8 text-center">
        <p className="text-gray-400">No timeline data available for {pacId}</p>
      </div>
    );
  }

  return (
    <div
      className="bg-gray-900 rounded-lg"
      role="region"
      aria-label={`Timeline for ${state.pacId}`}
    >
      {/* Header */}
      <TimelineHeader
        state={state}
        displayOptions={displayOptions}
        onDisplayOptionsChange={setDisplayOptions}
      />

      {/* Filter bar */}
      <FilterBar
        filters={filters}
        onFilterChange={setFilters}
        availableAgents={availableAgents}
      />

      {/* Timeline segments */}
      <div className="p-4 space-y-4" role="list" aria-label="Timeline phases">
        {segments.map((segment, index) => (
          <TimelineSegment
            key={segment.segmentId}
            segment={segment}
            isLast={index === segments.length - 1}
            density={displayOptions.density}
            showEvidenceHashes={displayOptions.showEvidenceHashes}
            showArtifactLinks={displayOptions.showArtifactLinks}
            onEventSelect={handleEventSelect}
            selectedEventId={selectedEventId || undefined}
          />
        ))}
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center">
          <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
        </div>
      )}
    </div>
  );
};

export default TimelineView;
