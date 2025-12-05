/**
 * MAGGIE PAC-001 + PAC-002 — Unit Tests for Preset Recommender
 * =============================================================
 * PAC-001: Core scoring, normalization, and memoization.
 * PAC-002: Explanation layer, weight profiles, edge cases.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  normalizeUsage,
  computeRecencyScore,
  computeSimilarity,
  computeCategoryMatch,
  computeRecommendations,
  getAIRecommendedPresets,
  validateRecommendations,
  getDefaultWeights,
  explainRecommendation,
  type SavedFilterPreset,
  type RecommendationContext,
  type RecommendationProfile,
  type ScoreBreakdown,
} from "./presetRecommender";

// =============================================================================
// TEST DATA
// =============================================================================

function createTestPreset(overrides: Partial<SavedFilterPreset>): SavedFilterPreset {
  return {
    id: "test-preset-1",
    name: "Test Preset",
    category: "RISK_ANALYSIS",
    tags: ["risk", "compliance"],
    usageCount: 10,
    lastUsedAt: new Date().toISOString(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    filters: {},
    ...overrides,
  };
}

const NOW = Date.now();
const ONE_DAY_MS = 24 * 60 * 60 * 1000;

// =============================================================================
// UNIT TESTS — Individual Scoring Functions
// =============================================================================

describe("normalizeUsage", () => {
  it("returns 0 when maxUsage is 0", () => {
    expect(normalizeUsage(10, 0)).toBe(0);
  });

  it("returns 1 when usage equals maxUsage", () => {
    expect(normalizeUsage(100, 100)).toBe(1);
  });

  it("returns correct ratio for intermediate values", () => {
    expect(normalizeUsage(50, 100)).toBe(0.5);
    expect(normalizeUsage(25, 100)).toBe(0.25);
  });

  it("clamps to 0–1 range", () => {
    expect(normalizeUsage(-10, 100)).toBe(0);
    expect(normalizeUsage(150, 100)).toBe(1);
  });
});

describe("computeRecencyScore", () => {
  it("returns 0 for null lastUsedAt", () => {
    expect(computeRecencyScore(null, NOW)).toBe(0);
  });

  it("returns ~1 for very recent usage", () => {
    const recentTime = new Date(NOW - 1000).toISOString(); // 1 second ago
    const score = computeRecencyScore(recentTime, NOW);
    expect(score).toBeGreaterThan(0.99);
  });

  it("returns 0 for usage older than 30 days", () => {
    const oldTime = new Date(NOW - 31 * ONE_DAY_MS).toISOString();
    expect(computeRecencyScore(oldTime, NOW)).toBe(0);
  });

  it("decays exponentially for intermediate times", () => {
    const fifteenDaysAgo = new Date(NOW - 15 * ONE_DAY_MS).toISOString();
    const score = computeRecencyScore(fifteenDaysAgo, NOW);
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThan(0.5);
  });

  it("returns 0 for invalid date strings", () => {
    expect(computeRecencyScore("not-a-date", NOW)).toBe(0);
  });
});

describe("computeSimilarity (Jaccard)", () => {
  it("returns 1 for identical non-empty sets", () => {
    expect(computeSimilarity(["a", "b", "c"], ["a", "b", "c"])).toBe(1);
  });

  it("returns 1 for two empty sets", () => {
    expect(computeSimilarity([], [])).toBe(1);
  });

  it("returns 0 when one set is empty", () => {
    expect(computeSimilarity(["a"], [])).toBe(0);
    expect(computeSimilarity([], ["a"])).toBe(0);
  });

  it("returns 0 for completely disjoint sets", () => {
    expect(computeSimilarity(["a", "b"], ["c", "d"])).toBe(0);
  });

  it("computes correct Jaccard for partial overlap", () => {
    // J({a,b,c}, {b,c,d}) = |{b,c}| / |{a,b,c,d}| = 2/4 = 0.5
    expect(computeSimilarity(["a", "b", "c"], ["b", "c", "d"])).toBe(0.5);
  });

  it("is case-insensitive", () => {
    expect(computeSimilarity(["Risk", "COMPLIANCE"], ["risk", "compliance"])).toBe(1);
  });

  it("trims whitespace", () => {
    expect(computeSimilarity(["  risk  "], ["risk"])).toBe(1);
  });
});

describe("computeCategoryMatch", () => {
  it("returns 1 for matching categories", () => {
    expect(computeCategoryMatch("RISK_ANALYSIS", "RISK_ANALYSIS")).toBe(1);
  });

  it("returns 0 for non-matching categories", () => {
    expect(computeCategoryMatch("RISK_ANALYSIS", "SETTLEMENT")).toBe(0);
  });

  it("returns 0.5 when target category is undefined", () => {
    expect(computeCategoryMatch("RISK_ANALYSIS", undefined)).toBe(0.5);
  });
});

// =============================================================================
// INTEGRATION TESTS — Full Recommendation Engine
// =============================================================================

describe("computeRecommendations", () => {
  let presets: SavedFilterPreset[];

  beforeEach(() => {
    presets = [
      createTestPreset({
        id: "preset-high-usage",
        name: "High Usage Preset",
        usageCount: 100,
        lastUsedAt: new Date(NOW - ONE_DAY_MS).toISOString(),
        tags: ["risk", "critical"],
        category: "RISK_ANALYSIS",
      }),
      createTestPreset({
        id: "preset-recent",
        name: "Recent Preset",
        usageCount: 10,
        lastUsedAt: new Date(NOW - 1000).toISOString(), // Just used
        tags: ["settlement"],
        category: "SETTLEMENT",
      }),
      createTestPreset({
        id: "preset-matching-tags",
        name: "Matching Tags Preset",
        usageCount: 20,
        lastUsedAt: new Date(NOW - 7 * ONE_DAY_MS).toISOString(),
        tags: ["risk", "compliance", "audit"],
        category: "COMPLIANCE",
      }),
      createTestPreset({
        id: "preset-old",
        name: "Old Preset",
        usageCount: 5,
        lastUsedAt: new Date(NOW - 60 * ONE_DAY_MS).toISOString(), // 60 days ago
        tags: ["legacy"],
        category: "CUSTOM",
      }),
    ];
  });

  it("returns top N recommendations", () => {
    const result = computeRecommendations(presets, {}, { topN: 2 });
    expect(result.recommendations).toHaveLength(2);
  });

  it("ranks high-usage presets higher when no context", () => {
    const result = computeRecommendations(presets, {}, { topN: 4 });
    // High usage + recent should be near top
    const topIds = result.recommendations.map((r) => r.presetId);
    expect(topIds[0]).toBe("preset-high-usage"); // Highest usage + recent
  });

  it("boosts presets matching current tags", () => {
    const context: RecommendationContext = {
      currentTags: ["risk", "compliance"],
    };
    const result = computeRecommendations(presets, context, { topN: 4 });

    // Matching tags preset should rank higher
    const matchingTagsRec = result.recommendations.find(
      (r) => r.presetId === "preset-matching-tags"
    );
    expect(matchingTagsRec).toBeDefined();
    expect(matchingTagsRec!.breakdown.tags).toBeGreaterThan(0.5);
  });

  it("boosts presets matching current category", () => {
    const context: RecommendationContext = {
      currentCategory: "SETTLEMENT",
    };
    const result = computeRecommendations(presets, context, { topN: 4 });

    const settlementRec = result.recommendations.find(
      (r) => r.presetId === "preset-recent"
    );
    expect(settlementRec).toBeDefined();
    expect(settlementRec!.breakdown.category).toBe(1);
  });

  it("all scores are normalized 0–1", () => {
    const result = computeRecommendations(presets, {}, { topN: 4 });

    for (const rec of result.recommendations) {
      expect(rec.score).toBeGreaterThanOrEqual(0);
      expect(rec.score).toBeLessThanOrEqual(1);
      expect(rec.breakdown.usage).toBeGreaterThanOrEqual(0);
      expect(rec.breakdown.usage).toBeLessThanOrEqual(1);
      expect(rec.breakdown.recency).toBeGreaterThanOrEqual(0);
      expect(rec.breakdown.recency).toBeLessThanOrEqual(1);
      expect(rec.breakdown.tags).toBeGreaterThanOrEqual(0);
      expect(rec.breakdown.tags).toBeLessThanOrEqual(1);
      expect(rec.breakdown.category).toBeGreaterThanOrEqual(0);
      expect(rec.breakdown.category).toBeLessThanOrEqual(1);
    }
  });

  it("includes debug info when requested", () => {
    const result = computeRecommendations(presets, {}, { includeDebug: true });
    expect(result.debug).toBeDefined();
    expect(result.debug!.totalPresetsScored).toBe(4);
    expect(result.debug!.allScores).toHaveLength(4);
  });

  it("generates meaningful reasons", () => {
    const result = computeRecommendations(presets, {}, { topN: 4 });

    for (const rec of result.recommendations) {
      expect(rec.reasons.length).toBeGreaterThan(0);
      expect(rec.reasons.every((r) => typeof r === "string")).toBe(true);
    }
  });

  it("handles empty preset array", () => {
    const result = computeRecommendations([], {});
    expect(result.recommendations).toHaveLength(0);
  });

  it("returns memoized result for same inputs", () => {
    const context = { currentTags: ["test"] };
    const result1 = computeRecommendations(presets, context);
    const result2 = computeRecommendations(presets, context);

    // Should be same object from cache
    expect(result1.computedAt).toBe(result2.computedAt);
  });
});

// =============================================================================
// VALIDATION TESTS — Self-Critique
// =============================================================================

describe("validateRecommendations", () => {
  it("validates correct recommendations", () => {
    const presets = [
      createTestPreset({ id: "p1", usageCount: 50 }),
      createTestPreset({ id: "p2", usageCount: 30 }),
    ];
    const result = computeRecommendations(presets, {});
    const validation = validateRecommendations(result);

    expect(validation.valid).toBe(true);
    expect(validation.issues).toHaveLength(0);
  });
});

// =============================================================================
// CONVENIENCE WRAPPER TESTS
// =============================================================================

describe("getAIRecommendedPresets", () => {
  it("returns array of top 3 recommendations", () => {
    const presets = [
      createTestPreset({ id: "p1", usageCount: 100 }),
      createTestPreset({ id: "p2", usageCount: 80 }),
      createTestPreset({ id: "p3", usageCount: 60 }),
      createTestPreset({ id: "p4", usageCount: 40 }),
    ];

    const recommendations = getAIRecommendedPresets(presets, {});
    expect(recommendations).toHaveLength(3);
    expect(recommendations[0].presetId).toBe("p1");
  });
});

// =============================================================================
// PAC-002 TESTS — Weight Profiles
// =============================================================================

describe("getDefaultWeights", () => {
  it("returns expected weights for moderate profile (default)", () => {
    const weights = getDefaultWeights();
    expect(weights.usage).toBe(0.25);
    expect(weights.recency).toBe(0.30);
    expect(weights.tags).toBe(0.30);
    expect(weights.category).toBe(0.15);
  });

  it("returns expected weights for conservative profile", () => {
    const weights = getDefaultWeights("conservative");
    expect(weights.usage).toBe(0.20);
    expect(weights.recency).toBe(0.25);
    expect(weights.tags).toBe(0.20);
    expect(weights.category).toBe(0.35); // Conservative favors category
  });

  it("returns expected weights for aggressive profile", () => {
    const weights = getDefaultWeights("aggressive");
    expect(weights.usage).toBe(0.30);
    expect(weights.recency).toBe(0.30);
    expect(weights.tags).toBe(0.35); // Aggressive favors tags
    expect(weights.category).toBe(0.05);
  });

  it("all profiles sum to 1.0", () => {
    const profiles: RecommendationProfile[] = ["conservative", "moderate", "aggressive"];
    for (const profile of profiles) {
      const weights = getDefaultWeights(profile);
      const sum = weights.usage + weights.recency + weights.tags + weights.category;
      expect(sum).toBeCloseTo(1.0, 5);
    }
  });
});

// =============================================================================
// PAC-002 TESTS — Explanation Layer
// =============================================================================

describe("explainRecommendation", () => {
  it("returns high strength for score >= 0.75", () => {
    const breakdown: ScoreBreakdown = {
      usage: 0.9,
      recency: 0.1,
      tags: 0.2,
      category: 0.1,
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    expect(explanation.presetId).toBe("test-preset");
    const usageReason = explanation.reasons.find((r) => r.kind === "usage");
    expect(usageReason).toBeDefined();
    expect(usageReason!.strength).toBe("high");
    expect(usageReason!.message).toBe("Frequently used by you");
  });

  it("returns medium strength for score >= 0.40 and < 0.75", () => {
    const breakdown: ScoreBreakdown = {
      usage: 0.5,
      recency: 0.1,
      tags: 0.2,
      category: 0.1,
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    const usageReason = explanation.reasons.find((r) => r.kind === "usage");
    expect(usageReason).toBeDefined();
    expect(usageReason!.strength).toBe("medium");
  });

  it("excludes low strength reasons (score < 0.40)", () => {
    const breakdown: ScoreBreakdown = {
      usage: 0.8, // high
      recency: 0.1, // low - should be excluded
      tags: 0.2, // low - should be excluded
      category: 0.1, // low - should be excluded
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    // Only usage should be included
    expect(explanation.reasons).toHaveLength(1);
    expect(explanation.reasons[0].kind).toBe("usage");
  });

  it("includes only recency when only recency is high", () => {
    const breakdown: ScoreBreakdown = {
      usage: 0.1,
      recency: 0.85,
      tags: 0.1,
      category: 0.1,
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    expect(explanation.reasons).toHaveLength(1);
    expect(explanation.reasons[0].kind).toBe("recency");
    expect(explanation.reasons[0].strength).toBe("high");
    expect(explanation.reasons[0].message).toBe("Used recently");
  });

  it("returns generic low signal message when all components are low", () => {
    const breakdown: ScoreBreakdown = {
      usage: 0.1,
      recency: 0.1,
      tags: 0.2,
      category: 0.3,
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    expect(explanation.reasons).toHaveLength(1);
    expect(explanation.reasons[0].strength).toBe("low");
    expect(explanation.reasons[0].message).toBe("Generic suggestion (low signal)");
  });

  it("includes multiple reasons when multiple components are significant", () => {
    const breakdown: ScoreBreakdown = {
      usage: 0.8, // high
      recency: 0.6, // medium
      tags: 0.9, // high
      category: 0.1, // low - excluded
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    expect(explanation.reasons).toHaveLength(3);
    const kinds = explanation.reasons.map((r) => r.kind);
    expect(kinds).toContain("usage");
    expect(kinds).toContain("recency");
    expect(kinds).toContain("tags");
    expect(kinds).not.toContain("category");
  });

  it("clamps out-of-range scores defensively", () => {
    const breakdown: ScoreBreakdown = {
      usage: 1.5, // out of range, should clamp to 1
      recency: -0.5, // out of range, should clamp to 0
      tags: 0.5,
      category: 0.5,
    };
    const explanation = explainRecommendation("test-preset", breakdown);

    // Should not throw, and usage should be treated as high (clamped to 1)
    const usageReason = explanation.reasons.find((r) => r.kind === "usage");
    expect(usageReason).toBeDefined();
    expect(usageReason!.strength).toBe("high");
  });
});

// =============================================================================
// PAC-002 TESTS — Profile Integration
// =============================================================================

describe("computeRecommendations with profiles", () => {
  let presets: SavedFilterPreset[];
  const fixedNow = Date.now();

  beforeEach(() => {
    // Create presets that will rank differently under different profiles
    presets = [
      createTestPreset({
        id: "preset-high-category-match",
        name: "Category Match Preset",
        usageCount: 30, // moderate usage
        lastUsedAt: new Date(fixedNow - 10 * ONE_DAY_MS).toISOString(),
        tags: ["other"],
        category: "RISK_ANALYSIS", // Will match when context category = RISK_ANALYSIS
      }),
      createTestPreset({
        id: "preset-high-tags",
        name: "Tags Match Preset",
        usageCount: 30, // moderate usage
        lastUsedAt: new Date(fixedNow - 10 * ONE_DAY_MS).toISOString(),
        tags: ["risk", "compliance", "audit"], // High tag similarity
        category: "SETTLEMENT", // Different category
      }),
      createTestPreset({
        id: "preset-high-usage",
        name: "High Usage Preset",
        usageCount: 100, // highest usage
        lastUsedAt: new Date(fixedNow - 20 * ONE_DAY_MS).toISOString(),
        tags: ["other"],
        category: "CUSTOM",
      }),
    ];
  });

  it("conservative profile favors category match", () => {
    const context: RecommendationContext = {
      currentCategory: "RISK_ANALYSIS",
      currentTags: ["risk", "compliance"],
    };

    const result = computeRecommendations(presets, context, {
      profile: "conservative",
      topN: 3,
      nowOverride: fixedNow,
    });

    // Conservative has highest category weight (0.35)
    // preset-high-category-match should rank higher due to category=1
    const ranking = result.recommendations.map((r) => r.presetId);
    expect(ranking[0]).toBe("preset-high-category-match");
  });

  it("aggressive profile favors tag similarity", () => {
    const context: RecommendationContext = {
      currentCategory: "RISK_ANALYSIS",
      currentTags: ["risk", "compliance", "audit"],
    };

    const result = computeRecommendations(presets, context, {
      profile: "aggressive",
      topN: 3,
      nowOverride: fixedNow,
    });

    // Aggressive has highest tags weight (0.35) and lowest category (0.05)
    // preset-high-tags should rank higher due to tag similarity
    const ranking = result.recommendations.map((r) => r.presetId);
    expect(ranking[0]).toBe("preset-high-tags");
  });

  it("weightsOverride takes priority over profile", () => {
    const context: RecommendationContext = {
      currentCategory: "RISK_ANALYSIS",
      currentTags: [],
    };

    // Override to heavily favor usage
    const result = computeRecommendations(presets, context, {
      profile: "conservative",
      weightsOverride: {
        usage: 1.0,
        recency: 0.0,
        tags: 0.0,
        category: 0.0,
      },
      topN: 3,
      nowOverride: fixedNow,
    });

    // Despite conservative profile, weightsOverride should win
    // preset-high-usage has usageCount=100
    const ranking = result.recommendations.map((r) => r.presetId);
    expect(ranking[0]).toBe("preset-high-usage");
  });

  it("each recommendation includes explanation", () => {
    const result = computeRecommendations(presets, {}, {
      profile: "moderate",
      topN: 3,
      nowOverride: fixedNow,
    });

    for (const rec of result.recommendations) {
      expect(rec.explanation).toBeDefined();
      expect(rec.explanation.presetId).toBe(rec.presetId);
      expect(rec.explanation.reasons.length).toBeGreaterThan(0);
    }
  });

  it("debug output includes resolved weights", () => {
    const result = computeRecommendations(presets, {}, {
      profile: "aggressive",
      includeDebug: true,
      nowOverride: fixedNow,
    });

    expect(result.debug).toBeDefined();
    expect(result.debug!.weights.tags).toBe(0.35); // aggressive tags weight
  });
});

// =============================================================================
// PAC-002 TESTS — Edge Cases
// =============================================================================

describe("edge cases", () => {
  it("handles presets with null lastUsedAt", () => {
    const presets = [
      createTestPreset({
        id: "never-used",
        name: "Never Used Preset",
        usageCount: 0,
        lastUsedAt: null,
      }),
    ];

    const result = computeRecommendations(presets, {});
    expect(result.recommendations).toHaveLength(1);
    expect(result.recommendations[0].breakdown.recency).toBe(0);
  });

  it("handles presets with empty tags", () => {
    const presets = [
      createTestPreset({
        id: "no-tags",
        name: "No Tags Preset",
        tags: [],
      }),
    ];

    const context: RecommendationContext = {
      currentTags: ["risk"],
    };

    const result = computeRecommendations(presets, context);
    expect(result.recommendations).toHaveLength(1);
    expect(result.recommendations[0].breakdown.tags).toBe(0); // No overlap
  });

  it("handles context with empty tags matching preset with empty tags", () => {
    const presets = [
      createTestPreset({
        id: "no-tags",
        name: "No Tags Preset",
        tags: [],
      }),
    ];

    const context: RecommendationContext = {
      currentTags: [],
    };

    const result = computeRecommendations(presets, context);
    expect(result.recommendations[0].breakdown.tags).toBe(1); // Both empty = perfect match
  });

  it("normalizes weights that don't sum to 1", () => {
    const presets = [
      createTestPreset({ id: "p1", usageCount: 100 }),
      createTestPreset({ id: "p2", usageCount: 50 }),
    ];

    const result = computeRecommendations(presets, {}, {
      weightsOverride: {
        usage: 2.0,
        recency: 2.0,
        tags: 2.0,
        category: 2.0,
      }, // Sum = 8, should normalize to 0.25 each
      includeDebug: true,
    });

    expect(result.debug!.weights.usage).toBeCloseTo(0.25, 5);
    expect(result.debug!.weights.recency).toBeCloseTo(0.25, 5);
  });

  it("validates recommendations with explanations pass validation", () => {
    const presets = [
      createTestPreset({ id: "p1", usageCount: 100 }),
      createTestPreset({ id: "p2", usageCount: 50 }),
    ];

    const result = computeRecommendations(presets, {});
    const validation = validateRecommendations(result);

    expect(validation.valid).toBe(true);
    expect(validation.issues).toHaveLength(0);
  });
});
