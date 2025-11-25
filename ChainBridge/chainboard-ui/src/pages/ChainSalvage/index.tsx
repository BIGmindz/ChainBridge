/**
 * ChainSalvagePage - Marketplace for Distressed Assets
 *
 * High-speed trading desk for damaged/off-spec cargo, containers, and inventory.
 * Layout:
 * - Top: Scrolling ticker with "Just Sold" items
 * - Left: Filter sidebar (commodity, location, risk, price)
 * - Center: Grid of AssetCard listings
 * - Real-time bid history updates (2s polling)
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import {
    fetchListings,
    fetchMarketplaceStats,
    submitBid,
} from "../../api/chainpay";
import { AssetCard } from "../../components/marketplace/AssetCard";
import { BidModal } from "../../components/marketplace/BidModal";
import { TickerTape } from "../../components/marketplace/TickerTape";
import { Skeleton } from "../../components/ui/Skeleton";
import type { CommodityType, Listing } from "../../types/marketplace";
import { classNames } from "../../utils/classNames";

/**
 * Filter form state
 */
interface FilterState {
  commodities: CommodityType[];
  conditionMin: number;
  originPort: string;
  riskLevel: string;
  priceMin: number;
  priceMax: number;
}

const INITIAL_FILTERS: FilterState = {
  commodities: [],
  conditionMin: 0,
  originPort: "",
  riskLevel: "",
  priceMin: 0,
  priceMax: 999999,
};

const COMMODITIES: CommodityType[] = [
  "ELECTRONICS",
  "TEXTILES",
  "CONSUMABLES",
  "MACHINERY",
  "HAZMAT",
  "PERISHABLES",
  "MIXED",
];

