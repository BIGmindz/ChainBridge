/**
 * useDutchPrice - Client-Side Dutch Auction Price Animation
 *
 * Strategy:
 * - Fetch official price from server every 30s
 * - Between fetches, use requestAnimationFrame to smoothly animate price decay
 * - Creates feeling of "liquid" and "alive" pricing
 * - No jitter or jarring jumps
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { getLivePrice } from "../api/marketplace";
interface UseDutchPriceOptions {
  listingId: string;
  initialPrice: number;
  onPriceDropped?: () => void;  // Callback when price drops (for flash animation)
}

interface DutchPriceState {
  displayPrice: number;           // Animated price for UI
  officialPrice: number;          // Latest from server
  isDecaying: boolean;            // Currently animating decay
  lastUpdate: number;             // Timestamp of last server fetch
  priceDropped: boolean;          // True if price dropped in last 2 seconds
}

/**
 * Hook for real-time Dutch auction price animation
 *
 * Usage:
 * ```tsx
 * const { displayPrice, isDecaying, isLoading } = useDutchPrice({
 *   listingId: listing.id,
 *   initialPrice: listing.startPrice,
 *   onPriceDropped: () => flashRed(),
 * });
 *
 * return <motion.span>{displayPrice.toFixed(0)}</motion.span>;
 * ```
 */
export function useDutchPrice({
  listingId,
  initialPrice,
  onPriceDropped,
}: UseDutchPriceOptions) {
  const [state, setState] = useState<DutchPriceState>({
    displayPrice: initialPrice,
    officialPrice: initialPrice,
    isDecaying: false,
    lastUpdate: Date.now(),
    priceDropped: false,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs to avoid recreating callbacks
  const decayRateRef = useRef(0); // USD per second
  const animationFrameRef = useRef<number | null>(null);
  const lastPriceRef = useRef(initialPrice);
  const fetchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /**
   * Fetch official price from server
   */
  const fetchOfficialPrice = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getLivePrice(listingId);

      if (data) {
        const oldPrice = state.officialPrice;
        const newPrice = data.officialPrice;
        const dropped = newPrice < oldPrice - 1; // Only flag if meaningful drop

        setState((prev) => ({
          ...prev,
          officialPrice: newPrice,
          displayPrice: newPrice,
          lastUpdate: Date.now(),
          priceDropped: dropped,
        }));

        lastPriceRef.current = newPrice;
        decayRateRef.current = data.decayPerSecond;

        if (dropped) {
          onPriceDropped?.();
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch price");
    } finally {
      setIsLoading(false);
    }
  }, [listingId, state.officialPrice, onPriceDropped]);

  /**
   * Animation loop: smooth decay between server updates
   */
  const animateDecay = useCallback(() => {
    setState((prev) => {
      const now = Date.now();
      const elapsedSeconds = (now - prev.lastUpdate) / 1000;

      // Calculate decay based on rate
      const decayedPrice = prev.officialPrice - decayRateRef.current * elapsedSeconds;

      // Don't go below official price (in case rate changed)
      const nextPrice = Math.max(decayedPrice, prev.officialPrice);

      return {
        ...prev,
        displayPrice: Math.round(nextPrice * 100) / 100, // Round to 2 decimals
        isDecaying: true,
      };
    });

    // Continue animation
    animationFrameRef.current = requestAnimationFrame(animateDecay);
  }, []);

  /**
   * Start animation loop and set up server polling
   */
  useEffect(() => {
    // Initial fetch
    fetchOfficialPrice();

    // Set up polling every 30 seconds
    fetchIntervalRef.current = setInterval(() => {
      fetchOfficialPrice();
    }, 30000);

    // Start animation loop
    animationFrameRef.current = requestAnimationFrame(animateDecay);

    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (fetchIntervalRef.current) {
        clearInterval(fetchIntervalRef.current);
      }
    };
  }, [listingId, fetchOfficialPrice, animateDecay]);

  /**
   * Clear "priceDropped" flag after animation plays (2 seconds)
   */
  useEffect(() => {
    if (state.priceDropped) {
      const timer = setTimeout(() => {
        setState((prev) => ({ ...prev, priceDropped: false }));
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [state.priceDropped]);

  return {
    displayPrice: Math.round(state.displayPrice),
    officialPrice: Math.round(state.officialPrice),
    isDecaying: state.isDecaying,
    priceDropped: state.priceDropped,
    isLoading,
    error,
    refetch: fetchOfficialPrice,
  };
}
