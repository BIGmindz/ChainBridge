/**
 * ChainPay & ChainStake API Client
 *
 * Handles API calls for:
 * - Payment reconciliation (ChainAudit fuzzy logic)
 * - Staking positions (ChainStake liquidity management)
 * - Collateral monitoring and breach alerts
 *
 * Base URL: Determined by window.location.origin (same domain)
 */

import type {
    AuditTrace,
    CollateralBreach,
    ReconciliationResult,
    StakingPosition,
    TreasurySummary,
} from "../types/chainbridge";
import type {
    Bid,
    BidHistoryEntry,
    Listing,
    MarketplaceStats,
} from "../types/marketplace";

const API_BASE = window.location.origin;

/**
 * API response wrapper with success/error handling
 */
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

/**
 * Error handler for API calls
 */
function handleError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Unknown error occurred";
}

// =============================================================================
// RECONCILIATION / CHAINAUDIT ENDPOINTS
// =============================================================================

/**
 * GET /api/audit/pending
 * Fetch pending reconciliation decisions waiting for operator review
 */
export async function getPendingReconciliations(): Promise<ReconciliationResult[]> {
  try {
    const response = await fetch(`${API_BASE}/api/audit/pending`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<ReconciliationResult[]> = await response.json();
    return data.data || [];
  } catch (error) {
    console.error("getPendingReconciliations failed:", handleError(error));
    return [];
  }
}

/**
 * GET /api/audit/history/:shipmentId
 * Fetch reconciliation history for a specific shipment
 */
export async function getReconciliationHistory(shipmentId: string): Promise<AuditTrace[]> {
  try {
    const response = await fetch(`${API_BASE}/api/audit/history/${shipmentId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<AuditTrace[]> = await response.json();
    return data.data || [];
  } catch (error) {
    console.error("getReconciliationHistory failed:", handleError(error));
    return [];
  }
}

/**
 * POST /api/audit/approve
 * Approve a reconciliation decision and trigger payment
 */
export async function approveReconciliation(
  reconciliationId: string,
  options?: { adjusted?: boolean; reason?: string }
): Promise<ReconciliationResult | null> {
  try {
    const response = await fetch(`${API_BASE}/api/audit/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reconciliation_id: reconciliationId,
        adjusted: options?.adjusted || false,
        reason: options?.reason || "Operator approved via Bloomberg UI",
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<ReconciliationResult> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("approveReconciliation failed:", handleError(error));
    return null;
  }
}

/**
 * POST /api/audit/reject
 * Reject a reconciliation decision (requires manual review)
 */
export async function rejectReconciliation(
  reconciliationId: string,
  reason: string
): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/audit/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reconciliation_id: reconciliationId,
        reason,
      }),
    });

    return response.ok;
  } catch (error) {
    console.error("rejectReconciliation failed:", handleError(error));
    return false;
  }
}

// =============================================================================
// STAKING / CHAINSTAKE ENDPOINTS
// =============================================================================

/**
 * GET /api/staking/positions
 * Fetch all active staking positions for current wallet
 */
export async function getStakingPositions(
  walletAddress?: string
): Promise<StakingPosition[]> {
  try {
    const query = walletAddress ? `?wallet=${encodeURIComponent(walletAddress)}` : "";
    const response = await fetch(`${API_BASE}/api/staking/positions${query}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<StakingPosition[]> = await response.json();
    return data.data || [];
  } catch (error) {
    console.error("getStakingPositions failed:", handleError(error));
    return [];
  }
}

/**
 * GET /api/staking/treasury-summary
 * Fetch aggregate treasury metrics (TVS, liquidity, yield, health)
 */
export async function getTreasurySummary(
  walletAddress?: string
): Promise<TreasurySummary | null> {
  try {
    const query = walletAddress ? `?wallet=${encodeURIComponent(walletAddress)}` : "";
    const response = await fetch(`${API_BASE}/api/staking/treasury-summary${query}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<TreasurySummary> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("getTreasurySummary failed:", handleError(error));
    return null;
  }
}

/**
 * POST /api/staking/stake-inventory
 * Create a new staking position (lock collateral for a shipment)
 */
export interface StakeInventoryPayload {
  shipmentId: string;
  collateralTokenId: string; // ERC721 or ERC20 token ID
  collateralAmount: number; // Amount to stake (wei or smallest unit)
  loanAmount: number; // Loan amount in USD
  loanTermDays?: number; // Loan duration (default 30 days)
  riskProfile?: "CONSERVATIVE" | "MODERATE" | "AGGRESSIVE"; // Risk tolerance
}

export async function stakeInventory(payload: StakeInventoryPayload): Promise<StakingPosition | null> {
  try {
    const response = await fetch(`${API_BASE}/api/staking/stake-inventory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<StakingPosition> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("stakeInventory failed:", handleError(error));
    return null;
  }
}

/**
 * GET /api/staking/critical-positions
 * Fetch positions with high liquidation risk (LTV > 80%)
 */
export async function getCriticalPositions(
  walletAddress?: string
): Promise<CollateralBreach[]> {
  try {
    const query = walletAddress ? `?wallet=${encodeURIComponent(walletAddress)}` : "";
    const response = await fetch(`${API_BASE}/api/staking/critical-positions${query}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<CollateralBreach[]> = await response.json();
    return data.data || [];
  } catch (error) {
    console.error("getCriticalPositions failed:", handleError(error));
    return [];
  }
}

// =============================================================================
// LIQUIDATION / FLASH REPAY ENDPOINTS
// =============================================================================

/**
 * POST /api/staking/flash-repay
 * Perform a flash repayment to restore position health
 */
export async function flashRepay(positionId: string, repayAmount?: number): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/staking/flash-repay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        position_id: positionId,
        repay_amount: repayAmount, // If not provided, backend calculates required amount
      }),
    });

    return response.ok;
  } catch (error) {
    console.error("flashRepay failed:", handleError(error));
    return false;
  }
}

