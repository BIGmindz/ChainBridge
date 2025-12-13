/**
 * PriceDecayGraph - Visual representation of price decay over time
 *
 * Shows:
 * - Start → Now → Reserve price trajectory
 * - Shaded discount depth area
 * - Time-to-expiry annotations
 * - Historical price points (if available from server)
 */

import { memo, useMemo } from "react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    Line,
    ResponsiveContainer,
    XAxis,
    YAxis,
} from "recharts";

import type { DutchAuctionState, Listing } from "../../types/marketplace";
import { classNames } from "../../utils/classNames";

interface PriceDecayGraphProps {
  listing: Listing & { dutchAuction?: DutchAuctionState };
  currentPrice: number;
  isDecaying?: boolean;
}

interface DataPoint {
  time: string;
  timeMinutes: number;
  price: number;
  reserve: number;
  pricePercent: number; // % of discount depth used
}

function PriceDecayGraphComponent({
  listing,
  currentPrice,
  isDecaying = false,
}: PriceDecayGraphProps) {
  const data = useMemo(() => {
    if (!listing.dutchAuction) return [];

    const {
      startPrice,
      reservePrice,
      decayRatePerHour,
      startedAt,
      expiresAt,
    } = listing.dutchAuction;

    const totalDecay = startPrice - reservePrice;
    const decayPerMinute = decayRatePerHour / 60;

    // Build timeline: every 5 minutes
    const startTime = new Date(startedAt).getTime();
    const endTime = new Date(expiresAt).getTime();
    const totalMinutes = (endTime - startTime) / 60000;

    const points: DataPoint[] = [];
    const interval = Math.max(1, Math.floor(totalMinutes / 20)); // ~20 points on chart

    for (let i = 0; i <= totalMinutes; i += interval) {
      const priceAtTime = Math.max(
        reservePrice,
        startPrice - (decayPerMinute * i)
      );
      const discountUsed = startPrice - priceAtTime;
      const discountPercent = (discountUsed / totalDecay) * 100;

      points.push({
        time: `${Math.floor(i / 60)}h ${i % 60}m`,
        timeMinutes: i,
        price: Math.round(priceAtTime),
        reserve: reservePrice,
        pricePercent: Math.min(100, Math.round(discountPercent)),
      });
    }

    // Add current time marker
    const nowTime = new Date().getTime();
    const nowMinutes = (nowTime - startTime) / 60000;
    if (nowMinutes > 0 && nowMinutes < totalMinutes) {
      const currentAtNow = Math.max(
        reservePrice,
        startPrice - (decayPerMinute * nowMinutes)
      );
      points.push({
        time: "Now",
        timeMinutes: nowMinutes,
        price: Math.round(currentAtNow),
        reserve: reservePrice,
        pricePercent: ((startPrice - currentAtNow) / totalDecay) * 100,
      });
      points.sort((a, b) => a.timeMinutes - b.timeMinutes);
    }

    return points;
  }, [listing.dutchAuction]);

  if (data.length === 0) {
    return (
      <div className="w-full h-64 bg-slate-900/50 rounded-lg border border-slate-700/50 flex items-center justify-center text-slate-400">
        No auction data available
      </div>
    );
  }

  const reservePrice = listing.dutchAuction?.reservePrice || 0;
  const startPrice = listing.dutchAuction?.startPrice || 0;

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="px-4 pt-4">
        <h3 className="text-sm font-semibold text-slate-200 mb-2">Price Decay Timeline</h3>
        <p className="text-xs text-slate-500">
          Auction started at ${startPrice.toLocaleString()} and decays toward ${reservePrice.toLocaleString()}
        </p>
      </div>

      {/* Chart Container */}
      <div className="relative w-full h-80 bg-slate-950/50 rounded-lg border border-slate-700/50 overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 30, left: 0, bottom: 50 }}
          >
            {/* Grid */}
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.2}
              vertical={false}
            />

            {/* Axes */}
            <XAxis
              dataKey="time"
              stroke="#94a3b8"
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="#94a3b8"
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              label={{ value: "Price ($)", angle: -90, position: "insideLeft" }}
              domain={[reservePrice * 0.95, startPrice * 1.05]}
            />

            {/* Reserve Price Line */}
            <Line
              type="monotone"
              dataKey="reserve"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              isAnimationActive={false}
              name="Reserve Price"
            />

            {/* Price Area Fill (Discount Depth) */}
            <Area
              type="monotone"
              dataKey="price"
              fill="#06b6d4"
              stroke="#0891b2"
              strokeWidth={3}
              dot={false}
              isAnimationActive={isDecaying}
              animationDuration={1000}
              name="Current Price"
              fillOpacity={0.15}
            />
          </AreaChart>
        </ResponsiveContainer>

        {/* Loading Indicator */}
        {isDecaying && (
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
            <span className="text-xs text-cyan-400">Updating...</span>
          </div>
        )}
      </div>

      {/* Discount Depth Metrics */}
      <div className="grid grid-cols-3 gap-4 px-4 pb-4">
        <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
          <div className="text-xs text-slate-500 mb-1">Start</div>
          <div className="text-lg font-mono font-bold text-slate-200">
            ${startPrice.toLocaleString()}
          </div>
        </div>

        <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
          <div className="text-xs text-slate-500 mb-1">Current</div>
          <div className="text-lg font-mono font-bold text-cyan-400">
            ${Math.round(currentPrice).toLocaleString()}
          </div>
        </div>

        <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
          <div className="text-xs text-slate-500 mb-1">Reserve</div>
          <div className="text-lg font-mono font-bold text-amber-400">
            ${reservePrice.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Discount Depth Percentage */}
      {data.length > 0 && (
        <div className="px-4 pb-4">
          <div className="flex justify-between text-xs text-slate-400 mb-2">
            <span>Discount Utilization</span>
            <span className="text-cyan-400 font-semibold">
              {Math.round(data[data.length - 1]?.pricePercent || 0)}%
            </span>
          </div>
          <div className="h-3 bg-slate-900/70 rounded-full border border-slate-700/50 overflow-hidden">
            <div
              className={classNames(
                "h-full transition-all duration-500 rounded-full",
                data[data.length - 1]?.pricePercent || 0 > 85
                  ? "bg-gradient-to-r from-red-500 to-orange-500"
                  : "bg-gradient-to-r from-cyan-500 to-blue-500"
              )}
              style={{ width: `${Math.min(100, data[data.length - 1]?.pricePercent || 0)}%` } as React.CSSProperties}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export const PriceDecayGraph = memo(PriceDecayGraphComponent);
