/**
 * ListingDetailPage - Dutch Auction Detail View
 *
 * Layout:
 * - Hero: Asset image (left) + DutchAuctionCard (right)
 * - Sticky footer: Buy Now button
 * - Transparency: SmartReconcileCard showing risk factors
 * - Graph: PriceDecayGraph showing historical decay
 */

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowLeft, CheckCircle } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { getListingWithAuction } from "../../api/marketplace";
import { DutchAuctionCard } from "../../components/marketplace/DutchAuctionCard";
import { GodModePanel } from "../../components/marketplace/GodModePanel";
import { PriceDecayGraph } from "../../components/marketplace/PriceDecayGraph";
import { Skeleton } from "../../components/ui/Skeleton";
import { useMarketplaceWallet } from "../../hooks/useMarketplaceWallet";
import { classNames } from "../../utils/classNames";

function ListingDetailPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const navigate = useNavigate();
  const wallet = useMarketplaceWallet();
  // State management now handled by DutchAuctionCard component

  // Fetch listing details
  const { data: listing, isLoading, error, refetch } = useQuery({
    queryKey: ["listing", listingId],
    queryFn: () => (listingId ? getListingWithAuction(listingId) : null),
    staleTime: 10000, // 10 seconds
    refetchInterval: 30000, // Poll every 30 seconds for deep updates
    enabled: !!listingId,
  });

  // Note: Buy handling is now managed by DutchAuctionCard component

  if (!listingId) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <p className="text-slate-400 mb-4">No listing ID provided</p>
          <button
            onClick={() => navigate("/chainboard/marketplace")}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            Back to Marketplace
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-slate-400 mb-4">Failed to load listing</p>
          <button
            onClick={() => navigate("/chainboard/marketplace")}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            Back to Marketplace
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header Bar */}
      <div className="sticky top-0 z-40 bg-slate-950/95 backdrop-blur border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/chainboard/marketplace")}
            className="p-2 hover:bg-slate-900 rounded-lg transition-colors"
            title="Back to marketplace"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-100">{listing?.title || "Asset Details"}</h1>
            <p className="text-sm text-slate-500">
              {listing?.commodity} • {listing?.location}
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading ? (
          // Loading skeleton
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            <div className="space-y-4">
              <Skeleton className="w-full aspect-square rounded-lg" />
              <Skeleton className="h-40 w-full" />
            </div>
            <Skeleton className="h-96 rounded-lg" />
          </div>
        ) : listing ? (
          <>
            {/* Hero Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
              {/* Asset Image */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
                className="relative"
              >
                <div className="aspect-square rounded-lg overflow-hidden border border-slate-700/50 bg-slate-900/50">
                  <img
                    src={listing.imageUrl}
                    alt={listing.title}
                    className="w-full h-full object-cover"
                  />
                </div>
                {listing.status === "SOLD" && (
                  <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm rounded-lg flex items-center justify-center">
                    <div className="text-center">
                      <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-2" />
                      <p className="text-xl font-bold text-slate-100">SOLD</p>
                    </div>
                  </div>
                )}
              </motion.div>

              {/* Dutch Auction Card */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
              >
                <DutchAuctionCard
                  listingId={listing.id}
                  demoMode={true}
                  onSettled={(intent) => {
                    console.log('Settlement completed:', intent);
                    // Handle successful settlement
                  }}
                />
              </motion.div>
            </div>

            {/* Success handling is now managed by DutchAuctionCard */}

            {/* Transparency: Risk Factors (SmartReconcileCard equivalent) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mb-12"
            >
              <h2 className="text-lg font-bold text-slate-200 mb-4">Condition & Risk Factors</h2>
              <div className="p-6 rounded-lg border border-slate-700/50 bg-slate-900/30 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                      Condition Rating
                    </p>
                    <p className="text-2xl font-bold text-slate-100">
                      {listing.conditionScore}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                      Risk Factors
                    </p>
                    <p className={classNames(
                      "text-2xl font-bold",
                      listing.riskFactors.length > 2
                        ? "text-red-400"
                        : listing.riskFactors.length > 0
                        ? "text-orange-400"
                        : "text-green-400"
                    )}>
                      {listing.riskFactors.length}
                    </p>
                  </div>
                </div>

                {listing.riskFactors.length > 0 && (
                  <div className="pt-4 border-t border-slate-700/50">
                    <p className="text-sm font-semibold text-slate-300 mb-3">Risk Factors:</p>
                    <ul className="space-y-2">
                      {listing.riskFactors.map((factor, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-slate-400">
                          <AlertTriangle className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                          <span>{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </motion.div>

            {/* Price Decay Graph */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mb-12"
            >
              <PriceDecayGraph
                listing={listing}
                currentPrice={listing.startPrice}
                isDecaying={true}
              />
            </motion.div>

            {/* Wallet Connection */}
            {!wallet.wallet.isConnected && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-6 rounded-lg border border-slate-700/50 bg-slate-900/30 text-center"
              >
                <p className="text-slate-400 mb-4">Connect your wallet to purchase</p>
                <button
                  onClick={() => wallet.connectWallet()}
                  className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-semibold transition-colors"
                >
                  Connect Wallet
                </button>
              </motion.div>
            )}
          </>
        ) : null}
      </div>

      {/* God Mode Panel */}
      <GodModePanel
        listingId={listingId}
        onResetComplete={() => refetch()}
        onTimeWarped={() => refetch()}
      />
    </div>
  );
}

export default ListingDetailPage;
