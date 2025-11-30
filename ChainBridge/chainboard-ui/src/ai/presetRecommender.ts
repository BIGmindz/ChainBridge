/**
 * MAGGIE PAC-001 + PAC-002 — AI Preset Recommendation Engine v2
 * ==============================================================
 * Glass-box heuristic scoring for filter preset recommendations.
 *
 * PAC-001: Core scoring engine with memoization.
 * PAC-002: Formal explanation layer + dynamic weight profiles.
 *
 * Design Choices (Maggie Self-Critique):
 * 1. All math is vanilla TS — no external ML libs.
 * 2. Each scoring term is interpretable (glass-box).
 * 3. All signals normalized 0–1 before weighting.
 * 4. Memoization via WeakMap for preset collections.
 * 5. Future-ready hooks for embedding-based similarity.
 * 6. Structured explanations derived only from the 4 component scores.
 * 7. Weight profiles for different risk appetites.
 *
 * Scoring Formula:
 *   score(preset) = w_usage * normalizedUsage
 *                 + w_recency * recencyScore
 *                 + w_tags * tagSimilarity
 *                 + w_category * categoryMatch
 *
 * @module ai/presetRecommender
 */

// =============================================================================
// TYPES
// =============================================================================

/**
 * SavedFilterPreset — canonical preset structure.
 * ONLY fields defined here may be used in scoring.
 */
export interface SavedFilterPreset {
  id: string;
  name: string;
  description?: string;
  category: PresetCategory;
  tags: string[];
  usageCount: number;
  lastUsedAt: string | null; // ISO timestamp or null if never used
  createdAt: string; // ISO timestamp
  updatedAt: string; // ISO timestamp
  filters: Record<string, unknown>; // Opaque filter config
  isDefault?: boolean;
  isShared?: boolean;
}

/**
 * Preset categories for domain-specific filtering.
 */
export type PresetCategory =
  | "RISK_ANALYSIS"
  | "CORRIDOR_INTEL"
  | "SETTLEMENT"
  | "COMPLIANCE"
  | "OPERATIONS"
  | "CUSTOM";

/**
 * Current user context for personalized recommendations.
 */
export interface RecommendationContext {
  currentCategory?: PresetCategory;
  currentTags?: string[];
  recentPresetIds?: string[];
}

/**
 * Breakdown of how each scoring term contributed.
 */
export interface ScoreBreakdown {
  usage: number;      // 0–1 normalized usage contribution
  recency: number;    // 0–1 recency contribution
  tags: number;       // 0–1 tag similarity contribution
  category: number;   // 0–1 category match contribution
}

// =============================================================================
// PAC-002 — EXPLANATION TYPES
// =============================================================================

/**
 * The four scoring dimensions that can generate explanations.
 */
export type RecommendationReasonKind = "usage" | "recency" | "tags" | "category";

/**
 * Strength of a recommendation reason, derived from score thresholds.
 * - high: score ≥ 0.75
 * - medium: score ≥ 0.40
 * - low: score < 0.40
 */
export type ReasonStrength = "low" | "medium" | "high";

/**
 * A single structured reason explaining why a preset was recommended.
 */
export interface RecommendationReason {
  kind: RecommendationReasonKind;
  strength: ReasonStrength;
  message: string; // User-facing, short
}

/**
 * Complete explanation for a single preset recommendation.
 */
export interface RecommendationExplanation {
  presetId: string;
  reasons: RecommendationReason[];
}

// =============================================================================
// PAC-002 — WEIGHT PROFILES
// =============================================================================

/**
 * Named weight profiles for different recommendation strategies.
 * - conservative: Favors known categories, stable presets
 * - moderate: Balanced (PAC-001 defaults)
 * - aggressive: Favors tag similarity and usage, explores more
 */
export type RecommendationProfile = "conservative" | "moderate" | "aggressive";

/**
 * Single recommendation result with explanation.
 */
