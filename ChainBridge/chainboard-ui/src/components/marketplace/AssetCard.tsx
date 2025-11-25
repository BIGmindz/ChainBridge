/**
 * AssetCard - Trading Card Style Marketplace Listing
 *
 * Displays a distressed asset with:
 * - Image (or broken container placeholder)
 * - Discount badge
 * - Countdown timer (red if critical)
 * - Condition report (glass box transparency)
 * - Current bid and quick actions
 */

import { motion } from "framer-motion";
import { AlertTriangle, TrendingDown } from "lucide-react";
import { memo } from "react";

import type { Listing } from "../../types/marketplace";
import { classNames } from "../../utils/classNames";

import { Countdown } from "./Countdown";

interface AssetCardProps {
  listing: Listing;
  onViewDetails: (listingId: string) => void;
  onPlaceBid: (listingId: string) => void;
}

/**
 * Condition score to color mapping (glass box aesthetic)
 */
function getConditionColor(score: number): string {
  if (score >= 90) return "from-green-500 to-green-600";  // PRISTINE
  if (score >= 70) return "from-blue-500 to-blue-600";    // GOOD
  if (score >= 50) return "from-amber-500 to-amber-600";  // FAIR
  if (score >= 30) return "from-orange-500 to-orange-600"; // POOR
  return "from-red-500 to-red-600";                        // SALVAGE
}

/**
 * Condition score to text
 */
function getConditionLabel(score: number): string {
  if (score >= 90) return "PRISTINE";
  if (score >= 70) return "GOOD";
  if (score >= 50) return "FAIR";
  if (score >= 30) return "POOR";
  return "SALVAGE";
}

export function AssetCardComponent({ listing, onViewDetails, onPlaceBid }: AssetCardProps) {
  const conditionColor = getConditionColor(listing.conditionScore);
  const conditionLabel = getConditionLabel(listing.conditionScore);
  const timeRemainingMs = new Date(listing.auctionEndAt).getTime() - Date.now();
  const isAuctionActive = timeRemainingMs > 0;
  const isUrgent = timeRemainingMs < 3600000; // Less than 1 hour

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="relative group"
    >
      <div className="bg-gradient-to-b from-slate-800 to-slate-900 rounded-lg overflow-hidden border border-slate-700 hover:border-cyan-500/50 transition-all duration-300 shadow-lg hover:shadow-cyan-500/20">
        {/* Image Container */}
        <div className="relative w-full h-48 bg-slate-950 overflow-hidden">
          {listing.imageUrl ? (
            <img
              src={listing.imageUrl}
              alt={listing.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            // Broken container placeholder (glass box visual)
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-950 relative overflow-hidden">
              <div className="absolute inset-0 opacity-10">
                <div className="absolute top-4 left-4 w-24 h-32 border-2 border-cyan-400 rounded-lg transform -rotate-6" />
                <div className="absolute top-8 right-6 w-20 h-28 border-2 border-red-400 rounded-lg transform rotate-3" />
              </div>
              <div className="relative flex flex-col items-center justify-center text-center z-10">
                <div className="text-4xl mb-2">📦</div>
                <div className="text-xs text-slate-500">Container</div>
                <div className="text-xs text-slate-500">Damaged</div>
              </div>
            </div>
          )}

          {/* Discount Badge */}
          <div className="absolute top-3 right-3 z-20">
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="bg-gradient-to-r from-red-600 to-red-700 px-3 py-1 rounded-full border border-red-500/50 shadow-lg"
            >
              <div className="flex items-center gap-1">
                <TrendingDown className="w-3 h-3" />
                <span className="text-sm font-bold">{listing.discountPercent}%</span>
              </div>
            </motion.div>
          </div>

          {/* Countdown Timer (Red if urgent) */}
          <div className={classNames(
            "absolute bottom-3 left-3 z-20 px-3 py-2 rounded-lg border",
            isUrgent && isAuctionActive
              ? "bg-red-950/90 border-red-500/50 animate-pulse"
              : "bg-slate-950/80 border-slate-600/50"
          )}>
            <Countdown
              endAt={listing.auctionEndAt}
              onExpired={() => {}}
            />
          </div>
        </div>

        {/* Title */}
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-sm font-semibold text-slate-100 truncate hover:text-cyan-400 cursor-pointer transition-colors">
            {listing.title}
          </h3>
          <p className="text-xs text-slate-500 truncate">
            {listing.location}
          </p>
        </div>

        {/* Condition Report (Glass Box) */}
        <div className="px-4 py-3 border-t border-slate-700/50 bg-gradient-to-r from-slate-800/50 to-slate-900/50">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-slate-400">Condition</span>
            <span className="text-xs font-bold text-slate-300">{listing.conditionScore}/100</span>
          </div>
          <div className="relative h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-700">
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: listing.conditionScore / 100 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className={classNames(
                "h-full origin-left bg-gradient-to-r",
                conditionColor
              )}
              style={{ willChange: "transform" }}
            />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className={classNames(
              "text-xs font-semibold px-2 py-1 rounded-full",
              conditionLabel === "PRISTINE"
                ? "bg-green-500/20 text-green-300"
                : conditionLabel === "GOOD"
                ? "bg-blue-500/20 text-blue-300"
                : conditionLabel === "FAIR"
                ? "bg-amber-500/20 text-amber-300"
                : conditionLabel === "POOR"
                ? "bg-orange-500/20 text-orange-300"
                : "bg-red-500/20 text-red-300"
            )}>
              {conditionLabel}
            </span>
            <div className="text-xs text-slate-500">
              {listing.riskFactors.length > 0 && (
                <span className="flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-orange-400" />
                  {listing.riskFactors[0]}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Price & Bidding */}
        <div className="px-4 py-3 border-t border-slate-700/50">
          <div className="mb-3">
            <div className="text-xs text-slate-500 mb-1">Current Price</div>
            <div className="text-xl font-bold text-cyan-400 font-mono">
              ${listing.currentPrice.toLocaleString("en-US", { maximumFractionDigits: 0 })}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {listing.bidCount} bids • {listing.viewCount} views
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-2">
            <button
              onClick={() => onViewDetails(listing.id)}
              className="w-full px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 text-sm font-medium rounded-lg transition-colors duration-200"
            >
              View Details
            </button>
            {isAuctionActive && (
              <button
                onClick={() => onPlaceBid(listing.id)}
                className="w-full px-3 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-cyan-500/30"
              >
                Place Bid
              </button>
            )}
            {listing.buyNowPrice && (
              <button
                onClick={() => onPlaceBid(listing.id)}
                className="w-full px-3 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-medium rounded-lg transition-all duration-200"
              >
                Buy Now: ${listing.buyNowPrice.toLocaleString("en-US", { maximumFractionDigits: 0 })}
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export const AssetCard = memo(AssetCardComponent);
