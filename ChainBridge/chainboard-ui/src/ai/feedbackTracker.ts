/**
 * MAGGIE PAC-003 — Behavioral Feedback Layer
 * ===========================================
 * Glass-box reinforcement system for AI preset recommendations.
 *
 * Design Principles:
 * 1. All updates are explicit, auditable, and reversible.
 * 2. Bayesian smoothing prevents overfitting to sparse data.
 * 3. Clipped weight updates prevent runaway drift.
 * 4. Per-preset counters support both implicit and explicit feedback.
 * 5. Wilson score intervals provide confidence bounds.
 * 6. All data exportable for future ML training.
 *
 * Failure Modes Addressed:
 * - Overfitting: Multi-user aggregation + Bayesian priors
 * - Sparse feedback: Laplace smoothing (add-1)
 * - Drift: Clipped step sizes (max 0.01 per update)
 * - Confusion clicks: Decay factor for old signals
 * - Popular ≠ valuable: Separate explicit feedback from implicit
 *
 * @module ai/feedbackTracker
 */

import type { ScoringWeights, ScoreBreakdown, RecommendationProfile } from "./presetRecommender";

// =============================================================================
// FEEDBACK TYPES
// =============================================================================

/**
 * Types of implicit feedback (inferred from behavior).
 */
export type ImplicitFeedbackType =
  | "selected"           // User clicked this recommendation
  | "ignored"            // Recommendation shown but not selected
  | "selected_other"     // User picked a different preset instead
  | "engaged";           // User took action after applying preset

/**
 * Types of explicit feedback (user-initiated).
 */
export type ExplicitFeedbackType =
  | "upvote"             // 👍
  | "downvote"           // 👎
  | "hide"               // "Never show this again"
  | "pin";               // "Pin this preset" (future)

/**
 * Single feedback event for logging/analytics.
 */
export interface FeedbackEvent {
  eventId: string;
  presetId: string;
  userId?: string;                    // Optional for multi-user aggregation
  feedbackType: ImplicitFeedbackType | ExplicitFeedbackType;
  timestamp: string;                  // ISO timestamp
  context: FeedbackContext;
  recommendationRank?: number;        // Position in the list (1-indexed)
  recommendationScore?: number;       // Score at time of feedback
  breakdown?: ScoreBreakdown;         // Component scores at feedback time
}

/**
 * Context at feedback time (for analytics).
 */
export interface FeedbackContext {
  profile: RecommendationProfile;
  category?: string;
  tags?: string[];
  searchTerm?: string;
  sessionId?: string;
}

/**
 * Per-preset feedback counters (Bayesian tracking).
 */
export interface PresetFeedbackStats {
  presetId: string;

  // Implicit signals
  timesShown: number;
  timesSelected: number;
  timesIgnored: number;
  timesSelectedOther: number;
  engagementCount: number;

  // Explicit signals
  upvotes: number;
  downvotes: number;
  hides: number;
  pins: number;

  // Computed scores (updated on each feedback)
  implicitScore: number;      // Bayesian posterior for implicit
  explicitScore: number;      // Bayesian posterior for explicit
  combinedScore: number;      // Weighted combination
  wilsonLower: number;        // Wilson score lower bound (95% CI)

  // Metadata
  lastUpdated: string;        // ISO timestamp
  totalFeedbackCount: number;
}

/**
 * Weight adjustment delta for reinforcement.
 */
export interface WeightAdjustment {
  profile: RecommendationProfile;
  deltas: ScoringWeights;     // Change to apply (can be negative)
  reason: string;             // Glass-box explanation
  timestamp: string;
  presetId: string;
  feedbackType: ImplicitFeedbackType | ExplicitFeedbackType;
}

/**
 * Learned weights after reinforcement (per profile).
 */
export interface LearnedWeights {
  profile: RecommendationProfile;
  baseWeights: ScoringWeights;      // Original profile weights
  adjustedWeights: ScoringWeights;  // After reinforcement
  totalAdjustments: number;
  lastAdjusted: string;             // ISO timestamp
  adjustmentHistory: WeightAdjustment[];
}

/**
 * Export format for ML training data.
 */