export interface PresetRecommendation {
  presetId: string;
  presetName: string;
  score: number;           // Final weighted score (0–1)
  breakdown: ScoreBreakdown;
  reasons: string[];       // Human-readable explanations (legacy, kept for backward compat)
  explanation: RecommendationExplanation; // PAC-002: Structured explanation
}

/**
 * Full recommendation response.
 */
export interface RecommendationResult {
  recommendations: PresetRecommendation[];
  computedAt: string;      // ISO timestamp
  contextUsed: RecommendationContext;
  debug?: RecommendationDebug;
}

/**
 * Debug output for glass-box transparency.
 */
export interface RecommendationDebug {
  totalPresetsScored: number;
  maxUsageInSet: number;
  recencyWindowMs: number;
  weights: ScoringWeights;
  allScores: Array<{ presetId: string; score: number; breakdown: ScoreBreakdown }>;
}

// =============================================================================
// CONFIGURATION — Tunable Weights
// =============================================================================

export interface ScoringWeights {
  usage: number;
  recency: number;
  tags: number;
  category: number;
}

/**
 * PAC-001 defaults (moderate profile).
 */
const DEFAULT_WEIGHTS: ScoringWeights = {
  usage: 0.25,
  recency: 0.30,
  tags: 0.30,
  category: 0.15,
};

/**
 * PAC-002: Weight profiles for different recommendation strategies.
 *
 * Design rationale:
 * - Conservative: Higher category weight (0.35) because users want "safe" familiar categories.
 *   Lower tags (0.20) to avoid exploratory suggestions.
 * - Moderate: Balanced weights, emphasizes recency and tags equally (0.30 each).
 * - Aggressive: Highest tags weight (0.35) for exploration, minimal category (0.05).
 *
 * All profiles sum to 1.0 for normalized scoring.
 */
const WEIGHT_PROFILES: Record<RecommendationProfile, ScoringWeights> = {
  conservative: {
    usage: 0.20,
    recency: 0.25,
    tags: 0.20,
    category: 0.35, // Conservative cares most about known categories
  },
  moderate: {
    usage: 0.25,
    recency: 0.30,
    tags: 0.30,
    category: 0.15,
  },
  aggressive: {
    usage: 0.30,
    recency: 0.30,
    tags: 0.35, // Aggressive emphasizes tag/strategy similarity
    category: 0.05,
  },
};

/**
 * Get default weights for a recommendation profile.
 * @param profile - The profile name (defaults to "moderate")
 * @returns Scoring weights for that profile
 */
export function getDefaultWeights(
  profile: RecommendationProfile = "moderate"
): ScoringWeights {
  return { ...WEIGHT_PROFILES[profile] };
}

// Recency window: 30 days in milliseconds
const RECENCY_WINDOW_MS = 30 * 24 * 60 * 60 * 1000;

// =============================================================================
// MEMOIZATION CACHE
// =============================================================================

interface MemoizedResult {
  result: RecommendationResult;
  contextHash: string;
  timestamp: number;
}

const memoCache = new WeakMap<readonly SavedFilterPreset[], MemoizedResult>();
const MEMO_TTL_MS = 60_000; // 1 minute TTL

function hashContext(ctx: RecommendationContext): string {
  return JSON.stringify({
    cat: ctx.currentCategory ?? null,
    tags: (ctx.currentTags ?? []).sort(),
    recent: (ctx.recentPresetIds ?? []).sort(),
  });
}

// =============================================================================
// CORE SCORING FUNCTIONS
// =============================================================================

/**
 * Normalize usage counts across all presets (0–1).
 * @param usageCount - This preset's usage count
 * @param maxUsage - Maximum usage count in the preset set
 * @returns Normalized value 0–1
 */
export function normalizeUsage(usageCount: number, maxUsage: number): number {
  if (maxUsage <= 0) return 0;
  return Math.min(1, Math.max(0, usageCount / maxUsage));
}

/**
 * Compute recency score based on time since last use.
 * Uses exponential decay within recency window.
 * @param lastUsedAt - ISO timestamp or null
 * @param now - Current timestamp (ms since epoch)
 * @returns Score 0–1 (1 = just used, 0 = old/never used)
 */
