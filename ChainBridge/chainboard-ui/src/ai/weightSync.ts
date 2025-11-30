/**
 * MAGGIE PAC-004 — Weight Layering, KPIs & Sync Infrastructure
 * ============================================================
 * Close the loop: blend global + local weights, measure KPIs, persist.
 *
 * Design Principles:
 * 1. Weight layering: effective = normalize(α·global + β·local)
 * 2. Three-tier sync: localStorage → Backend (ChainIQ) → Supabase
 * 3. KPI tracking: CTR, Hit@N, Time-to-Preset
 * 4. All data exportable for auditing and ML training
 *
 * Architecture:
 * - Global weights: Profile defaults (conservative/moderate/aggressive)
 * - Local weights: User-specific adjustments from PAC-003 feedback
 * - Effective weights: Blended result used for scoring
 *
 * @module ai/weightSync
 */

import type { ScoringWeights, RecommendationProfile } from "./presetRecommender";
import { getDefaultWeights } from "./presetRecommender";
import type { LearnedWeights, FeedbackExport, PresetFeedbackStats } from "./feedbackTracker";
import { getLearnedWeights, exportFeedbackData, resetFeedbackData } from "./feedbackTracker";

// =============================================================================
// TYPES
// =============================================================================

/**
 * Layer blending parameters.
 * effective_weights = normalize(alpha * global + beta * local)
 */
export interface LayerBlendConfig {
  alpha: number;  // Global weight influence [0, 1]
  beta: number;   // Local weight influence [0, 1]
}

/**
 * Default blend: 70% global, 30% local.
 * Conservative start — local learning needs evidence before dominating.
 */
export const DEFAULT_BLEND_CONFIG: LayerBlendConfig = {
  alpha: 0.7,
  beta: 0.3,
};

/**
 * Effective weights after blending.
 */
export interface EffectiveWeights {
  profile: RecommendationProfile;
  globalWeights: ScoringWeights;
  localWeights: ScoringWeights;
  effectiveWeights: ScoringWeights;
  blendConfig: LayerBlendConfig;
  localAdjustmentCount: number;
  computedAt: string;
}

/**
 * KPI metrics tracked per session/user.
 */
export interface KPIMetrics {
  // Click-through rate: selections / impressions
  ctr: number;
  impressions: number;
  selections: number;

  // Hit@N: was selected preset in top N recommendations?
  hitAt1: number;     // Selections from rank 1
  hitAt3: number;     // Selections from rank 1-3
  totalSelections: number;

  // Time-to-preset: average time from recommendations shown to selection (ms)
  avgTimeToPresetMs: number;
  timeToPresetSamples: number[];

  // Session metadata
  sessionStart: string;
  lastUpdated: string;
  sessionId: string;
}

/**
 * Sync state for persistence layer.
 */
export interface SyncState {
  lastLocalStorageSync: string | null;
  lastBackendSync: string | null;
  lastSupabaseSync: string | null;
  pendingChanges: number;
  syncErrors: SyncError[];
}

/**
 * Sync error record.
 */
export interface SyncError {
  timestamp: string;
  layer: "localStorage" | "backend" | "supabase";
  error: string;
  retryCount: number;
}

/**
 * Full analytics export for PAC-004.
 */
export interface AnalyticsExport {
  exportedAt: string;
  version: "1.0";

  // Per-preset data
  presets: {
    presetId: string;
    posterior: number;       // Bayesian posterior
    clicks: number;          // timesSelected
    votes: {
      up: number;
      down: number;
    };
  }[];

  // Per-profile data
  profiles: {
    profile: RecommendationProfile;
    weights: ScoringWeights;
    interactionCount: number;
  }[];

  // KPI summary
  kpis: KPIMetrics;

  // Raw feedback data (from PAC-003)
  feedbackExport: FeedbackExport;
}

/**
 * Sync hook callback types.
 */
export type SyncCallback = (data: AnalyticsExport) => Promise<void>;
export type SyncErrorCallback = (error: SyncError) => void;