export function ChainSalvagePage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>(INITIAL_FILTERS);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [isBidModalOpen, setIsBidModalOpen] = useState(false);
  const [isSubmittingBid, setIsSubmittingBid] = useState(false);

  // Fetch marketplace listings
  const { data: listings = [], isLoading: isLoadingListings } = useQuery({
    queryKey: [
      "marketplace:listings",
      filters.commodities,
      filters.conditionMin,
      filters.originPort,
    ],
    queryFn: () =>
      fetchListings({
        commodity: filters.commodities[0],
        condition_min: filters.conditionMin,
        location: filters.originPort || undefined,
        limit: 100,
      }),
    staleTime: 10000, // 10 second cache
  });

  // Fetch marketplace stats for ticker
  const { data: stats } = useQuery({
    queryKey: ["marketplace:stats"],
    queryFn: fetchMarketplaceStats,
    staleTime: 5000, // 5 second cache
  });

  // Poll bid history every 2 seconds for selected listing
  const { data: selectedListingData } = useQuery({
    queryKey: ["marketplace:listing", selectedListing?.id],
    queryFn: () =>
      selectedListing
        ? fetchListings({ limit: 1 }).then((items) =>
            items.find((l) => l.id === selectedListing.id)
          )
        : null,
    staleTime: 1000, // 1 second cache
    enabled: !!selectedListing,
    refetchInterval: 2000, // Poll every 2 seconds
  });

  // Filter listings by criteria
  const filteredListings = listings.filter((listing) => {
    if (
      filters.commodities.length > 0 &&
      !filters.commodities.includes(listing.commodity)
    ) {
      return false;
    }
    if (listing.conditionScore < filters.conditionMin) {
      return false;
    }
    if (
      filters.originPort &&
      !listing.location.toLowerCase().includes(filters.originPort.toLowerCase())
    ) {
      return false;
    }
    if (
      listing.currentPrice < filters.priceMin ||
      listing.currentPrice > filters.priceMax
    ) {
      return false;
    }
    return true;
  });

  // Handle bid submission
  const handlePlaceBid = async (bidAmount: number) => {
    if (!selectedListing) return;

    setIsSubmittingBid(true);

    try {
      const result = await submitBid(selectedListing.id, {
        bidAmount,
        bidderAddress: "0x_placeholder", // TODO: Connect Web3 wallet
      });

      if (result) {
        // Optimistic update: invalidate cache and refresh
        await queryClient.invalidateQueries({
          queryKey: ["marketplace:listings"],
        });
        await queryClient.invalidateQueries({
          queryKey: ["marketplace:listing", selectedListing.id],
        });
        setIsBidModalOpen(false);
      }
    } catch (err) {
      console.error("Bid submission failed:", err);
    } finally {
      setIsSubmittingBid(false);
    }
  };

  // Update selected listing with latest data
  useEffect(() => {
    if (selectedListingData) {
      setSelectedListing(selectedListingData);
    }
  }, [selectedListingData]);

  return (
    <div className="bg-slate-950 min-h-screen text-slate-100">
      {/* Header with Ticker */}
      {stats && <TickerTape stats={stats} />}

      <div className="flex h-screen relative">
        {/* Sidebar Filters */}
        <aside className="w-64 bg-slate-900 border-r border-slate-700 overflow-y-auto p-4 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-100 mb-4">Filters</h2>

            {/* Commodity Filter */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-300 mb-3">
                Commodity Type
              </label>
              <div className="space-y-2">
                {COMMODITIES.map((commodity) => (
                  <label key={commodity} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={filters.commodities.includes(commodity)}
                      onChange={(e) => {
                        setFilters((prev) => ({
                          ...prev,
                          commodities: e.target.checked
                            ? [...prev.commodities, commodity]
                            : prev.commodities.filter((c) => c !== commodity),
                        }));
                      }}
                      className="rounded border-slate-500 bg-slate-950 cursor-pointer"
                    />
                    <span className="text-sm text-slate-300">{commodity}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Condition Score Filter */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Condition Score (Min)
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={filters.conditionMin}
                onChange={(e) => {
                  setFilters((prev) => ({
                    ...prev,
                    conditionMin: parseInt(e.target.value),
                  }));
                }}
                className="w-full cursor-pointer"
              />
              <div className="text-xs text-slate-500 mt-1">
                {filters.conditionMin}/100
              </div>
            </div>

            {/* Origin Port Filter */}
            <div className="mb-6">
              <label htmlFor="origin-port" className="block text-sm font-semibold text-slate-300 mb-2">
                Origin Port
              </label>
              <input
                id="origin-port"
                type="text"
                placeholder="e.g., Los Angeles"
                value={filters.originPort}
                onChange={(e) => {
                  setFilters((prev) => ({
                    ...prev,
                    originPort: e.target.value,
                  }));
                }}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm focus:border-cyan-500 focus:outline-none"
              />
            </div>

            {/* Price Range Filter */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-300 mb-2">
                Price Range
              </label>
              <div className="space-y-2">
                <input
                  type="number"
                  placeholder="Min"
                  value={filters.priceMin || ""}
                  onChange={(e) => {
                    setFilters((prev) => ({
                      ...prev,
                      priceMin: parseInt(e.target.value) || 0,
                    }));
                  }}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm focus:border-cyan-500 focus:outline-none"
                />
                <input
                  type="number"
                  placeholder="Max"
                  value={filters.priceMax === 999999 ? "" : filters.priceMax}
                  onChange={(e) => {
                    setFilters((prev) => ({
                      ...prev,
                      priceMax: parseInt(e.target.value) || 999999,
                    }));
                  }}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Reset Filters */}
            <button
              onClick={() => setFilters(INITIAL_FILTERS)}
              className="w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-100 text-sm font-medium rounded-lg transition-colors"
            >
              Reset Filters
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Listings Grid */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-2xl font-bold text-slate-100">
                Marketplace Listings
              </h1>
              <button
                onClick={() =>
                  queryClient.invalidateQueries({
                    queryKey: ["marketplace:listings"],
                  })
                }
                title="Refresh listings"
                className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <RefreshCw
                  className={classNames(
                    "w-5 h-5 text-slate-400",
                    isLoadingListings && "animate-spin"
                  )}
                />
              </button>
            </div>

            {isLoadingListings ? (
              // Loading skeleton grid
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {[...Array(8)].map((_, i) => (
                  <Skeleton key={i} className="h-96 rounded-lg" />
                ))}
              </div>
            ) : filteredListings.length === 0 ? (
              // Empty state
              <div className="flex flex-col items-center justify-center h-96">
                <AlertTriangle className="w-12 h-12 text-slate-600 mb-4" />
                <p className="text-slate-400 text-lg">No listings match your filters</p>
                <button
                  onClick={() => setFilters(INITIAL_FILTERS)}
                  className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-100 rounded-lg transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              // Listings grid
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredListings.map((listing) => (
                  <AssetCard
                    key={listing.id}
                    listing={listing}
                    onViewDetails={(listingId) => {
                      const listing = filteredListings.find(
                        (l) => l.id === listingId
                      );
                      if (listing) {
                        setSelectedListing(listing);
                      }
                    }}
                    onPlaceBid={(listingId) => {
                      const listing = filteredListings.find(
                        (l) => l.id === listingId
                      );
                      if (listing) {
                        setSelectedListing(listing);
                        setIsBidModalOpen(true);
                      }
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bid Modal */}
      <BidModal
        listing={selectedListing}
        isOpen={isBidModalOpen}
        onClose={() => {
          setIsBidModalOpen(false);
        }}
        onSubmit={handlePlaceBid}
        isSubmitting={isSubmittingBid}
      />
    </div>
  );
}