export function computeRecencyScore(lastUsedAt: string | null, now: number): number {
  if (!lastUsedAt) return 0;

  const lastUsedMs = new Date(lastUsedAt).getTime();
  if (isNaN(lastUsedMs)) return 0;

  const deltaMs = now - lastUsedMs;
  if (deltaMs < 0) return 1; // Future date = treat as very recent
  if (deltaMs > RECENCY_WINDOW_MS) return 0;

  // Exponential decay: score = e^(-k * normalizedDelta)
  // k=3 gives nice decay curve: ~0.05 at end of window
  const normalizedDelta = deltaMs / RECENCY_WINDOW_MS;
  return Math.exp(-3 * normalizedDelta);
}

/**
 * Compute Jaccard similarity between two tag sets.
 * J(A, B) = |A ∩ B| / |A ∪ B|
 * @param tagsA - First tag set
 * @param tagsB - Second tag set
 * @returns Similarity 0–1 (1 = identical, 0 = no overlap)
 */
export function computeSimilarity(tagsA: string[], tagsB: string[]): number {
  if (tagsA.length === 0 && tagsB.length === 0) return 1; // Both empty = perfect match
  if (tagsA.length === 0 || tagsB.length === 0) return 0; // One empty = no match

  const setA = new Set(tagsA.map((t) => t.toLowerCase().trim()));
  const setB = new Set(tagsB.map((t) => t.toLowerCase().trim()));

  let intersectionSize = 0;
  setA.forEach((tag) => {
    if (setB.has(tag)) intersectionSize++;
  });

  const unionSize = setA.size + setB.size - intersectionSize;
  if (unionSize === 0) return 0;

  return intersectionSize / unionSize;
}

/**
 * Category match: 1 if same category, 0 otherwise.
 * @param presetCategory - Preset's category
 * @param targetCategory - Target category from context
 * @returns 1 or 0
 */
export function computeCategoryMatch(
  presetCategory: PresetCategory,
  targetCategory: PresetCategory | undefined
): number {
  if (!targetCategory) return 0.5; // No target = neutral score
  return presetCategory === targetCategory ? 1 : 0;
}

// =============================================================================
// REASON GENERATION
// =============================================================================

function generateReasons(breakdown: ScoreBreakdown, weights: ScoringWeights): string[] {
  const reasons: string[] = [];
  const threshold = 0.3; // Only mention significant contributors

  if (breakdown.usage >= threshold) {
    reasons.push("Frequently used preset");
  }
  if (breakdown.recency >= threshold) {
    reasons.push("Recently used");
  }
  if (breakdown.tags >= threshold) {
    reasons.push("Similar tags to current context");
  }
  if (breakdown.category >= threshold && weights.category > 0) {
    reasons.push("Matches current category");
  }

  if (reasons.length === 0) {
    reasons.push("General recommendation");
  }

  return reasons;
}

// =============================================================================
// PAC-002 — EXPLANATION LAYER
// =============================================================================

/**
 * Thresholds for mapping scores to strength levels.
 * These are calibrated for interpretability:
 * - HIGH_THRESHOLD (0.75): Strong signal, definitely worth mentioning
 * - MEDIUM_THRESHOLD (0.40): Moderate signal, contributes meaningfully
 * - Below 0.40: Low signal, omit from explanations unless all are low
 */
const HIGH_THRESHOLD = 0.75;
const MEDIUM_THRESHOLD = 0.40;

/**
 * Map a normalized score [0,1] to a strength level.
 * @param score - Normalized score (clamped to [0,1] defensively)
 * @returns Strength level
 */
function scoreToStrength(score: number): ReasonStrength {
  const clampedScore = Math.max(0, Math.min(1, score));
  if (clampedScore >= HIGH_THRESHOLD) return "high";
  if (clampedScore >= MEDIUM_THRESHOLD) return "medium";
  return "low";
}