// =============================================================================
// CONFIGURATION
// =============================================================================

const SYNC_CONFIG = {
  // localStorage key prefix
  STORAGE_PREFIX: "maggie_pac004_",

  // Sync intervals (ms)
  LOCAL_STORAGE_DEBOUNCE_MS: 1000,
  BACKEND_SYNC_INTERVAL_MS: 60_000,

  // Retry config
  MAX_RETRY_COUNT: 3,
  RETRY_DELAY_MS: 5000,

  // KPI tracking
  MAX_TIME_SAMPLES: 100,

  // Cache TTL
  EFFECTIVE_WEIGHTS_CACHE_TTL_MS: 30_000,
} as const;

// =============================================================================
// IN-MEMORY STATE
// =============================================================================

/** Current sync state */
let syncState: SyncState = {
  lastLocalStorageSync: null,
  lastBackendSync: null,
  lastSupabaseSync: null,
  pendingChanges: 0,
  syncErrors: [],
};

/** KPI metrics for current session */
let kpiMetrics: KPIMetrics = createInitialKPIMetrics();

/** Recommendation impression timestamps (for time-to-preset) */
const impressionTimestamps = new Map<string, number>();

/** Cached effective weights */
const effectiveWeightsCache = new Map<RecommendationProfile, { weights: EffectiveWeights; timestamp: number }>();

/** Registered sync hooks */
const backendSyncHooks: SyncCallback[] = [];
const supabaseSyncHooks: SyncCallback[] = [];
const errorHooks: SyncErrorCallback[] = [];

/** localStorage debounce timer */
let localStorageDebounceTimer: ReturnType<typeof setTimeout> | null = null;

// =============================================================================
// WEIGHT LAYERING — Core Algorithm
// =============================================================================

/**
 * Blend global and local weights.
 * effective = normalize(alpha * global + beta * local)
 *
 * @param global - Profile default weights
 * @param local - User-adjusted weights from feedback
 * @param config - Blend parameters (alpha, beta)
 * @returns Blended weights (normalized to sum to 1)
 */
export function blendWeights(
  global: ScoringWeights,
  local: ScoringWeights,
  config: LayerBlendConfig = DEFAULT_BLEND_CONFIG
): ScoringWeights {
  const { alpha, beta } = config;

  // Weighted combination
  const blended = {
    usage: alpha * global.usage + beta * local.usage,
    recency: alpha * global.recency + beta * local.recency,
    tags: alpha * global.tags + beta * local.tags,
    category: alpha * global.category + beta * local.category,
  };

  // Normalize to sum to 1
  return normalizeWeights(blended);
}

/**
 * Normalize weights to sum to 1.0.
 */
function normalizeWeights(weights: ScoringWeights): ScoringWeights {
  const sum = weights.usage + weights.recency + weights.tags + weights.category;
  if (sum <= 0) {
    return { usage: 0.25, recency: 0.25, tags: 0.25, category: 0.25 };
  }
  return {
    usage: weights.usage / sum,
    recency: weights.recency / sum,
    tags: weights.tags / sum,
    category: weights.category / sum,
  };
}

/**
 * Get effective weights for a profile, blending global + local.
 * Uses caching to avoid recomputation.
 *
 * @param profile - Recommendation profile
 * @param blendConfig - Optional custom blend config
 * @returns EffectiveWeights with full breakdown
 */
export function getEffectiveWeights(
  profile: RecommendationProfile,
  blendConfig: LayerBlendConfig = DEFAULT_BLEND_CONFIG
): EffectiveWeights {
  // Check cache
  const cached = effectiveWeightsCache.get(profile);
  const now = Date.now();
  if (cached && (now - cached.timestamp) < SYNC_CONFIG.EFFECTIVE_WEIGHTS_CACHE_TTL_MS) {
    return cached.weights;
  }

  // Get global (profile defaults)
  const globalWeights = getDefaultWeights(profile);

  // Get local (learned from feedback)
  const learned = getLearnedWeights(profile, globalWeights);
  const localWeights = learned.adjustedWeights;

  // Blend
  const effectiveWeights = blendWeights(globalWeights, localWeights, blendConfig);

  const result: EffectiveWeights = {
    profile,
    globalWeights,
    localWeights,
    effectiveWeights,
    blendConfig,
    localAdjustmentCount: learned.totalAdjustments,
    computedAt: new Date().toISOString(),
  };

  // Cache
  effectiveWeightsCache.set(profile, { weights: result, timestamp: now });

  return result;
}

