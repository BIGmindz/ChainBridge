import { useMutation } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, DollarSign, Loader2, Wallet } from "lucide-react";
import React, { useCallback, useMemo, useState } from "react";

import {
    createBuyIntent,
    getCanonicalPrice,
    type BuyIntentResponse,
    type CanonicalPriceQuote,
} from "../../api/marketplace";
import { useDutchPrice } from "../../hooks/useDutchPrice";
import { useMarketplaceWallet } from "../../hooks/useMarketplaceWallet";

type SettlementStatus = "IDLE" | "PENDING" | "SETTLING" | "SETTLED" | "FAILED";

interface ApiError {
  response?: {
    data?: {
      code?: string;
      error_code?: string;
    };
  };
  data?: {
    code?: string;
    error_code?: string;
  };
  code?: string;
  error_code?: string;
}

interface DutchAuctionCardProps {
  listingId: string;
  demoMode?: boolean;
  onSettled?: (intent: BuyIntentResponse) => void;
}

export const DutchAuctionCard: React.FC<DutchAuctionCardProps> = ({
  listingId,
  demoMode = false,
  onSettled,
}) => {
  const [status, setStatus] = useState<SettlementStatus>("IDLE");
  const [error, setError] = useState<string | null>(null);

  const { officialPrice, isDecaying } = useDutchPrice({
    listingId,
    initialPrice: 1000 // Default initial price
  });
  const { wallet, connectWallet } = useMarketplaceWallet();

  const isBusy = status === "PENDING" || status === "SETTLING";
  const isConnected = wallet.isConnected;
  const walletAddress = wallet.address;
  const isDemo = demoMode;

  const priceLabel = useMemo(() => {
    if (!officialPrice) return "—";
    return `$${officialPrice.toFixed(2)}`;
  }, [officialPrice]);

  const handleConnect = useCallback(async () => {
    setError(null);
    try {
      await connectWallet();
    } catch (e) {
      console.error(e);
      setError("Unable to connect wallet. Please try again.");
    }
  }, [connectWallet]);

  const canonicalPriceMutation = useMutation({
    mutationFn: async () => {
      return await getCanonicalPrice(listingId);
    },
  });

  const buyIntentMutation = useMutation({
    mutationFn: async (payload: { quote: CanonicalPriceQuote }) => {
      if (!walletAddress) {
        throw new Error("Wallet not connected");
      }
      return await createBuyIntent(listingId, {
        walletAddress: walletAddress,
        proofNonce: payload.quote.proofNonce,
        clientPrice: payload.quote.price,
      });
    },
  });

  const handleBuyNow = useCallback(async () => {
    if (!isConnected) {
      void handleConnect();
      return;
    }

    setError(null);
    setStatus("PENDING");

    try {
      // Step 1: get authoritative quote from backend
      const canonical = await canonicalPriceMutation.mutateAsync();
      if (!canonical) {
        throw new Error("Failed to get canonical price");
      }

      // Step 2: create buy intent with exact price + nonce
      const intent = await buyIntentMutation.mutateAsync({ quote: canonical });
      if (!intent) {
        throw new Error("Failed to create buy intent");
      }

      setStatus("SETTLING");

      // NOTE: On-chain settlement is handled by the backend worker.
      // Frontend treats returned intent as locked-in.
      setStatus("SETTLED");
      onSettled?.(intent);
    } catch (err: unknown) {
      console.error(err);
      setStatus("FAILED");

      const apiError = err as ApiError;
      const detail = apiError?.response?.data ?? apiError?.data ?? apiError;
      const code = detail?.code ?? detail?.error_code;

      if (code === "QUOTE_MISMATCH") {
        setError("Price changed while you were confirming. We've refreshed to the latest official price.");
      } else if (code === "NONCE_EXPIRED") {
        setError("Your quote expired. Please request a new quote and try again.");
      } else {
        setError("Unable to process purchase at this time. Please try again or contact support.");
      }
    }
  }, [
    isConnected,
    handleConnect,
    canonicalPriceMutation,
    buyIntentMutation,
    onSettled,
  ]);

  const statusBadge = useMemo(() => {
    switch (status) {
      case "PENDING":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-1 text-xs text-amber-300">
            <Loader2 className="h-3 w-3 animate-spin" />
            Locking in price…
          </span>
        );
      case "SETTLING":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-1 text-xs text-amber-300">
            <Loader2 className="h-3 w-3 animate-spin" />
            Submitting settlement…
          </span>
        );
      case "SETTLED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">
            <CheckCircle2 className="h-3 w-3" />
            Purchase complete
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-1 text-xs text-rose-300">
            <AlertCircle className="h-3 w-3" />
            Failed – review details
          </span>
        );
      default:
        return null;
    }
  }, [status]);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-700 bg-slate-900/80 p-6 shadow-lg">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Dutch Auction • Listing #{listingId}
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-3xl font-mono font-bold text-slate-50">
              {priceLabel}
            </span>
            {isDecaying && (
              <span className="text-xs text-amber-300">
                ticking down in real time
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Official ChainBridge price (server-authoritative)
          </p>
        </div>

        <div className="flex flex-col items-end gap-2">
          {statusBadge}
          {isDemo && (
            <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2 py-1 text-[10px] font-medium uppercase text-sky-300">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-300" />
              Demo Wallet
            </span>
          )}
        </div>
      </div>

      {/* Wallet status */}
      <div className="flex items-center justify-between rounded-xl bg-slate-800/70 px-3 py-2 text-xs">
        <div className="flex items-center gap-2 text-slate-300">
          <Wallet className="h-4 w-4 text-slate-400" />
          {isConnected && walletAddress ? (
            <>
              <span>Wallet connected</span>
              <span className="font-mono text-slate-400">
                {walletAddress.slice(0, 6)}…{walletAddress.slice(-4)}
              </span>
            </>
          ) : (
            <span className="text-slate-400">Wallet not connected</span>
          )}
        </div>
        {!isConnected && (
          <button
            type="button"
            onClick={handleConnect}
            className="inline-flex items-center gap-1 rounded-lg bg-slate-50/5 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-50/10"
          >
            <Wallet className="h-3 w-3" />
            Connect Wallet
          </button>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Buy button */}
      <button
        type="button"
        onClick={handleBuyNow}
        disabled={isBusy}
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-md transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-emerald-500/60"
      >
        {isBusy ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing…
          </>
        ) : (
          <>
            <DollarSign className="h-4 w-4" />
            Buy Now at {priceLabel}
          </>
        )}
      </button>

      {/* Footnote */}
      <p className="mt-1 text-[10px] leading-snug text-slate-500">
        Animations are client-side only. Final settlement price and execution
        are validated on the ChainBridge backend before funds move.
      </p>
    </div>
  );
};

export default DutchAuctionCard;