/**
 * Human-readable messages for each reason kind.
 * Kept short and user-facing.
 */
const REASON_MESSAGES: Record<RecommendationReasonKind, string> = {
  usage: "Frequently used by you",
  recency: "Used recently",
  tags: "Matches your current tags",
  category: "Same category as current view",
};

/**
 * Generate a structured explanation for a recommendation.
 * Glass-box: all reasons derive directly from the 4 component scores.
 *
 * Rules:
 * 1. Only include reasons where strength !== "low" (to avoid noise)
 * 2. If all components are low, return a single generic reason
 * 3. All inputs assumed ∈ [0,1] but clamped defensively
 *
 * @param presetId - The preset being explained
 * @param breakdown - The 4 component scores
 * @returns Structured explanation
 */
export function explainRecommendation(
  presetId: string,
  breakdown: ScoreBreakdown
): RecommendationExplanation {
  const reasons: RecommendationReason[] = [];

  // Process each component
  const components: Array<{ kind: RecommendationReasonKind; score: number }> = [
    { kind: "usage", score: breakdown.usage },
    { kind: "recency", score: breakdown.recency },
    { kind: "tags", score: breakdown.tags },
    { kind: "category", score: breakdown.category },
  ];

  for (const { kind, score } of components) {
    const strength = scoreToStrength(score);
    // Only include non-low reasons to avoid noisy explanations
    if (strength !== "low") {
      reasons.push({
        kind,
        strength,
        message: REASON_MESSAGES[kind],
      });
    }
  }

  // If all components are low, provide a generic fallback reason
  if (reasons.length === 0) {
    reasons.push({
      kind: "usage",
      strength: "low",
      message: "Generic suggestion (low signal)",
    });
  }

  return { presetId, reasons };
}

// =============================================================================
// MAIN RECOMMENDATION ENGINE
// =============================================================================

/**
 * Normalize weights so they sum to 1.0.
 * Ensures consistent scoring regardless of weight magnitudes.
 * @param weights - Raw weights (may not sum to 1)
 * @returns Normalized weights summing to 1.0
 */
function normalizeWeights(weights: ScoringWeights): ScoringWeights {
  const sum = weights.usage + weights.recency + weights.tags + weights.category;
  if (sum <= 0) return getDefaultWeights("moderate"); // Fallback if all zero
  return {
    usage: weights.usage / sum,
    recency: weights.recency / sum,
    tags: weights.tags / sum,
    category: weights.category / sum,
  };
}

/**
 * Compute AI recommendations for presets.
 * Glass-box scoring with full breakdown.
 *
 * PAC-002: Now supports profile-based weights and structured explanations.
 *
 * @param presets - All available presets
 * @param context - Current user context
 * @param options - Optional configuration
 * @returns Ranked recommendations with explanations
 */