/**
 * Invalidate effective weights cache (call after feedback).
 */
export function invalidateWeightsCache(profile?: RecommendationProfile): void {
  if (profile) {
    effectiveWeightsCache.delete(profile);
  } else {
    effectiveWeightsCache.clear();
  }
}

// =============================================================================
// KPI TRACKING
// =============================================================================

/**
 * Create initial KPI metrics for a session.
 */
function createInitialKPIMetrics(): KPIMetrics {
  const now = new Date().toISOString();
  return {
    ctr: 0,
    impressions: 0,
    selections: 0,
    hitAt1: 0,
    hitAt3: 0,
    totalSelections: 0,
    avgTimeToPresetMs: 0,
    timeToPresetSamples: [],
    sessionStart: now,
    lastUpdated: now,
    sessionId: generateSessionId(),
  };
}

/**
 * Generate a unique session ID.
 */
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Record that recommendations were shown (impression).
 * Call this when recommendations are displayed to user.
 *
 * @param presetIds - IDs of presets shown
 */
export function recordImpression(presetIds: string[]): void {
  const now = Date.now();
  kpiMetrics.impressions++;
  kpiMetrics.lastUpdated = new Date().toISOString();

  // Store timestamp for time-to-preset calculation
  presetIds.forEach((id) => {
    impressionTimestamps.set(id, now);
  });

  // Trigger debounced localStorage sync
  queueLocalStorageSync();
}

/**
 * Record a preset selection with rank info.
 * Updates CTR, Hit@N, and Time-to-Preset KPIs.
 *
 * @param presetId - Selected preset ID
 * @param rank - Position in recommendations (1-indexed)
 */
export function recordSelection(presetId: string, rank: number): void {
  const now = Date.now();

  kpiMetrics.selections++;
  kpiMetrics.totalSelections++;

  // Update CTR
  kpiMetrics.ctr = kpiMetrics.impressions > 0
    ? kpiMetrics.selections / kpiMetrics.impressions
    : 0;

  // Update Hit@N
  if (rank === 1) {
    kpiMetrics.hitAt1++;
  }
  if (rank <= 3) {
    kpiMetrics.hitAt3++;
  }

  // Calculate time-to-preset
  const impressionTime = impressionTimestamps.get(presetId);
  if (impressionTime) {
    const elapsed = now - impressionTime;
    kpiMetrics.timeToPresetSamples.push(elapsed);

    // Keep bounded
    if (kpiMetrics.timeToPresetSamples.length > SYNC_CONFIG.MAX_TIME_SAMPLES) {
      kpiMetrics.timeToPresetSamples.shift();
    }

    // Update average
    kpiMetrics.avgTimeToPresetMs =
      kpiMetrics.timeToPresetSamples.reduce((a, b) => a + b, 0) /
      kpiMetrics.timeToPresetSamples.length;

    impressionTimestamps.delete(presetId);
  }

  kpiMetrics.lastUpdated = new Date().toISOString();

  // Trigger sync
  queueLocalStorageSync();
}

/**
 * Get current KPI metrics.
 */
export function getKPIMetrics(): KPIMetrics {
  return { ...kpiMetrics, timeToPresetSamples: [...kpiMetrics.timeToPresetSamples] };
}

/**
 * Get Hit@N rates.
 */
export function getHitRates(): { hitRate1: number; hitRate3: number } {
  const total = kpiMetrics.totalSelections;
  if (total === 0) {
    return { hitRate1: 0, hitRate3: 0 };
  }
  return {
    hitRate1: kpiMetrics.hitAt1 / total,
    hitRate3: kpiMetrics.hitAt3 / total,
  };
}

