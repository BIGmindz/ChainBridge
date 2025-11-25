/**
 * ChainSalvage Marketplace Types
 *
 * Canonical types for the distressed asset marketplace
 * (e.g., damaged containers, off-spec cargo, salvage inventory)
 */

/**
 * Condition score categories for asset quality assessment
 */
export type ConditionRating =
  | "PRISTINE"      // 90-100: No defects, full functionality
  | "GOOD"          // 70-89: Minor cosmetic damage, fully functional
  | "FAIR"          // 50-69: Moderate damage, mostly functional
  | "POOR"          // 30-49: Heavy damage, limited functionality
  | "SALVAGE";      // 0-29: Severely damaged, parts/material value only

/**
 * Commodity type for filtering and categorization
 */
export type CommodityType =
  | "ELECTRONICS"
  | "TEXTILES"
  | "CONSUMABLES"
  | "MACHINERY"
  | "HAZMAT"
  | "PERISHABLES"
  | "MIXED";

/**
 * Listing status in the marketplace
 */
export type ListingStatus =
  | "ACTIVE"        // Available for bidding
  | "AUCTION_LIVE"  // Currently being auctioned
  | "SOLD"          // Sold successfully
  | "CANCELLED";    // No longer available

/**
 * Bid status tracking
 */
export type BidStatus =
  | "PENDING"       // Awaiting blockchain confirmation
  | "ACCEPTED"      // Confirmed
  | "OUTBID"        // Replaced by higher bid
  | "LOST"          // Auction ended without winning
  | "WON";          // Winning bid

/**
 * Core marketplace listing representing a distressed asset
 */
export interface Listing {
  id: string;
  shipmentId: string;              // Link to original ChainBridge shipment
  title: string;                    // "20ft Container Electronics - Water Damaged"
  description: string;              // Detailed description of contents and damage

  // Asset Details
  commodity: CommodityType;
  location: string;                 // "Port of Los Angeles, Pier 9A"
  manifest: string;                 // Manifest hash or summary
  originalValue: number;            // Original declared value (USD)
  estimatedValue: number;           // Appraiser's estimated current value (USD)
  discountPercent: number;          // e.g., -40 for 40% discount

  // Condition & Risk
  conditionScore: number;           // 0-100 numeric score
  conditionRating: ConditionRating; // Category (PRISTINE, GOOD, FAIR, POOR, SALVAGE)
  damageReport: string;             // Description of damage
  riskFactors: string[];            // ["Temperature breach", "Container dent"]

  // Auction & Bidding
  status: ListingStatus;
  startPrice: number;               // Minimum opening bid (USD)
  currentPrice: number;             // Current highest bid (USD)
  currentBidder?: string;           // Wallet address of highest bidder
  buyNowPrice?: number;             // Immediate purchase price if set
  auctionStartAt: string;           // ISO timestamp
  auctionEndAt: string;             // ISO timestamp (countdown reference)

  // Metrics
  bidCount: number;                 // Total bids received
  viewCount: number;                // Total views

  // UI Metadata
  imageUrl?: string;                // Asset preview image (or placeholder if missing)
  createdAt: string;                // ISO timestamp when listing created
  updatedAt: string;                // ISO timestamp when last updated
}

/**
 * Bid placed on a marketplace listing
 */
export interface Bid {
  id: string;
  listingId: string;
  bidderAddress: string;            // Wallet address of bidder
  bidAmount: number;                // Bid amount (USD)
  bidFee: number;                   // Platform fee (USD)
  totalAmount: number;              // bidAmount + bidFee
  status: BidStatus;
  placedAt: string;                 // ISO timestamp
  blockchainTxHash?: string;        // Transaction hash if confirmed
}

/**
 * Bid history entry for timeline/audit trail
 */
export interface BidHistoryEntry {
  id: string;
  listingId: string;
  bidder: string;                   // Bidder wallet or name
  amount: number;                   // Bid amount (USD)
  bidFee: number;                   // Fee for this bid
  totalPaid: number;                // amount + fee
  timestamp: string;                // ISO timestamp
  status: "ACCEPTED" | "OUTBID";   // Whether bid was winning or replaced
}

/**
 * Quick filter criteria for marketplace grid
 */
export interface MarketplaceFilters {
  commodities?: CommodityType[];
  conditionMin?: number;            // Minimum condition score (0-100)
  originPort?: string;              // Filter by origin location
  riskLevelMax?: string;            // "LOW" | "MEDIUM" | "HIGH"
  priceMin?: number;
  priceMax?: number;
  timeRemaining?: "1H" | "4H" | "24H" | "7D"; // Auction time filtering
}

/**
 * Marketplace summary statistics (header ticker)
 */
export interface MarketplaceStats {
  totalListings: number;
  activeBids: number;
  volumeTodayUsd: number;           // Total value of sales today
  justSoldList: Array<{
    title: string;
    finalPrice: number;
    timeAgoMs: number;
  }>;
  lastUpdated: string;              // ISO timestamp
}

/**
 * Watchlist entry for user-saved listings
 */
export interface WatchlistEntry {
  id: string;
  userId: string;
  listingId: string;
  savedAt: string;                  // ISO timestamp
  notifyOnOutbid?: boolean;
  notifyOnSold?: boolean;
}

/**
 * Dutch Auction State - Price continuously decays over time
 */
export interface DutchAuctionState {
  listingId: string;
  startPrice: number;               // Initial price
  reservePrice: number;             // Minimum acceptable price
  decayRatePerHour: number;         // Price drop per hour (USD/h)
  startedAt: string;                // ISO timestamp when auction began
  expiresAt: string;                // ISO timestamp when auction ends
  lastFetchedPrice: number;         // Most recent official price from server
  lastFetchedAt: string;            // When we last hit the API
}

/**
 * Live price with decay information
 */
export interface LivePriceData {
  listingId: string;
  officialPrice: number;            // Server-authoritative price
  calculatedPrice: number;          // Client-calculated with decay
  decayPerSecond: number;           // Derived from hourly rate
  priceDropped: boolean;            // True if price dropped in last 2s
  updatedAt: string;                // ISO timestamp
}