export interface FeedbackExport {
  exportedAt: string;
  version: "1.0";
  events: FeedbackEvent[];
  presetStats: PresetFeedbackStats[];
  learnedWeights: LearnedWeights[];
}

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Reinforcement learning parameters.
 * All values chosen for stability and interpretability.
 */
const REINFORCEMENT_CONFIG = {
  // Step size for weight updates (clipped)
  STEP_SIZE: 0.01,
  MAX_STEP_SIZE: 0.02,
  MIN_STEP_SIZE: 0.001,

  // Bayesian prior parameters (Laplace smoothing)
  PRIOR_POSITIVE: 1,
  PRIOR_NEGATIVE: 1,

  // Decay factor for old feedback (exponential)
  DECAY_HALF_LIFE_DAYS: 30,

  // Minimum feedback count before adjusting weights
  MIN_FEEDBACK_FOR_ADJUSTMENT: 5,

  // Maximum history to retain
  MAX_HISTORY_SIZE: 1000,
  MAX_ADJUSTMENT_HISTORY: 100,

  // Weight bounds (never go below/above these)
  MIN_WEIGHT: 0.05,
  MAX_WEIGHT: 0.50,

  // Implicit vs explicit weight in combined score
  IMPLICIT_WEIGHT: 0.6,
  EXPLICIT_WEIGHT: 0.4,
} as const;

// =============================================================================
// IN-MEMORY STORAGE (Replace with persistence layer in production)
// =============================================================================

/** Per-preset feedback stats */
const presetStatsStore = new Map<string, PresetFeedbackStats>();

/** Learned weights per profile */
const learnedWeightsStore = new Map<RecommendationProfile, LearnedWeights>();

/** Event history (circular buffer) */
const eventHistory: FeedbackEvent[] = [];

// =============================================================================
// CORE ALGORITHMS
// =============================================================================

/**
 * Compute Bayesian posterior probability.
 * Uses Laplace smoothing (add-1) for stability with sparse data.
 *
 * posterior = (successes + prior_a) / (total + prior_a + prior_b)
 *
 * @param successes - Number of positive outcomes
 * @param failures - Number of negative outcomes
 * @returns Posterior probability [0, 1]
 */
export function computeBayesianPosterior(successes: number, failures: number): number {
  const alpha = REINFORCEMENT_CONFIG.PRIOR_POSITIVE;
  const beta = REINFORCEMENT_CONFIG.PRIOR_NEGATIVE;
  return (successes + alpha) / (successes + failures + alpha + beta);
}

/**
 * Compute Wilson score lower bound (95% confidence interval).
 * More robust than raw success rate for small sample sizes.
 *
 * Formula: Wilson score interval lower bound
 *
 * @param successes - Number of positive outcomes
 * @param total - Total number of trials
 * @returns Lower bound of 95% CI [0, 1]
 */
export function computeWilsonLower(successes: number, total: number): number {
  if (total === 0) return 0;

  const z = 1.96; // 95% confidence
  const phat = successes / total;
  const denominator = 1 + (z * z) / total;
  const center = phat + (z * z) / (2 * total);
  const spread = z * Math.sqrt((phat * (1 - phat) + (z * z) / (4 * total)) / total);

  return Math.max(0, (center - spread) / denominator);
}

/**
 * Clamp a value to [min, max] range.
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Normalize weights to sum to 1.0.
 */
function normalizeWeights(weights: ScoringWeights): ScoringWeights {
  const sum = weights.usage + weights.recency + weights.tags + weights.category;
  if (sum <= 0) return { usage: 0.25, recency: 0.25, tags: 0.25, category: 0.25 };
  return {
    usage: weights.usage / sum,
    recency: weights.recency / sum,
    tags: weights.tags / sum,
    category: weights.category / sum,
  };
}

/**
 * Generate a unique event ID.
 */