/**
 * Reset KPI metrics (new session).
 */
export function resetKPIMetrics(): void {
  kpiMetrics = createInitialKPIMetrics();
  impressionTimestamps.clear();
}

// =============================================================================
// SYNC INFRASTRUCTURE — Three-Tier Persistence
// =============================================================================

/**
 * Queue a debounced localStorage sync.
 */
function queueLocalStorageSync(): void {
  syncState.pendingChanges++;

  if (localStorageDebounceTimer) {
    clearTimeout(localStorageDebounceTimer);
  }

  localStorageDebounceTimer = setTimeout(() => {
    syncToLocalStorage();
  }, SYNC_CONFIG.LOCAL_STORAGE_DEBOUNCE_MS);
}

/**
 * Sync data to localStorage.
 */
export function syncToLocalStorage(): void {
  if (typeof window === "undefined" || !window.localStorage) {
    recordSyncError("localStorage", "localStorage not available");
    return;
  }

  try {
    // Store KPIs
    window.localStorage.setItem(
      `${SYNC_CONFIG.STORAGE_PREFIX}kpis`,
      JSON.stringify(kpiMetrics)
    );

    // Store effective weights per profile
    const profiles: RecommendationProfile[] = ["conservative", "moderate", "aggressive"];
    profiles.forEach((profile) => {
      const effective = getEffectiveWeights(profile);
      window.localStorage.setItem(
        `${SYNC_CONFIG.STORAGE_PREFIX}weights_${profile}`,
        JSON.stringify(effective)
      );
    });

    // Store last sync timestamp
    const now = new Date().toISOString();
    window.localStorage.setItem(
      `${SYNC_CONFIG.STORAGE_PREFIX}lastSync`,
      now
    );

    syncState.lastLocalStorageSync = now;
    syncState.pendingChanges = 0;

  } catch (error) {
    recordSyncError("localStorage", String(error));
  }
}

/**
 * Load data from localStorage.
 */
export function loadFromLocalStorage(): boolean {
  if (typeof window === "undefined" || !window.localStorage) {
    return false;
  }

  try {
    // Load KPIs
    const kpisJson = window.localStorage.getItem(`${SYNC_CONFIG.STORAGE_PREFIX}kpis`);
    if (kpisJson) {
      const loaded = JSON.parse(kpisJson) as KPIMetrics;
      // Merge with current session (keep session ID)
      kpiMetrics = {
        ...loaded,
        sessionId: kpiMetrics.sessionId,
        sessionStart: kpiMetrics.sessionStart,
      };
    }

    return true;
  } catch (error) {
    recordSyncError("localStorage", `Load error: ${String(error)}`);
    return false;
  }
}

/**
 * Register a backend sync hook.
 * Called when data should be synced to ChainIQ backend.
 */
export function registerBackendSyncHook(callback: SyncCallback): void {
  backendSyncHooks.push(callback);
}

/**
 * Register a Supabase sync hook.
 * Called for long-term persistence.
 */
export function registerSupabaseSyncHook(callback: SyncCallback): void {
  supabaseSyncHooks.push(callback);
}

/**
 * Register an error callback.
 */
export function registerErrorHook(callback: SyncErrorCallback): void {
  errorHooks.push(callback);
}

/**
 * Trigger backend sync (ChainIQ).
 */
export async function syncToBackend(): Promise<void> {
  if (backendSyncHooks.length === 0) {
    return; // No hooks registered
  }

  const data = buildAnalyticsExport();

  for (const hook of backendSyncHooks) {
    try {
      await hook(data);
    } catch (error) {
      recordSyncError("backend", String(error));
    }
  }

  syncState.lastBackendSync = new Date().toISOString();
}

/**
 * Trigger Supabase sync.
 */
