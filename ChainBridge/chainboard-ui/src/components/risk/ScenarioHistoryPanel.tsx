/**
 * ScenarioHistoryPanel — Example Integration for MAGGIE PAC-001
 * ==============================================================
 * Demonstrates how to integrate the AI preset recommender into a React component.
 *
 * Usage:
 *   import ScenarioHistoryPanel from "@/components/risk/ScenarioHistoryPanel";
 *   <ScenarioHistoryPanel presets={savedPresets} currentCategory="RISK_ANALYSIS" />
 */

import { useMemo, useState } from "react";
import {
  computeRecommendations,
  logRecommendationTable,
  validateRecommendations,
  type SavedFilterPreset,
  type PresetCategory,
  type PresetRecommendation,
  type RecommendationContext,
} from "@/ai/presetRecommender";

interface ScenarioHistoryPanelProps {
  /** All available filter presets */
  presets: readonly SavedFilterPreset[];
  /** Current category context for recommendations */
  currentCategory?: PresetCategory;
  /** Current tag context for recommendations */
  currentTags?: string[];
  /** Callback when user selects a preset */
  onSelectPreset?: (presetId: string) => void;
  /** Show debug information */
  debug?: boolean;
}

export default function ScenarioHistoryPanel({
  presets,
  currentCategory,
  currentTags = [],
  onSelectPreset,
  debug = false,
}: ScenarioHistoryPanelProps): JSX.Element {
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);

  // Build recommendation context from props
  const context: RecommendationContext = useMemo(
    () => ({
      currentCategory,
      currentTags,
    }),
    [currentCategory, currentTags]
  );

  // Compute recommendations (memoized internally by the engine)
  const recommendationResult = useMemo(() => {
    const result = computeRecommendations(presets, context, {
      topN: 3,
      includeDebug: debug,
    });

    // Log in development
    if (debug) {
      logRecommendationTable(result);
      const validation = validateRecommendations(result);
      if (!validation.valid) {
        console.error("[MAGGIE] Validation issues:", validation.issues);
      }
    }

    return result;
  }, [presets, context, debug]);

  const handleSelectPreset = (presetId: string) => {
    setSelectedPresetId(presetId);
    onSelectPreset?.(presetId);
  };

  const recommendations = recommendationResult.recommendations;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">
          AI Recommended Presets
        </h3>
        <span className="text-xs text-slate-400">
          Powered by MAGGIE PAC-001
        </span>
      </div>

      {recommendations.length === 0 ? (
        <p className="text-sm text-slate-400">
          No recommendations available. Add more presets or usage history.
        </p>
      ) : (
        <div className="space-y-3">
          {recommendations.map((rec, index) => (
            <PresetRecommendationCard
              key={rec.presetId}
              recommendation={rec}
              rank={index + 1}
              isSelected={selectedPresetId === rec.presetId}
              onSelect={() => handleSelectPreset(rec.presetId)}
              showBreakdown={debug}
            />
          ))}
        </div>
      )}

      {debug && recommendationResult.debug && (
        <div className="mt-4 rounded border border-slate-600 bg-slate-900 p-3">
          <h4 className="mb-2 text-xs font-medium text-slate-300">
            Debug Info
          </h4>
          <pre className="overflow-x-auto text-xs text-slate-400">
            {JSON.stringify(recommendationResult.debug, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

interface PresetRecommendationCardProps {
  recommendation: PresetRecommendation;
  rank: number;
  isSelected: boolean;
  onSelect: () => void;
  showBreakdown?: boolean;
}

function PresetRecommendationCard({
  recommendation,
  rank,
  isSelected,
  onSelect,
  showBreakdown = false,
}: PresetRecommendationCardProps): JSX.Element {
  const { presetName, score, breakdown, reasons } = recommendation;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border p-3 text-left transition-all ${
        isSelected
          ? "border-blue-500 bg-blue-500/10"
          : "border-slate-600 bg-slate-700/30 hover:border-slate-500 hover:bg-slate-700/50"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-600 text-xs font-bold text-white">
            {rank}
          </span>
          <span className="font-medium text-white">{presetName}</span>
        </div>
        <ScoreBadge score={score} />
      </div>

      {/* Reasons */}
      <div className="mt-2 flex flex-wrap gap-1">
        {reasons.map((reason) => (
          <span
            key={reason}
            className="rounded bg-slate-600/50 px-2 py-0.5 text-xs text-slate-300"
          >
            {reason}
          </span>
        ))}
      </div>

      {/* Score breakdown (debug mode) */}
      {showBreakdown && (
        <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
          <BreakdownItem label="Usage" value={breakdown.usage} />
          <BreakdownItem label="Recency" value={breakdown.recency} />
          <BreakdownItem label="Tags" value={breakdown.tags} />
          <BreakdownItem label="Category" value={breakdown.category} />
        </div>
      )}
    </button>
  );
}

function ScoreBadge({ score }: { score: number }): JSX.Element {
  const percentage = Math.round(score * 100);
  const colorClass =
    percentage >= 70
      ? "bg-green-500/20 text-green-400"
      : percentage >= 40
        ? "bg-yellow-500/20 text-yellow-400"
        : "bg-slate-500/20 text-slate-400";

  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {percentage}% match
    </span>
  );
}

function BreakdownItem({
  label,
  value,
}: {
  label: string;
  value: number;
}): JSX.Element {
  const barWidth = Math.round(value * 100);
  return (
    <div className="text-slate-400">
      <div className="mb-1">{label}</div>
      <div className="h-1.5 w-full overflow-hidden rounded bg-slate-600">
        <div
          className="h-full bg-blue-500 transition-all"
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <div className="mt-0.5 text-right">{value.toFixed(2)}</div>
    </div>
  );
}
