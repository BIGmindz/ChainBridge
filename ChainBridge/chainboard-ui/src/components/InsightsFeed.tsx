/**
 * InsightsFeed Component
 *
 * Displays ChainIQ risk stories as a feed of actionable intelligence.
 * Shows human-readable narratives explaining why shipments are risky.
 */

import type { RiskStory } from "../core/types/iq";
import { useRiskStories } from "../hooks/useRiskStories";

import { RiskBadge } from "./RiskBadge";

export function InsightsFeed() {
  const { data, loading, error, refetch } = useRiskStories(20);

  return (
    <section className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <header className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Risk Insights</h3>
          <p className="text-sm text-gray-600 mt-0.5">
            AI-generated narratives explaining shipment risks
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={loading}
          className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50"
        >
          Refresh
        </button>
      </header>

      {loading && !data && (
        <div className="px-6 py-12">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
                <div className="h-3 bg-gray-100 rounded w-3/4 mb-1"></div>
                <div className="h-3 bg-gray-100 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && !data && (
        <div className="px-6 py-12 text-center">
          <div className="text-red-600 mb-3">
            <svg
              className="w-12 h-12 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <p className="text-gray-700 font-medium mb-1">Failed to load insights</p>
          <p className="text-sm text-gray-500 mb-4">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {data && data.stories.length === 0 && (
        <div className="px-6 py-12 text-center text-gray-500">
          <p>No risk stories available</p>
        </div>
      )}

      {data && data.stories.length > 0 && (
        <ul className="divide-y divide-gray-100">
          {data.stories.map((story) => (
            <InsightItem key={story.shipmentId} story={story} />
          ))}
        </ul>
      )}

      {data && (
        <footer className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          Showing {data.stories.length} of {data.total} insights
        </footer>
      )}
    </section>
  );
}

interface InsightItemProps {
  story: RiskStory;
}

function InsightItem({ story }: InsightItemProps) {
  return (
    <li className="px-6 py-4 hover:bg-gray-50 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900">{story.reference}</span>
          <span className="text-xs text-gray-400">•</span>
          <span className="text-xs text-gray-600">{story.corridor}</span>
        </div>
        <RiskBadge category={story.riskCategory} score={story.score} size="sm" />
      </div>

      <p className="text-sm text-gray-700 mb-2 leading-relaxed">{story.summary}</p>

      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-blue-600">→ {story.recommended_action}</span>
      </div>

      {story.factors.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {story.factors.map((factor) => (
            <span
              key={factor}
              className="inline-block px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
            >
              {formatFactor(factor)}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function formatFactor(factor: string): string {
  return factor
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