export function computeRecommendations(
  presets: readonly SavedFilterPreset[],
  context: RecommendationContext = {},
  options: {
    topN?: number;
    weights?: Partial<ScoringWeights>;
    profile?: RecommendationProfile;       // PAC-002: Named profile
    weightsOverride?: ScoringWeights;      // PAC-002: Full weights override
    includeDebug?: boolean;
    nowOverride?: number;                  // PAC-002: For deterministic testing
  } = {}
): RecommendationResult {
  const topN = options.topN ?? 3;
  const includeDebug = options.includeDebug ?? false;
  const now = options.nowOverride ?? Date.now();

  // PAC-002: Resolve weights with priority:
  // 1. weightsOverride (if provided) → use directly
  // 2. profile (if provided) → getDefaultWeights(profile)
  // 3. weights partial (if provided) → merge with moderate defaults
  // 4. Default → moderate profile
  let resolvedWeights: ScoringWeights;
  if (options.weightsOverride) {
    resolvedWeights = normalizeWeights(options.weightsOverride);
  } else if (options.profile) {
    resolvedWeights = getDefaultWeights(options.profile);
  } else if (options.weights) {
    resolvedWeights = normalizeWeights({ ...DEFAULT_WEIGHTS, ...options.weights });
  } else {
    resolvedWeights = DEFAULT_WEIGHTS;
  }

  // Check memoization cache (include weights in hash for PAC-002)
  const contextHash = hashContext(context) + JSON.stringify(resolvedWeights);
  const cached = memoCache.get(presets);
  if (cached && cached.contextHash === contextHash && now - cached.timestamp < MEMO_TTL_MS) {
    return cached.result;
  }

  // Compute max usage for normalization
  const maxUsage = presets.reduce((max, p) => Math.max(max, p.usageCount), 0);

  // Score all presets
  const allScores: Array<{
    presetId: string;
    presetName: string;
    score: number;
    breakdown: ScoreBreakdown;
  }> = [];

  for (const preset of presets) {
    // Compute individual signals (all 0–1)
    const usageSignal = normalizeUsage(preset.usageCount, maxUsage);
    const recencySignal = computeRecencyScore(preset.lastUsedAt, now);
    const tagSignal = computeSimilarity(preset.tags, context.currentTags ?? []);
    const categorySignal = computeCategoryMatch(preset.category, context.currentCategory);

    // Weighted sum
    const score =
      resolvedWeights.usage * usageSignal +
      resolvedWeights.recency * recencySignal +
      resolvedWeights.tags * tagSignal +
      resolvedWeights.category * categorySignal;

    const breakdown: ScoreBreakdown = {
      usage: usageSignal,
      recency: recencySignal,
      tags: tagSignal,
      category: categorySignal,
    };

    allScores.push({
      presetId: preset.id,
      presetName: preset.name,
      score,
      breakdown,
    });
  }

  // Sort by score descending
  allScores.sort((a, b) => b.score - a.score);

  // Take top N and generate reasons + explanations (PAC-002)
  const recommendations: PresetRecommendation[] = allScores.slice(0, topN).map((scored) => ({
    presetId: scored.presetId,
    presetName: scored.presetName,
    score: scored.score,
    breakdown: scored.breakdown,
    reasons: generateReasons(scored.breakdown, resolvedWeights),
    explanation: explainRecommendation(scored.presetId, scored.breakdown), // PAC-002
  }));

  const result: RecommendationResult = {
    recommendations,
    computedAt: new Date(now).toISOString(),
    contextUsed: context,
  };

  // Include debug info if requested
  if (includeDebug) {
    result.debug = {
      totalPresetsScored: presets.length,
      maxUsageInSet: maxUsage,
      recencyWindowMs: RECENCY_WINDOW_MS,
      weights: resolvedWeights,
      allScores: allScores.map((s) => ({
        presetId: s.presetId,
        score: s.score,
        breakdown: s.breakdown,
      })),
    };
  }

  // Cache result (WeakMap allows GC when presets array is dropped)
  memoCache.set(presets, {
    result,
    contextHash,
    timestamp: now,
  });

  return result;
}

// =============================================================================
// INTEGRATION HOOK — For ScenarioHistoryPanel or similar components
// =============================================================================

/**
 * Get AI-recommended presets for a given context.
 * Convenience wrapper for UI integration.
 *
 * @param filterPresets - All available presets
 * @param currentContext - Current UI context
 * @returns Top 3 recommended presets with explanations
 */
export function getAIRecommendedPresets(
  filterPresets: readonly SavedFilterPreset[],
  currentContext: RecommendationContext
): PresetRecommendation[] {
  const result = computeRecommendations(filterPresets, currentContext, {
    topN: 3,
    includeDebug: false,
  });
  return result.recommendations;
}

// =============================================================================
// FUTURE ML HOOKS (Placeholders for Phase 2)
// =============================================================================

/**
 * FUTURE: Embedding-based similarity using vector math.
 * Placeholder for when backend ML service is available.
 *
 * @param _embeddingA - First embedding vector
 * @param _embeddingB - Second embedding vector
 * @returns Cosine similarity 0–1
 */