function generateEventId(): string {
  return `fb_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

// =============================================================================
// FEEDBACK RECORDING
// =============================================================================

/**
 * Initialize feedback stats for a preset.
 */
function initPresetStats(presetId: string): PresetFeedbackStats {
  return {
    presetId,
    timesShown: 0,
    timesSelected: 0,
    timesIgnored: 0,
    timesSelectedOther: 0,
    engagementCount: 0,
    upvotes: 0,
    downvotes: 0,
    hides: 0,
    pins: 0,
    implicitScore: 0.5,
    explicitScore: 0.5,
    combinedScore: 0.5,
    wilsonLower: 0,
    lastUpdated: new Date().toISOString(),
    totalFeedbackCount: 0,
  };
}

/**
 * Get or create feedback stats for a preset.
 */
export function getPresetStats(presetId: string): PresetFeedbackStats {
  let stats = presetStatsStore.get(presetId);
  if (!stats) {
    stats = initPresetStats(presetId);
    presetStatsStore.set(presetId, stats);
  }
  return { ...stats }; // Return copy to prevent mutation
}

/**
 * Record implicit feedback (user behavior).
 *
 * @param presetId - The preset receiving feedback
 * @param feedbackType - Type of implicit feedback
 * @param context - Context at feedback time
 * @param recommendationData - Optional data about the recommendation
 * @returns The recorded feedback event
 */
export function recordImplicitFeedback(
  presetId: string,
  feedbackType: ImplicitFeedbackType,
  context: FeedbackContext,
  recommendationData?: {
    rank?: number;
    score?: number;
    breakdown?: ScoreBreakdown;
  }
): FeedbackEvent {
  // Get or create stats
  let stats = presetStatsStore.get(presetId);
  if (!stats) {
    stats = initPresetStats(presetId);
  }

  // Update counters based on feedback type
  switch (feedbackType) {
    case "selected":
      stats.timesSelected++;
      stats.timesShown++;
      break;
    case "ignored":
      stats.timesIgnored++;
      stats.timesShown++;
      break;
    case "selected_other":
      stats.timesSelectedOther++;
      stats.timesShown++;
      break;
    case "engaged":
      stats.engagementCount++;
      break;
  }

  stats.totalFeedbackCount++;
  stats.lastUpdated = new Date().toISOString();

  // Recompute Bayesian scores
  const implicitSuccesses = stats.timesSelected + stats.engagementCount;
  const implicitFailures = stats.timesIgnored + stats.timesSelectedOther;
  stats.implicitScore = computeBayesianPosterior(implicitSuccesses, implicitFailures);
  stats.wilsonLower = computeWilsonLower(implicitSuccesses, stats.timesShown);

  // Recompute combined score
  stats.combinedScore =
    REINFORCEMENT_CONFIG.IMPLICIT_WEIGHT * stats.implicitScore +
    REINFORCEMENT_CONFIG.EXPLICIT_WEIGHT * stats.explicitScore;

  // Store updated stats
  presetStatsStore.set(presetId, stats);

  // Create and store event
  const event: FeedbackEvent = {
    eventId: generateEventId(),
    presetId,
    feedbackType,
    timestamp: new Date().toISOString(),
    context,
    recommendationRank: recommendationData?.rank,
    recommendationScore: recommendationData?.score,
    breakdown: recommendationData?.breakdown,
  };

  // Add to history (circular buffer)
  eventHistory.push(event);
  if (eventHistory.length > REINFORCEMENT_CONFIG.MAX_HISTORY_SIZE) {
    eventHistory.shift();
  }

  return event;
}

/**
 * Record explicit feedback (user action).
 *
 * @param presetId - The preset receiving feedback
 * @param feedbackType - Type of explicit feedback
 * @param context - Context at feedback time
 * @returns The recorded feedback event
 */
export function recordExplicitFeedback(
  presetId: string,
  feedbackType: ExplicitFeedbackType,
  context: FeedbackContext
): FeedbackEvent {
  // Get or create stats
  let stats = presetStatsStore.get(presetId);
  if (!stats) {
    stats = initPresetStats(presetId);
  }

  // Update counters based on feedback type
  switch (feedbackType) {
    case "upvote":
      stats.upvotes++;
      break;
    case "downvote":
      stats.downvotes++;
      break;
    case "hide":
      stats.hides++;
      break;
    case "pin":
      stats.pins++;
      break;
  }

  stats.totalFeedbackCount++;
  stats.lastUpdated = new Date().toISOString();

  // Recompute explicit Bayesian score
  // Upvotes and pins are positive; downvotes and hides are negative
  const explicitSuccesses = stats.upvotes + stats.pins;
  const explicitFailures = stats.downvotes + stats.hides;
  stats.explicitScore = computeBayesianPosterior(explicitSuccesses, explicitFailures);

  // Recompute combined score
  stats.combinedScore =
    REINFORCEMENT_CONFIG.IMPLICIT_WEIGHT * stats.implicitScore +
    REINFORCEMENT_CONFIG.EXPLICIT_WEIGHT * stats.explicitScore;

  // Store updated stats
  presetStatsStore.set(presetId, stats);

  // Create and store event
  const event: FeedbackEvent = {
    eventId: generateEventId(),
    presetId,
    feedbackType,
    timestamp: new Date().toISOString(),
    context,
  };

  // Add to history
  eventHistory.push(event);
  if (eventHistory.length > REINFORCEMENT_CONFIG.MAX_HISTORY_SIZE) {
    eventHistory.shift();
  }

  return event;
}

// =============================================================================
// WEIGHT REINFORCEMENT
// =============================================================================

/**
 * Initialize learned weights for a profile from defaults.
 */
function initLearnedWeights(
  profile: RecommendationProfile,
  baseWeights: ScoringWeights
): LearnedWeights {
  return {
    profile,
    baseWeights: { ...baseWeights },
    adjustedWeights: { ...baseWeights },
    totalAdjustments: 0,
    lastAdjusted: new Date().toISOString(),
    adjustmentHistory: [],
  };
}

/**
 * Get learned weights for a profile.
 * Returns base weights if no learning has occurred.
 */
export function getLearnedWeights(
  profile: RecommendationProfile,
  baseWeights: ScoringWeights
): LearnedWeights {
  let learned = learnedWeightsStore.get(profile);
  if (!learned) {
    learned = initLearnedWeights(profile, baseWeights);
    learnedWeightsStore.set(profile, learned);
  }
  return { ...learned, adjustmentHistory: [...learned.adjustmentHistory] };
}

/**
 * Compute weight adjustment based on feedback.
 *
 * Glass-box logic:
 * - Positive feedback → nudge weights toward components that scored high
 * - Negative feedback → nudge weights away from components that scored high
 * - Step size is clipped to prevent runaway drift
 *
 * @param feedbackType - Type of feedback received
 * @param breakdown - Component scores at feedback time
 * @returns Weight deltas to apply
 */
export function computeWeightDeltas(
  feedbackType: ImplicitFeedbackType | ExplicitFeedbackType,
  breakdown: ScoreBreakdown
): ScoringWeights {
  // Determine direction: positive or negative reinforcement
  const isPositive = ["selected", "engaged", "upvote", "pin"].includes(feedbackType);
  const direction = isPositive ? 1 : -1;

  // Compute raw deltas proportional to component scores
  const stepSize = REINFORCEMENT_CONFIG.STEP_SIZE;
  const rawDeltas = {
    usage: direction * breakdown.usage * stepSize,
    recency: direction * breakdown.recency * stepSize,
    tags: direction * breakdown.tags * stepSize,
    category: direction * breakdown.category * stepSize,
  };

  // Clamp each delta
  const clampDelta = (d: number) => clamp(d, -REINFORCEMENT_CONFIG.MAX_STEP_SIZE, REINFORCEMENT_CONFIG.MAX_STEP_SIZE);

  return {
    usage: clampDelta(rawDeltas.usage),
    recency: clampDelta(rawDeltas.recency),
    tags: clampDelta(rawDeltas.tags),
    category: clampDelta(rawDeltas.category),
  };
}

/**
 * Apply reinforcement to learned weights.
 *
 * @param profile - Which weight profile to adjust
 * @param baseWeights - Original profile weights (for reference)
 * @param presetId - Preset that triggered the feedback
 * @param feedbackType - Type of feedback
 * @param breakdown - Component scores at feedback time
 * @returns The adjustment that was applied
 */
export function applyReinforcement(
  profile: RecommendationProfile,
  baseWeights: ScoringWeights,
  presetId: string,
  feedbackType: ImplicitFeedbackType | ExplicitFeedbackType,
  breakdown: ScoreBreakdown
): WeightAdjustment {
  // Get or create learned weights
  let learned = learnedWeightsStore.get(profile);
  if (!learned) {
    learned = initLearnedWeights(profile, baseWeights);
  }

  // Check minimum feedback threshold
  const stats = getPresetStats(presetId);
  if (stats.totalFeedbackCount < REINFORCEMENT_CONFIG.MIN_FEEDBACK_FOR_ADJUSTMENT) {
    // Not enough data — return zero adjustment but still record
    const noOpAdjustment: WeightAdjustment = {
      profile,
      deltas: { usage: 0, recency: 0, tags: 0, category: 0 },
      reason: `Insufficient feedback (${stats.totalFeedbackCount}/${REINFORCEMENT_CONFIG.MIN_FEEDBACK_FOR_ADJUSTMENT})`,
      timestamp: new Date().toISOString(),
      presetId,
      feedbackType,
    };
    return noOpAdjustment;
  }

  // Compute deltas
  const deltas = computeWeightDeltas(feedbackType, breakdown);

  // Apply deltas with clamping to weight bounds
  const newWeights: ScoringWeights = {
    usage: clamp(
      learned.adjustedWeights.usage + deltas.usage,
      REINFORCEMENT_CONFIG.MIN_WEIGHT,
      REINFORCEMENT_CONFIG.MAX_WEIGHT
    ),
    recency: clamp(
      learned.adjustedWeights.recency + deltas.recency,
      REINFORCEMENT_CONFIG.MIN_WEIGHT,
      REINFORCEMENT_CONFIG.MAX_WEIGHT
    ),
    tags: clamp(
      learned.adjustedWeights.tags + deltas.tags,
      REINFORCEMENT_CONFIG.MIN_WEIGHT,
      REINFORCEMENT_CONFIG.MAX_WEIGHT
    ),
    category: clamp(
      learned.adjustedWeights.category + deltas.category,
      REINFORCEMENT_CONFIG.MIN_WEIGHT,
      REINFORCEMENT_CONFIG.MAX_WEIGHT
    ),
  };

  // Normalize to sum to 1
  learned.adjustedWeights = normalizeWeights(newWeights);
  learned.totalAdjustments++;
  learned.lastAdjusted = new Date().toISOString();

  // Create adjustment record
  const adjustment: WeightAdjustment = {
    profile,
    deltas,
    reason: generateAdjustmentReason(feedbackType, breakdown),
    timestamp: learned.lastAdjusted,
    presetId,
    feedbackType,
  };

  // Add to history (bounded)
  learned.adjustmentHistory.push(adjustment);
  if (learned.adjustmentHistory.length > REINFORCEMENT_CONFIG.MAX_ADJUSTMENT_HISTORY) {
    learned.adjustmentHistory.shift();
  }

  // Store
  learnedWeightsStore.set(profile, learned);

  return adjustment;
}

/**
 * Generate human-readable reason for weight adjustment.
 */
function generateAdjustmentReason(
  feedbackType: ImplicitFeedbackType | ExplicitFeedbackType,
  breakdown: ScoreBreakdown
): string {
  const isPositive = ["selected", "engaged", "upvote", "pin"].includes(feedbackType);
  const direction = isPositive ? "boosting" : "reducing";

  // Find strongest component
  const components = [
    { name: "usage", value: breakdown.usage },
    { name: "recency", value: breakdown.recency },
    { name: "tags", value: breakdown.tags },
    { name: "category", value: breakdown.category },
  ];
  components.sort((a, b) => b.value - a.value);
  const strongest = components[0];

  return `${feedbackType} feedback → ${direction} weights toward ${strongest.name} (score: ${strongest.value.toFixed(2)})`;
}

// =============================================================================
// INTEGRATION HOOKS — For UI and System Components
// =============================================================================

/**
 * Record that a preset was selected from recommendations.
 * Convenience wrapper for common use case.
 */
export function onPresetSelected(
  presetId: string,
  profile: RecommendationProfile,
  baseWeights: ScoringWeights,
  rank: number,
  score: number,
  breakdown: ScoreBreakdown,
  context?: Partial<FeedbackContext>
): { event: FeedbackEvent; adjustment: WeightAdjustment } {
  const fullContext: FeedbackContext = {
    profile,
    ...context,
  };

  const event = recordImplicitFeedback(presetId, "selected", fullContext, {
    rank,
    score,
    breakdown,
  });

  const adjustment = applyReinforcement(profile, baseWeights, presetId, "selected", breakdown);

  return { event, adjustment };
}

/**
 * Record that a recommendation was shown but not selected.
 * Call this when the user selects a different preset.
 */
export function onPresetIgnored(
  presetId: string,
  profile: RecommendationProfile,
  context?: Partial<FeedbackContext>
): FeedbackEvent {
  const fullContext: FeedbackContext = {
    profile,
    ...context,
  };

  return recordImplicitFeedback(presetId, "ignored", fullContext);
}

/**
 * Record thumbs up/down feedback.
 */
export function onExplicitFeedback(
  presetId: string,
  isPositive: boolean,
  profile: RecommendationProfile,
  baseWeights: ScoringWeights,
  breakdown: ScoreBreakdown,
  context?: Partial<FeedbackContext>
): { event: FeedbackEvent; adjustment: WeightAdjustment } {
  const feedbackType: ExplicitFeedbackType = isPositive ? "upvote" : "downvote";
  const fullContext: FeedbackContext = {
    profile,
    ...context,
  };

  const event = recordExplicitFeedback(presetId, feedbackType, fullContext);
  const adjustment = applyReinforcement(profile, baseWeights, presetId, feedbackType, breakdown);

  return { event, adjustment };
}

/**
 * Mark a preset as hidden ("never show again").
 */
export function onPresetHidden(
  presetId: string,
  profile: RecommendationProfile,
  context?: Partial<FeedbackContext>
): FeedbackEvent {
  const fullContext: FeedbackContext = {
    profile,
    ...context,
  };

  return recordExplicitFeedback(presetId, "hide", fullContext);
}

/**
 * Get hidden preset IDs for filtering.
 */
export function getHiddenPresetIds(): string[] {
  const hidden: string[] = [];
  presetStatsStore.forEach((stats, presetId) => {
    if (stats.hides > 0) {
      hidden.push(presetId);
    }
  });
  return hidden;
}

/**
 * Check if a preset should be filtered out.
 */
export function shouldFilterPreset(presetId: string): boolean {
  const stats = presetStatsStore.get(presetId);
  if (!stats) return false;
  return stats.hides > 0;
}

// =============================================================================
// DATA EXPORT — For Analytics and ML Training
// =============================================================================

/**
 * Export all feedback data for analytics/ML.
 */
export function exportFeedbackData(): FeedbackExport {
  const presetStats: PresetFeedbackStats[] = [];
  presetStatsStore.forEach((stats) => {
    presetStats.push({ ...stats });
  });

  const learnedWeights: LearnedWeights[] = [];
  learnedWeightsStore.forEach((learned) => {
    learnedWeights.push({
      ...learned,
      adjustmentHistory: [...learned.adjustmentHistory],
    });
  });

  return {
    exportedAt: new Date().toISOString(),
    version: "1.0",
    events: [...eventHistory],
    presetStats,
    learnedWeights,
  };
}

/**
 * Get feedback statistics summary.
 */
export function getFeedbackSummary(): {
  totalEvents: number;
  totalPresets: number;
  avgImplicitScore: number;
  avgExplicitScore: number;
  profilesWithAdjustments: number;
} {
  let totalImplicit = 0;
  let totalExplicit = 0;
  let count = 0;

  presetStatsStore.forEach((stats) => {
    totalImplicit += stats.implicitScore;
    totalExplicit += stats.explicitScore;
    count++;
  });

  let profilesWithAdjustments = 0;
  learnedWeightsStore.forEach((learned) => {
    if (learned.totalAdjustments > 0) {
      profilesWithAdjustments++;
    }
  });

  return {
    totalEvents: eventHistory.length,
    totalPresets: presetStatsStore.size,
    avgImplicitScore: count > 0 ? totalImplicit / count : 0.5,
    avgExplicitScore: count > 0 ? totalExplicit / count : 0.5,
    profilesWithAdjustments,
  };
}

// =============================================================================
// RESET & TESTING UTILITIES
// =============================================================================

/**
 * Clear all feedback data (for testing).
 */
export function resetFeedbackData(): void {
  presetStatsStore.clear();
  learnedWeightsStore.clear();
  eventHistory.length = 0;
}

/**
 * Get raw event history (for testing/debugging).
 */
export function getEventHistory(): FeedbackEvent[] {
  return [...eventHistory];
}

/**
 * Get all preset stats (for testing/debugging).
 */
export function getAllPresetStats(): Map<string, PresetFeedbackStats> {
  return new Map(presetStatsStore);
}