/**
 * POST /api/staking/liquidate
 * Liquidate a position (abandon collateral, trigger sale)
 */
export async function liquidatePosition(positionId: string, reason?: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/staking/liquidate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        position_id: positionId,
        reason: reason || "Operator initiated liquidation via Bloomberg UI",
      }),
    });

    return response.ok;
  } catch (error) {
    console.error("liquidatePosition failed:", handleError(error));
    return false;
  }
}

// =============================================================================
// LIQUIDITY SUMMARY HELPER
// =============================================================================

/**
 * Helper function to fetch complete treasury view
 * Returns positions + summary in one call
 */
export async function getLiquiditySummary(walletAddress?: string): Promise<{
  positions: StakingPosition[];
  summary: TreasurySummary | null;
  criticalPositions: CollateralBreach[];
}> {
  try {
    const [positions, summary, criticalPositions] = await Promise.all([
      getStakingPositions(walletAddress),
      getTreasurySummary(walletAddress),
      getCriticalPositions(walletAddress),
    ]);

    return { positions, summary, criticalPositions };
  } catch (error) {
    console.error("getLiquiditySummary failed:", handleError(error));
    return { positions: [], summary: null, criticalPositions: [] };
  }
}

// =============================================================================
// CHAINSALVAGE MARKETPLACE ENDPOINTS
// =============================================================================

/**
 * GET /api/marketplace/listings
 * Fetch all active marketplace listings with optional filtering
 */
export async function fetchListings(params?: {
  commodity?: string;
  condition_min?: number;
  location?: string;
  limit?: number;
  offset?: number;
}): Promise<Listing[]> {
  try {
    const queryParams = new URLSearchParams();
    if (params?.commodity) queryParams.append("commodity", params.commodity);
    if (params?.condition_min !== undefined) queryParams.append("condition_min", params.condition_min.toString());
    if (params?.location) queryParams.append("location", params.location);
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.offset) queryParams.append("offset", params.offset.toString());

    const response = await fetch(`${API_BASE}/api/marketplace/listings?${queryParams}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<Listing[]> = await response.json();
    return data.data || [];
  } catch (error) {
    console.error("fetchListings failed:", handleError(error));
    return [];
  }
}

/**
 * GET /api/marketplace/listings/:listingId
 * Fetch single listing with full details
 */
export async function fetchListingDetail(listingId: string): Promise<Listing | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listings/${listingId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<Listing> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("fetchListingDetail failed:", handleError(error));
    return null;
  }
}

/**
 * GET /api/marketplace/listings/:listingId/bids
 * Fetch bid history for a specific listing
 */
export async function fetchBidHistory(listingId: string): Promise<BidHistoryEntry[]> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listings/${listingId}/bids`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<BidHistoryEntry[]> = await response.json();
    return data.data || [];
  } catch (error) {
    console.error("fetchBidHistory failed:", handleError(error));
    return [];
  }
}

/**
 * POST /api/marketplace/listings/:listingId/bid
 * Submit a bid on a listing
 */
export interface BidPayload {
  bidAmount: number;
  bidderAddress: string;
  bidderEmail?: string;
}

export async function submitBid(listingId: string, payload: BidPayload): Promise<Bid | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listings/${listingId}/bid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<Bid> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("submitBid failed:", handleError(error));
    return null;
  }
}

/**
 * POST /api/marketplace/listings/:listingId/buy-now
 * Execute immediate purchase at buyNowPrice
 */
export interface BuyNowPayload {
  buyerAddress: string;
  buyerEmail?: string;
}

export async function executeBuyNow(listingId: string, payload: BuyNowPayload): Promise<Bid | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/listings/${listingId}/buy-now`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<Bid> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("executeBuyNow failed:", handleError(error));
    return null;
  }
}

/**
 * GET /api/marketplace/stats
 * Fetch marketplace summary (volume, just sold list, etc.)
 */
export async function fetchMarketplaceStats(): Promise<MarketplaceStats | null> {
  try {
    const response = await fetch(`${API_BASE}/api/marketplace/stats`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: ApiResponse<MarketplaceStats> = await response.json();
    return data.data || null;
  } catch (error) {
    console.error("fetchMarketplaceStats failed:", handleError(error));
    return null;
  }
}


export default {
  // ChainAudit
  getPendingReconciliations,
  getReconciliationHistory,
  approveReconciliation,
  rejectReconciliation,

  // ChainStake
  getStakingPositions,
  getTreasurySummary,
  stakeInventory,
  getCriticalPositions,

  // Liquidation
  flashRepay,
  liquidatePosition,

  // Aggregates
  getLiquiditySummary,

  // ChainSalvage Marketplace
  fetchListings,
  fetchListingDetail,
  fetchBidHistory,
  submitBid,
  executeBuyNow,
  fetchMarketplaceStats,
};
