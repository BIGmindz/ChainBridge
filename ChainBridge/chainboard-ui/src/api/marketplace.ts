/**
 * ChainSalvage Marketplace API Client
 *
 * Handles marketplace-specific operations (Dutch auctions, live pricing, demo controls)
 * Separate from chainpay.ts to keep concerns separated
 */

import type { DutchAuctionState, Listing, LivePriceData } from "../types/marketplace";

const API_BASE = window.location.origin;

/**
 * Canonical price quote with server proof
 */
export interface CanonicalPriceQuote {
  price: number;
  currency: string;
  quotedAt: string;                // ISO timestamp
  proofNonce: string;              // Server-generated nonce for validation
  auctionStateVersion: number;     // Version to detect state changes
}

/**
 * Buy intent response from settlement pipeline
 */
export interface BuyIntentResponse {
  intentId: string;
  status: 'PENDING' | 'CONFIRMED' | 'FAILED' | 'PRICE_CHANGED';
  price: number;                   // Final settled price
  expiresAt: string;               // ISO timestamp when intent expires
  errorCode?: string;              // Error details if status is FAILED
  errorMessage?: string;
}

/**
 * API response wrapper
 */
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

/**
 * GET /api/marketplace/listing/:id/live-price
 * Fetch current official price with decay info for Dutch auction
 * Polls every 30 seconds to get authoritative price from server
 */
export async function getLivePrice(listingId: string): Promise<LivePriceData | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listing/${listingId}/live-price`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data: ApiResponse<LivePriceData> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("getLivePrice failed:", error);
    return null;
  }
}

/**
 * GET /marketplace/listings/:id/price
 * Get canonical price with server proof for settlement
 * This is the official price that will be used for Web3 settlement
 */
export async function getCanonicalPrice(listingId: string): Promise<CanonicalPriceQuote | null> {
  try {
    const response = await fetch(`${API_BASE}/marketplace/listings/${listingId}/price`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data: ApiResponse<CanonicalPriceQuote> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("getCanonicalPrice failed:", error);
    return null;
  }
}

/**
 * GET /api/marketplace/listing/:id
 * Fetch full listing details including Dutch auction state
 */
export async function getListingWithAuction(listingId: string): Promise<Listing & { dutchAuction?: DutchAuctionState } | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listing/${listingId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data: ApiResponse<Listing & { dutchAuction?: DutchAuctionState }> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("getListingWithAuction failed:", error);
    return null;
  }
}

/**
 * POST /marketplace/listings/:id/buy_intents
 * Create a buy intent for Web3 settlement pipeline
 */
export interface CreateBuyIntentPayload {
  walletAddress: string;
  proofNonce: string;              // From canonical price quote
  clientPrice: number;             // Price user saw (for mismatch detection)
}

export async function createBuyIntent(
  listingId: string,
  payload: CreateBuyIntentPayload
): Promise<BuyIntentResponse | null> {
  try {
    const response = await fetch(`${API_BASE}/marketplace/listings/${listingId}/buy_intents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      if (response.status === 409) {
        // Price changed - parse the error response
        const errorData: ApiResponse<BuyIntentResponse> = await response.json();
        return errorData.data || {
          intentId: '',
          status: 'PRICE_CHANGED',
          price: 0,
          expiresAt: new Date().toISOString(),
          errorMessage: 'Price has changed since quote'
        };
      }
      throw new Error(`HTTP ${response.status}`);
    }

    const data: ApiResponse<BuyIntentResponse> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("createBuyIntent failed:", error);
    return null;
  }
}

/**
 * POST /api/marketplace/listing/:id/buy-now-web3
 * Execute buy-now with Web3 signature (legacy - kept for backwards compatibility)
 */
export interface BuyNowPayload {
  buyerAddress: string;
  signature: string;      // From wallet.signMessage()
  priceAtTimeOfClick: number; // Proof of price seen by buyer
}

export async function executeBuyNowWeb3(
  listingId: string,
  payload: BuyNowPayload
): Promise<{ txHash: string; status: string } | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listing/${listingId}/buy-now-web3`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data: ApiResponse<{ txHash: string; status: string }> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("executeBuyNowWeb3 failed:", error);
    return null;
  }
}

/**
 * ============================================================================
 * DEMO CONTROLS (God Mode) - These are HIDDEN from production
 * ============================================================================
 */

/**
 * POST /demo/reset
 * Reset marketplace state (demo only)
 */
export async function demoReset(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/demo/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return response.ok;
  } catch (error) {
    console.error("demoReset failed:", error);
    return false;
  }
}

/**
 * POST /demo/trigger-breach
 * Trigger a simulated environmental breach (temp/humidity) to demo red mode
 */
export interface DemoBreach {
  listingId: string;
  breachType: "TEMPERATURE" | "HUMIDITY" | "CONTAMINATION";
  severity: "WARNING" | "CRITICAL";
}

export async function demoTriggerBreach(breach: DemoBreach): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/demo/trigger-breach`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(breach),
    });
    return response.ok;
  } catch (error) {
    console.error("demoTriggerBreach failed:", error);
    return false;
  }
}

/**
 * POST /demo/warp-time
 * Fast-forward the auction clock (for demo)
 * Price decays based on elapsed time
 */
export interface DemoWarpTime {
  listingId: string;
  hoursToAdvance: number; // e.g., 1, 6, 24
}

export async function demoWarpTime(warp: DemoWarpTime): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/demo/warp-time`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(warp),
    });
    return response.ok;
  } catch (error) {
    console.error("demoWarpTime failed:", error);
    return false;
  }
}

export default {
  // Live pricing
  getLivePrice,
  getListingWithAuction,
  getCanonicalPrice,

  // Web3 settlement
  createBuyIntent,
  executeBuyNowWeb3,

  // Demo controls
  demoReset,
  demoTriggerBreach,
  demoWarpTime,
};
