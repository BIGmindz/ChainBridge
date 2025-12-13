/**
 * BidModal - Marketplace Bidding Interface
 *
 * Features:
 * - Manual bid input with fee transparency
 * - Quick bid buttons (+5%, +10%)
 * - Fee calculation display
 * - Confirmation flow
 */

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, X, Zap } from "lucide-react";
import { memo, useEffect, useState } from "react";

import type { Listing } from "../../types/marketplace";
import { classNames } from "../../utils/classNames";

interface BidModalProps {
  listing: Listing | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (bidAmount: number) => Promise<void>;
  isSubmitting?: boolean;
}

/**
 * Platform fee percentage (configurable)
 */
const PLATFORM_FEE_PERCENT = 5; // 5% fee on bid amount

export function BidModalComponent({ listing, isOpen, onClose, onSubmit, isSubmitting }: BidModalProps) {
  const [bidAmount, setBidAmount] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [step, setStep] = useState<"input" | "confirm">("input");

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setBidAmount("");
      setError("");
      setStep("input");
    }
  }, [isOpen]);

  if (!listing) return null;

  const parsedBid = parseFloat(bidAmount) || 0;
  const isValidBid = parsedBid > listing.currentPrice;
  const platformFee = isValidBid ? parsedBid * (PLATFORM_FEE_PERCENT / 100) : 0;
  const totalAmount = isValidBid ? parsedBid + platformFee : 0;
  const minimumBid = listing.currentPrice + 1; // Minimum increment

  const handleQuickBid = (percentIncrease: number) => {
    const newBid = listing.currentPrice * (1 + percentIncrease / 100);
    setBidAmount(newBid.toFixed(2));
    setError("");
  };

  const handleSubmit = async () => {
    if (!isValidBid) {
      setError(`Bid must be at least $${minimumBid.toFixed(2)}`);
      return;
    }

    if (step === "input") {
      setStep("confirm");
      return;
    }

    try {
      await onSubmit(parsedBid);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to place bid");
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-gradient-to-b from-slate-800 to-slate-900 rounded-lg shadow-2xl border border-slate-700 max-w-md w-full overflow-hidden">
              {/* Header */}
              <div className="bg-gradient-to-r from-slate-800 to-slate-900 px-6 py-4 border-b border-slate-700 flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-100">Place Bid</h2>
                <button
                  onClick={onClose}
                  disabled={isSubmitting}
                  title="Close modal"
                  className="p-1 hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {/* Content */}
              <div className="px-6 py-4 space-y-4">
                {/* Asset Info */}
                <div className="bg-slate-950/50 border border-slate-700/50 rounded-lg p-3">
                  <h3 className="text-sm font-semibold text-slate-100 mb-1">{listing.title}</h3>
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>Current: ${listing.currentPrice.toLocaleString()}</span>
                    <span>Bids: {listing.bidCount}</span>
                  </div>
                </div>

                {step === "input" && (
                  <>
                    {/* Bid Input */}
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Your Bid Amount
                      </label>
                      <div className="flex items-center border border-slate-600 rounded-lg bg-slate-950 overflow-hidden focus-within:border-cyan-500 transition-colors">
                        <span className="px-3 text-slate-500 font-mono">$</span>
                        <input
                          type="number"
                          min={minimumBid}
                          value={bidAmount}
                          onChange={(e) => {
                            setBidAmount(e.target.value);
                            setError("");
                          }}
                          placeholder={`${minimumBid.toFixed(2)}`}
                          className="flex-1 px-3 py-3 bg-transparent text-slate-100 font-mono text-lg focus:outline-none"
                          disabled={isSubmitting}
                        />
                      </div>
                      {isValidBid && (
                        <p className="text-xs text-green-400 mt-2">
                          ✓ Valid bid (≥ ${minimumBid.toFixed(2)})
                        </p>
                      )}
                    </div>

                    {/* Quick Bid Buttons */}
                    <div className="bg-slate-950/50 border border-slate-700/50 rounded-lg p-3">
                      <p className="text-xs font-medium text-slate-400 mb-2">Quick Bids</p>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => handleQuickBid(5)}
                          className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 text-sm font-medium rounded transition-colors"
                          disabled={isSubmitting}
                        >
                          +5% (+${(listing.currentPrice * 0.05).toFixed(0)})
                        </button>
                        <button
                          onClick={() => handleQuickBid(10)}
                          className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 text-sm font-medium rounded transition-colors"
                          disabled={isSubmitting}
                        >
                          +10% (+${(listing.currentPrice * 0.1).toFixed(0)})
                        </button>
                      </div>
                    </div>

                    {/* Fee Transparency */}
                    {isValidBid && (
                      <div className="bg-gradient-to-r from-blue-950 to-blue-900/50 border border-blue-700/50 rounded-lg p-3 space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-300">Bid Amount:</span>
                          <span className="font-mono text-slate-100">${parsedBid.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-300">Platform Fee ({PLATFORM_FEE_PERCENT}%):</span>
                          <span className="font-mono text-slate-100">${platformFee.toFixed(2)}</span>
                        </div>
                        <div className="border-t border-blue-700/50 pt-2 flex justify-between text-sm font-semibold">
                          <span className="text-slate-100">Total:</span>
                          <span className="font-mono text-cyan-300">${totalAmount.toFixed(2)}</span>
                        </div>
                      </div>
                    )}

                    {/* Error Message */}
                    {error && (
                      <div className="bg-red-950/50 border border-red-700/50 rounded-lg p-3 flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-red-300">{error}</p>
                      </div>
                    )}
                  </>
                )}

                {step === "confirm" && (
                  <>
                    {/* Confirmation */}
                    <div className="bg-gradient-to-r from-cyan-950 to-cyan-900/50 border border-cyan-700/50 rounded-lg p-4 space-y-3">
                      <div className="flex items-center gap-2 mb-3">
                        <Zap className="w-5 h-5 text-cyan-400" />
                        <p className="text-sm font-semibold text-slate-100">Confirm Bid</p>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-slate-300">Bid Amount:</span>
                          <span className="font-mono font-semibold text-slate-100">${parsedBid.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-300">Platform Fee:</span>
                          <span className="font-mono font-semibold text-slate-100">${platformFee.toFixed(2)}</span>
                        </div>
                        <div className="border-t border-cyan-700/50 pt-2 flex justify-between">
                          <span className="font-semibold text-slate-100">Total:</span>
                          <span className="font-mono text-lg font-bold text-cyan-300">${totalAmount.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Confirmation Message */}
                    <div className="text-center text-sm text-slate-400">
                      <p>Submitting your bid to the blockchain...</p>
                    </div>
                  </>
                )}
              </div>

              {/* Footer */}
              <div className="bg-slate-950/50 border-t border-slate-700 px-6 py-3 flex gap-3">
                <button
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="flex-1 px-4 py-2 border border-slate-600 hover:border-slate-500 text-slate-100 font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {step === "confirm" ? "Back" : "Cancel"}
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || (step === "input" && !isValidBid)}
                  className={classNames(
                    "flex-1 px-4 py-2 font-medium rounded-lg transition-all duration-200 shadow-lg",
                    step === "confirm"
                      ? "bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white hover:shadow-cyan-500/30 disabled:opacity-50"
                      : "bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-slate-100 disabled:opacity-50"
                  )}
                >
                  {isSubmitting ? "Submitting..." : step === "confirm" ? "Confirm Bid" : "Review"}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export const BidModal = memo(BidModalComponent);
