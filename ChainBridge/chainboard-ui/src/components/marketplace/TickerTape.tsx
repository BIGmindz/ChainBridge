/**
 * TickerTape - Scrolling Marquee Header
 *
 * Displays "Just Sold" items in a high-speed trading desk style ticker.
 * Shows recently sold listings with final price and time ago.
 */

import { TrendingUp } from "lucide-react";
import { memo, useMemo } from "react";

import type { MarketplaceStats } from "../../types/marketplace";

interface TickerTapeProps {
  stats: MarketplaceStats;
}

/**
 * Format time ago string (e.g., "2m ago", "1h ago")
 */
function formatTimeAgo(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "Just now";
}

export function TickerTapeComponent({ stats }: TickerTapeProps) {
  // Create repeating ticker items for infinite scroll effect
  const tickerItems = useMemo(() => {
    const items = stats.justSoldList.map((item, idx) => ({
      ...item,
      key: `sold-${idx}`,
    }));
    // Duplicate items for infinite scroll effect
    return [...items, ...items, ...items];
  }, [stats.justSoldList]);

  return (
    <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border-b border-slate-700 overflow-hidden h-16 flex items-center shadow-lg">
      <div className="flex items-center gap-4 px-4 h-full w-full">
        {/* Header Label */}
        <div className="flex items-center gap-2 flex-shrink-0 border-r border-slate-700 pr-4">
          <TrendingUp className="w-4 h-4 text-green-400 animate-pulse" />
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Just Sold
          </span>
        </div>

        {/* Scrolling Ticker */}
        <div className="flex-1 overflow-hidden">
          <div className="flex gap-6 animate-scroll">
            {tickerItems.map((item) => (
              <div
                key={item.key}
                className="flex items-center gap-4 flex-shrink-0 py-2 px-4 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-cyan-500/50 transition-colors cursor-pointer"
              >
                <span className="text-sm font-semibold text-slate-100 whitespace-nowrap max-w-xs truncate">
                  {item.title}
                </span>
                <span className="text-sm font-mono font-bold text-emerald-400 whitespace-nowrap">
                  ${item.finalPrice.toLocaleString()}
                </span>
                <span className="text-xs text-slate-500 whitespace-nowrap">
                  {formatTimeAgo(item.timeAgoMs)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Volume Stats */}
        <div className="flex-shrink-0 border-l border-slate-700 pl-4 text-right">
          <div className="text-xs text-slate-500">Volume Today</div>
          <div className="text-lg font-bold text-cyan-400">
            ${(stats.volumeTodayUsd / 1000).toFixed(0)}K
          </div>
        </div>
      </div>

      <style>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-33.333%);
          }
        }

        .animate-scroll {
          animation: scroll 60s linear infinite;
        }

        .animate-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
}

export const TickerTape = memo(TickerTapeComponent);
