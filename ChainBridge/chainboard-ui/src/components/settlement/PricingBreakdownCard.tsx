/**
 * PricingBreakdownCard
 *
 * Visual pricing breakdown for settlement intelligence.
 * Shows base rate, fuel, accessorials, volatility buffer, and total.
 *
 * Features:
 * - Radial progress indicators
 * - Tailwind gradients
 * - Animated reveal on mount
 * - Expandable detail view
 * - Percentage contribution to total
 */

import { useState } from "react";

import { classNames } from "../../utils/classNames";

export interface PricingBreakdown {
  base_rate: number;
  fuel_surcharge: number;
  accessorials: number;
  volatility_buffer: number;
  total_price: number;
  currency: string;
}

interface PricingBreakdownCardProps {
  pricing: PricingBreakdown | null;
  isLoading?: boolean;
  compact?: boolean; // Compact mode for embedded views
}

interface PriceLineItem {
  label: string;
  amount: number;
  color: string;
  gradientFrom: string;
  gradientTo: string;
  description: string;
}

export function PricingBreakdownCard({
  pricing,
  isLoading = false,
  compact = false,
}: PricingBreakdownCardProps) {
  const [isExpanded, setIsExpanded] = useState(!compact);

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-800 rounded w-32" />
          <div className="h-8 bg-slate-800 rounded w-48" />
          <div className="space-y-2">
            <div className="h-3 bg-slate-800 rounded" />
            <div className="h-3 bg-slate-800 rounded w-5/6" />
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!pricing) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-center">
        <div className="text-slate-600 text-sm">
          💵 No pricing data available
        </div>
      </div>
    );
  }

  const total = pricing.total_price;

  const lineItems: PriceLineItem[] = [
    {
      label: "Base Rate",
      amount: pricing.base_rate,
      color: "text-blue-400",
      gradientFrom: "from-blue-500",
      gradientTo: "to-blue-600",
      description: "Core transportation cost",
    },
    {
      label: "Fuel Surcharge",
      amount: pricing.fuel_surcharge,
      color: "text-amber-400",
      gradientFrom: "from-amber-500",
      gradientTo: "to-amber-600",
      description: "Market-based fuel adjustment",
    },
    {
      label: "Accessorials",
      amount: pricing.accessorials,
      color: "text-purple-400",
      gradientFrom: "from-purple-500",
      gradientTo: "to-purple-600",
      description: "Additional services & fees",
    },
    {
      label: "Volatility Buffer",
      amount: pricing.volatility_buffer,
      color: "text-rose-400",
      gradientFrom: "from-rose-500",
      gradientTo: "to-rose-600",
      description: "Risk-adjusted pricing cushion",
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between border-b border-slate-800 hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">💵</span>
          <div className="text-left">
            <div className="text-xs text-slate-500 uppercase tracking-wide">Total Price</div>
            <div className="text-xl font-bold text-slate-200">
              {pricing.currency} {total.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
          </div>
        </div>
        <div className="text-slate-500 text-xs">
          {isExpanded ? "▼ Collapse" : "▶ Expand"}
        </div>
      </button>

      {/* Breakdown Details */}
      <div
        className={classNames(
          "overflow-hidden transition-all duration-300",
          isExpanded ? "max-h-96" : "max-h-0"
        )}
      >
        <div className="p-4 space-y-3">
          {lineItems.map((item) => {
            const percentage = total > 0 ? (item.amount / total) * 100 : 0;

            return (
              <div key={item.label} className="group">
                {/* Label & Amount */}
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={classNames("text-sm font-medium", item.color)}>
                      {item.label}
                    </span>
                    {!compact && (
                      <span className="text-xs text-slate-600">
                        ({percentage.toFixed(1)}%)
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-mono text-slate-300">
                    {pricing.currency} {item.amount.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="relative h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={classNames(
                      "absolute top-0 left-0 h-full bg-gradient-to-r transition-all duration-500",
                      item.gradientFrom,
                      item.gradientTo
                    )}
                    style={{ width: `${percentage}%` }}
                  />
                </div>

                {/* Description (expandable on hover) */}
                {!compact && (
                  <div className="text-xs text-slate-500 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {item.description}
                  </div>
                )}
              </div>
            );
          })}

          {/* Total Divider */}
          <div className="border-t border-slate-700 pt-3 mt-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-400">Total Settlement</span>
              <span className="text-lg font-bold font-mono text-emerald-400">
                {pricing.currency} {total.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