export async function syncToSupabase(): Promise<void> {
  if (supabaseSyncHooks.length === 0) {
    return; // No hooks registered
  }

  const data = buildAnalyticsExport();

  for (const hook of supabaseSyncHooks) {
    try {
      await hook(data);
    } catch (error) {
      recordSyncError("supabase", String(error));
    }
  }

  syncState.lastSupabaseSync = new Date().toISOString();
}

/**
 * Record a sync error.
 */
function recordSyncError(layer: SyncError["layer"], error: string): void {
  const syncError: SyncError = {
    timestamp: new Date().toISOString(),
    layer,
    error,
    retryCount: 0,
  };

  syncState.syncErrors.push(syncError);

  // Keep bounded
  if (syncState.syncErrors.length > 100) {
    syncState.syncErrors.shift();
  }

  // Notify error hooks
  errorHooks.forEach((hook) => {
    try {
      hook(syncError);
    } catch {
      // Ignore errors in error handlers
    }
  });
}

/**
 * Get current sync state.
 */
export function getSyncState(): SyncState {
  return { ...syncState, syncErrors: [...syncState.syncErrors] };
}

// =============================================================================
// ANALYTICS EXPORT
// =============================================================================

/**
 * Build full analytics export.
 */
export function buildAnalyticsExport(): AnalyticsExport {
  const feedbackExport = exportFeedbackData();

  // Per-preset data
  const presets = feedbackExport.presetStats.map((stats: PresetFeedbackStats) => ({
    presetId: stats.presetId,
    posterior: stats.combinedScore,
    clicks: stats.timesSelected,
    votes: {
      up: stats.upvotes,
      down: stats.downvotes,
    },
  }));

  // Per-profile data
  const profiles: RecommendationProfile[] = ["conservative", "moderate", "aggressive"];
  const profileData = profiles.map((profile) => {
    const effective = getEffectiveWeights(profile);
    const learned = feedbackExport.learnedWeights.find(
      (lw: LearnedWeights) => lw.profile === profile
    );
    return {
      profile,
      weights: effective.effectiveWeights,
      interactionCount: learned?.totalAdjustments ?? 0,
    };
  });

  return {
    exportedAt: new Date().toISOString(),
    version: "1.0",
    presets,
    profiles: profileData,
    kpis: getKPIMetrics(),
    feedbackExport,
  };
}

/**
 * Export analytics to JSON string.
 */
export function exportAnalyticsJSON(): string {
  return JSON.stringify(buildAnalyticsExport(), null, 2);
}

// =============================================================================
// RESET & TESTING UTILITIES
// =============================================================================

/**
 * Reset all PAC-004 state (for testing).
 */
export function resetWeightSyncState(): void {
  syncState = {
    lastLocalStorageSync: null,
    lastBackendSync: null,
    lastSupabaseSync: null,
    pendingChanges: 0,
    syncErrors: [],
  };

  kpiMetrics = createInitialKPIMetrics();
  impressionTimestamps.clear();
  effectiveWeightsCache.clear();

  // Clear registered hooks
  backendSyncHooks.length = 0;
  supabaseSyncHooks.length = 0;
  errorHooks.length = 0;

  if (localStorageDebounceTimer) {
    clearTimeout(localStorageDebounceTimer);
    localStorageDebounceTimer = null;
  }

  // Also reset PAC-003 feedback data
  resetFeedbackData();
}

/**
 * Clear localStorage data (for testing).
 */
export function clearLocalStorage(): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }

  const keysToRemove: string[] = [];
  for (let i = 0; i < window.localStorage.length; i++) {
    const key = window.localStorage.key(i);
    if (key?.startsWith(SYNC_CONFIG.STORAGE_PREFIX)) {
      keysToRemove.push(key);
    }
  }

  keysToRemove.forEach((key) => {
    window.localStorage.removeItem(key);
  });
}

/**
 * Get internal state for testing.
 */
export function getInternalState(): {
  impressionCount: number;
  cachedProfileCount: number;
  pendingChanges: number;
} {
  return {
    impressionCount: impressionTimestamps.size,
    cachedProfileCount: effectiveWeightsCache.size,
    pendingChanges: syncState.pendingChanges,
  };
}