export function computeEmbeddingSimilarity(
  _embeddingA: number[],
  _embeddingB: number[]
): number {
  // TODO: Implement when SxT/Claude embedding service is integrated
  // return cosineSimilarity(embeddingA, embeddingB);
  console.warn("[MAGGIE] Embedding similarity not yet implemented — awaiting backend ML service");
  return 0;
}

/**
 * FUTURE: Behavioral personalization based on user history.
 * Placeholder for cross-user collaborative filtering.
 *
 * @param _userId - User ID for personalization
 * @param _presets - Available presets
 * @returns Personalized scoring adjustments
 */
export function getPersonalizedWeights(
  _userId: string,
  _presets: readonly SavedFilterPreset[]
): Partial<ScoringWeights> {
  // TODO: Implement when user behavior tracking is available
  console.warn("[MAGGIE] Personalized weights not yet implemented — using defaults");
  return {};
}

// =============================================================================
// DEBUG & TESTING UTILITIES
// =============================================================================

/**
 * Log recommendation results in a formatted table.
 * For development debugging only.
 */
export function logRecommendationTable(result: RecommendationResult): void {
  console.group("[MAGGIE PAC-002] Recommendation Results");
  console.log("Computed at:", result.computedAt);
  console.log("Context:", result.contextUsed);
  console.table(
    result.recommendations.map((r) => ({
      Preset: r.presetName,
      Score: r.score.toFixed(3),
      Usage: r.breakdown.usage.toFixed(2),
      Recency: r.breakdown.recency.toFixed(2),
      Tags: r.breakdown.tags.toFixed(2),
      Category: r.breakdown.category.toFixed(2),
      Reasons: r.reasons.join(", "),
      Explanations: r.explanation.reasons.map((e) => `${e.kind}:${e.strength}`).join(", "),
    }))
  );
  if (result.debug) {
    console.log("Debug:", result.debug);
  }
  console.groupEnd();
}

/**
 * Self-critique validation for Maggie's output.
 * Ensures all mathematical invariants hold.
 * PAC-002: Also validates explanations.
 */
export function validateRecommendations(result: RecommendationResult): {
  valid: boolean;
  issues: string[];
} {
  const issues: string[] = [];

  for (const rec of result.recommendations) {
    // All scores must be 0–1
    if (rec.score < 0 || rec.score > 1) {
      issues.push(`Score out of range for ${rec.presetId}: ${rec.score}`);
    }
    // All breakdown values must be 0–1
    const bd = rec.breakdown;
    if (bd.usage < 0 || bd.usage > 1) issues.push(`Usage out of range: ${bd.usage}`);
    if (bd.recency < 0 || bd.recency > 1) issues.push(`Recency out of range: ${bd.recency}`);
    if (bd.tags < 0 || bd.tags > 1) issues.push(`Tags out of range: ${bd.tags}`);
    if (bd.category < 0 || bd.category > 1) issues.push(`Category out of range: ${bd.category}`);
    // Reasons must exist
    if (rec.reasons.length === 0) {
      issues.push(`No reasons provided for ${rec.presetId}`);
    }
    // PAC-002: Explanation must exist and have at least one reason
    if (!rec.explanation) {
      issues.push(`No explanation for ${rec.presetId}`);
    } else if (rec.explanation.reasons.length === 0) {
      issues.push(`Empty explanation reasons for ${rec.presetId}`);
    } else {
      // Validate each reason
      for (const reason of rec.explanation.reasons) {
        const validKinds = ["usage", "recency", "tags", "category"];
        const validStrengths = ["low", "medium", "high"];
        if (!validKinds.includes(reason.kind)) {
          issues.push(`Invalid reason kind: ${reason.kind}`);
        }
        if (!validStrengths.includes(reason.strength)) {
          issues.push(`Invalid reason strength: ${reason.strength}`);
        }
        if (!reason.message || reason.message.length === 0) {
          issues.push(`Empty reason message for ${reason.kind}`);
        }
      }
    }
  }

  return { valid: issues.length === 0, issues };
}
