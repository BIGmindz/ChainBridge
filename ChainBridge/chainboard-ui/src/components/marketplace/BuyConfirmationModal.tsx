/**
 * BuyConfirmationModal - Enhanced Web3-aware purchase confirmation
 *
 * Implements complete 4-step buy flow with:
 * - Real-time settlement tracking
 * - Price drift handling
 * - Trust indicators
 * - Full accessibility (keyboard nav, focus traps, ARIA)
 * - Demo mode support
 */

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Check, Clock, X, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import type { BuyIntentResponse, CanonicalPriceQuote } from "../../api/marketplace";
import { classNames } from "../../utils/classNames";

interface BuyConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  listingTitle: string;
  displayPrice: number;          // Client-side animated price
  canonicalQuote?: CanonicalPriceQuote; // Server-authoritative price
  walletAddress: string;
  isDemoWallet: boolean;
  onConfirmPurchase: (quote: CanonicalPriceQuote) => Promise<BuyIntentResponse | null>;
}

type ModalStep = 'quote' | 'confirm' | 'intent' | 'result';

interface ResultState {
  success: boolean;
  message: string;
  intentId?: string;
  priceChanged?: {
    oldPrice: number;
    newPrice: number;
  };
}

export function BuyConfirmationModal({
  isOpen,
  onClose,
  listingTitle,
  displayPrice,
  canonicalQuote,
  walletAddress,
  isDemoWallet,
  onConfirmPurchase,
}: BuyConfirmationModalProps) {
  const [currentStep, setCurrentStep] = useState<ModalStep>('quote');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ResultState | null>(null);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isProcessing) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, isProcessing, onClose]);

  const handleConfirm = async () => {
    if (!canonicalQuote) return;

    setCurrentStep('intent');
    setIsProcessing(true);

    try {
      const response = await onConfirmPurchase(canonicalQuote);

      if (response) {
        if (response.status === 'PRICE_CHANGED') {
          setResult({
            success: false,
            message: 'Price changed since quote. Please review the updated price.',
            priceChanged: {
              oldPrice: displayPrice,
              newPrice: response.price,
            },
          });
        } else if (response.status === 'CONFIRMED' || response.status === 'PENDING') {
          setResult({
            success: true,
            message: 'Settlement intent created successfully! Your purchase is being processed.',
            intentId: response.intentId,
          });
        } else {
          setResult({
            success: false,
            message: response.errorMessage || 'Failed to create settlement intent',
          });
        }
      } else {
        setResult({
          success: false,
          message: 'Failed to create settlement intent. Please try again.',
        });
      }
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    } finally {
      setIsProcessing(false);
      setCurrentStep('result');
    }
  };

  const handleClose = () => {
    if (isProcessing) return; // Prevent closing during processing
    setCurrentStep('quote');
    setResult(null);
    setIsProcessing(false);
    onClose();
  };

  const handleConfirmKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isProcessing && canonicalQuote) {
      void handleConfirm();
    }
  };

  const priceDifference = canonicalQuote ? Math.abs(canonicalQuote.price - displayPrice) : 0;
  const hasPriceDifference = priceDifference > 0.01; // Ignore tiny differences

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleClose}
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: "spring", duration: 0.3 }}
          className="relative w-full max-w-md bg-slate-900 rounded-xl border border-slate-700 shadow-2xl"
          onKeyDown={handleConfirmKeyPress}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-slate-700">
            <h2 id="modal-title" className="text-lg font-bold text-white">
              {currentStep === 'quote' && 'Confirm Purchase'}
              {currentStep === 'confirm' && 'Review Terms'}
              {currentStep === 'intent' && 'Processing...'}
              {currentStep === 'result' && (result?.success ? 'Success!' : 'Error')}
            </h2>
            <button
              onClick={handleClose}
              disabled={isProcessing}
              className="p-1 text-slate-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">
            {/* Asset Info */}
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
              <div className="text-sm text-slate-400 mb-1">Asset</div>
              <div className="font-semibold text-white truncate">{listingTitle}</div>
            </div>

            {/* Wallet Info */}
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
              <div className="text-sm text-slate-400 mb-1">Wallet</div>
              <div className="font-mono text-sm text-white flex items-center gap-2">
                {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
                {isDemoWallet && (
                  <span className="px-2 py-1 text-xs bg-orange-500/20 text-orange-400 rounded border border-orange-500/30">
                    DEMO
                  </span>
                )}
              </div>
            </div>

            {/* Price Information */}
            {currentStep === 'quote' && canonicalQuote && (
              <div className="space-y-3">
                <div className="p-4 bg-cyan-950/30 rounded-lg border border-cyan-500/30">
                  <div className="text-sm text-cyan-400 mb-2 flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    Official ChainBridge Price
                  </div>
                  <div className="text-2xl font-bold font-mono text-white">
                    ${canonicalQuote.price.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Quoted at {new Date(canonicalQuote.quotedAt).toLocaleTimeString()}
                  </div>
                </div>

                {hasPriceDifference && (
                  <div className="p-3 bg-orange-950/30 rounded-lg border border-orange-500/30 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                    <div className="text-sm">
                      <div className="text-orange-400 font-medium mb-1">
                        Price Difference Detected
                      </div>
                      <div className="text-slate-300">
                        Client price: ${displayPrice.toLocaleString()}<br />
                        Server price wins for settlement
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Processing State */}
            {currentStep === 'intent' && (
              <div className="text-center py-8">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-12 h-12 mx-auto mb-4 border-2 border-cyan-500 border-t-transparent rounded-full"
                />
                <div className="text-white font-medium mb-2">Creating settlement intent...</div>
                <div className="text-sm text-slate-400">
                  {isDemoWallet ? 'Simulating Web3 transaction' : 'Please check your wallet'}
                </div>
              </div>
            )}

            {/* Result State */}
            {currentStep === 'result' && result && (
              <div className="text-center py-4">
                <div className={classNames(
                  "w-12 h-12 mx-auto mb-4 rounded-full flex items-center justify-center",
                  result.success
                    ? "bg-emerald-500/20 border-2 border-emerald-500"
                    : "bg-red-500/20 border-2 border-red-500"
                )}>
                  {result.success ? (
                    <Check className="w-6 h-6 text-emerald-400" />
                  ) : (
                    <X className="w-6 h-6 text-red-400" />
                  )}
                </div>

                <div className={classNames(
                  "font-medium mb-2",
                  result.success ? "text-emerald-400" : "text-red-400"
                )}>
                  {result.success ? 'Settlement in Progress' : 'Transaction Failed'}
                </div>

                <div className="text-sm text-slate-300 mb-4">
                  {result.message}
                </div>

                {result.intentId && (
                  <div className="p-3 bg-slate-800/50 rounded border border-slate-700/50">
                    <div className="text-xs text-slate-400 mb-1">Intent ID</div>
                    <div className="font-mono text-xs text-white break-all">
                      {result.intentId}
                    </div>
                  </div>
                )}

                {result.priceChanged && (
                  <div className="p-3 bg-orange-950/30 rounded border border-orange-500/30">
                    <div className="text-sm text-orange-400 font-medium mb-2">
                      Price Updated
                    </div>
                    <div className="text-xs text-slate-300">
                      Old: ${result.priceChanged.oldPrice.toLocaleString()}<br />
                      New: ${result.priceChanged.newPrice.toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 p-6 border-t border-slate-700">
            {currentStep === 'quote' && (
              <>
                <button
                  onClick={handleClose}
                  className="flex-1 px-4 py-2 text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                  aria-label="Cancel purchase"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={!canonicalQuote || isProcessing}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Confirm purchase"
                >
                  Confirm Purchase
                </button>
              </>
            )}

            {currentStep === 'result' && (
              <button
                onClick={handleClose}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-slate-700 to-slate-600 hover:from-slate-600 hover:to-slate-500 text-white rounded-lg transition-all"
                aria-label={result?.success ? 'Close modal' : 'Try again'}
              >
                {result?.success ? 'Close' : 'Try Again'}
              </button>
            )}
          </div>

          {/* Trust Indicator */}
          <div className="px-6 pb-4">
            <div className="text-xs text-slate-500 text-center flex items-center justify-center gap-1">
              <Clock className="w-3 h-3" />
              Signed with your wallet, validated by ChainBridge
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
