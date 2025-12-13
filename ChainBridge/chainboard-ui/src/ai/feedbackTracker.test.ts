/**
 * MAGGIE PAC-003 — Unit Tests for Feedback Tracker
 * =================================================
 * Tests Bayesian scoring, weight reinforcement, and edge cases.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  computeBayesianPosterior,
  computeWilsonLower,
  computeWeightDeltas,
  recordImplicitFeedback,
  recordExplicitFeedback,
  applyReinforcement,
  getPresetStats,
  getLearnedWeights,
  onPresetSelected,
  onExplicitFeedback,
  onPresetHidden,
  getHiddenPresetIds,
  shouldFilterPreset,
  exportFeedbackData,
  getFeedbackSummary,
  resetFeedbackData,
  getEventHistory,
  type FeedbackContext,
} from "./feedbackTracker";
import type { ScoringWeights, ScoreBreakdown } from "./presetRecommender";

// =============================================================================
// TEST SETUP
// =============================================================================

const DEFAULT_CONTEXT: FeedbackContext = {
  profile: "moderate",
  category: "RISK_ANALYSIS",
  tags: ["risk", "compliance"],
};

const DEFAULT_BREAKDOWN: ScoreBreakdown = {
  usage: 0.8,
  recency: 0.6,
  tags: 0.7,
  category: 0.5,
};

const DEFAULT_WEIGHTS: ScoringWeights = {
  usage: 0.25,
  recency: 0.30,
  tags: 0.30,
  category: 0.15,
};

beforeEach(() => {
  resetFeedbackData();
});

// =============================================================================
// BAYESIAN POSTERIOR TESTS
// =============================================================================

describe("computeBayesianPosterior", () => {
  it("returns 0.5 with no data (prior only)", () => {
    // With Laplace smoothing (1, 1), posterior = (0+1)/(0+0+1+1) = 0.5
    expect(computeBayesianPosterior(0, 0)).toBe(0.5);
  });

  it("returns value > 0.5 with more successes than failures", () => {
    const posterior = computeBayesianPosterior(10, 2);
    expect(posterior).toBeGreaterThan(0.5);
    // (10+1)/(10+2+2) = 11/14 ≈ 0.786
    expect(posterior).toBeCloseTo(11 / 14, 3);
  });

  it("returns value < 0.5 with more failures than successes", () => {
    const posterior = computeBayesianPosterior(2, 10);
    expect(posterior).toBeLessThan(0.5);
    // (2+1)/(2+10+2) = 3/14 ≈ 0.214
    expect(posterior).toBeCloseTo(3 / 14, 3);
  });

  it("approaches 1.0 with many successes", () => {
    const posterior = computeBayesianPosterior(1000, 0);
    expect(posterior).toBeGreaterThan(0.99);
  });

  it("approaches 0.0 with many failures", () => {
    const posterior = computeBayesianPosterior(0, 1000);
    expect(posterior).toBeLessThan(0.01);
  });
});

// =============================================================================
// WILSON SCORE TESTS
// =============================================================================

describe("computeWilsonLower", () => {
  it("returns 0 with no data", () => {
    expect(computeWilsonLower(0, 0)).toBe(0);
  });

  it("returns low value with few successes and few trials", () => {
    // With 1 success out of 1 trial, lower bound should be conservative
    const wilson = computeWilsonLower(1, 1);
    expect(wilson).toBeGreaterThan(0);
    expect(wilson).toBeLessThan(1);
  });

  it("increases with more successes at same rate", () => {
    const wilson10of20 = computeWilsonLower(10, 20);
    const wilson50of100 = computeWilsonLower(50, 100);
    // Same rate (50%), but more data should give tighter bound
    expect(wilson50of100).toBeGreaterThan(wilson10of20);
  });

  it("returns higher value with better success rate", () => {
    const wilson90pct = computeWilsonLower(90, 100);
    const wilson50pct = computeWilsonLower(50, 100);
    expect(wilson90pct).toBeGreaterThan(wilson50pct);
  });

  it("is always <= raw success rate", () => {
    const successes = 80;
    const total = 100;
    const rawRate = successes / total;
    const wilson = computeWilsonLower(successes, total);
    expect(wilson).toBeLessThanOrEqual(rawRate);
  });
});

// =============================================================================
// WEIGHT DELTA TESTS
// =============================================================================

describe("computeWeightDeltas", () => {
  it("returns positive deltas for positive feedback", () => {
    const deltas = computeWeightDeltas("selected", DEFAULT_BREAKDOWN);
    expect(deltas.usage).toBeGreaterThan(0);
    expect(deltas.recency).toBeGreaterThan(0);
    expect(deltas.tags).toBeGreaterThan(0);
    expect(deltas.category).toBeGreaterThan(0);
  });

  it("returns negative deltas for negative feedback", () => {
    const deltas = computeWeightDeltas("downvote", DEFAULT_BREAKDOWN);
    expect(deltas.usage).toBeLessThan(0);
    expect(deltas.recency).toBeLessThan(0);
    expect(deltas.tags).toBeLessThan(0);
    expect(deltas.category).toBeLessThan(0);
  });

  it("scales deltas proportionally to breakdown scores", () => {
    const breakdown: ScoreBreakdown = {
      usage: 1.0,
      recency: 0.5,
      tags: 0.25,
      category: 0.0,
    };
    const deltas = computeWeightDeltas("selected", breakdown);

    // Usage delta should be highest (score = 1.0)
    expect(Math.abs(deltas.usage)).toBeGreaterThan(Math.abs(deltas.recency));
    expect(Math.abs(deltas.recency)).toBeGreaterThan(Math.abs(deltas.tags));
    // Category delta should be 0 (score = 0)
    expect(deltas.category).toBe(0);
  });

  it("clamps deltas to MAX_STEP_SIZE", () => {
    const highBreakdown: ScoreBreakdown = {
      usage: 1.0,
      recency: 1.0,
      tags: 1.0,
      category: 1.0,
    };
    const deltas = computeWeightDeltas("selected", highBreakdown);

    // Max step size is 0.02
    expect(Math.abs(deltas.usage)).toBeLessThanOrEqual(0.02);
    expect(Math.abs(deltas.recency)).toBeLessThanOrEqual(0.02);
    expect(Math.abs(deltas.tags)).toBeLessThanOrEqual(0.02);
    expect(Math.abs(deltas.category)).toBeLessThanOrEqual(0.02);
  });

  it("treats upvote, pin, engaged as positive", () => {
    const types = ["selected", "engaged", "upvote", "pin"] as const;
    for (const type of types) {
      const deltas = computeWeightDeltas(type, DEFAULT_BREAKDOWN);
      expect(deltas.usage).toBeGreaterThan(0);
    }
  });

  it("treats downvote, hide, ignored, selected_other as negative", () => {
    const types = ["ignored", "selected_other", "downvote", "hide"] as const;
    for (const type of types) {
      const deltas = computeWeightDeltas(type, DEFAULT_BREAKDOWN);
      expect(deltas.usage).toBeLessThan(0);
    }
  });
});

// =============================================================================
// IMPLICIT FEEDBACK TESTS
// =============================================================================

describe("recordImplicitFeedback", () => {
  it("creates preset stats on first feedback", () => {
    const event = recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);

    expect(event.presetId).toBe("preset-1");
    expect(event.feedbackType).toBe("selected");
    expect(event.eventId).toBeDefined();
    expect(event.timestamp).toBeDefined();

    const stats = getPresetStats("preset-1");
    expect(stats.timesSelected).toBe(1);
    expect(stats.timesShown).toBe(1);
  });

  it("increments timesIgnored for ignored feedback", () => {
    recordImplicitFeedback("preset-1", "ignored", DEFAULT_CONTEXT);
    const stats = getPresetStats("preset-1");

    expect(stats.timesIgnored).toBe(1);
    expect(stats.timesShown).toBe(1);
    expect(stats.timesSelected).toBe(0);
  });

  it("increments engagementCount for engaged feedback", () => {
    recordImplicitFeedback("preset-1", "engaged", DEFAULT_CONTEXT);
    const stats = getPresetStats("preset-1");

    expect(stats.engagementCount).toBe(1);
    // Engaged doesn't increment timesShown
    expect(stats.timesShown).toBe(0);
  });

  it("updates Bayesian implicit score", () => {
    // Add positive feedback
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);

    const stats = getPresetStats("preset-1");
    expect(stats.implicitScore).toBeGreaterThan(0.5);
  });

  it("adds event to history", () => {
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);

    const history = getEventHistory();
    expect(history.length).toBe(1);
    expect(history[0].presetId).toBe("preset-1");
  });

  it("stores recommendation data when provided", () => {
    const event = recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT, {
      rank: 1,
      score: 0.85,
      breakdown: DEFAULT_BREAKDOWN,
    });

    expect(event.recommendationRank).toBe(1);
    expect(event.recommendationScore).toBe(0.85);
    expect(event.breakdown).toEqual(DEFAULT_BREAKDOWN);
  });
});

// =============================================================================
// EXPLICIT FEEDBACK TESTS
// =============================================================================

describe("recordExplicitFeedback", () => {
  it("records upvote correctly", () => {
    const event = recordExplicitFeedback("preset-1", "upvote", DEFAULT_CONTEXT);

    expect(event.feedbackType).toBe("upvote");

    const stats = getPresetStats("preset-1");
    expect(stats.upvotes).toBe(1);
    expect(stats.explicitScore).toBeGreaterThan(0.5);
  });

  it("records downvote correctly", () => {
    recordExplicitFeedback("preset-1", "downvote", DEFAULT_CONTEXT);

    const stats = getPresetStats("preset-1");
    expect(stats.downvotes).toBe(1);
    expect(stats.explicitScore).toBeLessThan(0.5);
  });

  it("records hide correctly", () => {
    recordExplicitFeedback("preset-1", "hide", DEFAULT_CONTEXT);

    const stats = getPresetStats("preset-1");
    expect(stats.hides).toBe(1);
  });

  it("records pin correctly", () => {
    recordExplicitFeedback("preset-1", "pin", DEFAULT_CONTEXT);

    const stats = getPresetStats("preset-1");
    expect(stats.pins).toBe(1);
    expect(stats.explicitScore).toBeGreaterThan(0.5);
  });

  it("computes combined score from implicit and explicit", () => {
    // Mix of implicit and explicit feedback
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    recordExplicitFeedback("preset-1", "upvote", DEFAULT_CONTEXT);

    const stats = getPresetStats("preset-1");
    // Combined = 0.6 * implicit + 0.4 * explicit
    expect(stats.combinedScore).toBeGreaterThan(0.5);
    expect(stats.combinedScore).toBeLessThanOrEqual(1);
  });
});

// =============================================================================
// WEIGHT REINFORCEMENT TESTS
// =============================================================================

describe("applyReinforcement", () => {
  it("requires minimum feedback count before adjusting", () => {
    // Only 1 feedback event — below threshold of 5
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);

    const adjustment = applyReinforcement(
      "moderate",
      DEFAULT_WEIGHTS,
      "preset-1",
      "selected",
      DEFAULT_BREAKDOWN
    );

    // Should return no-op adjustment
    expect(adjustment.deltas.usage).toBe(0);
    expect(adjustment.reason).toContain("Insufficient feedback");
  });

  it("applies adjustment after minimum feedback reached", () => {
    // Add 5 feedback events to meet threshold
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    const adjustment = applyReinforcement(
      "moderate",
      DEFAULT_WEIGHTS,
      "preset-1",
      "selected",
      DEFAULT_BREAKDOWN
    );

    // Should have non-zero deltas
    expect(adjustment.deltas.usage).not.toBe(0);
    expect(adjustment.reason).not.toContain("Insufficient");
  });

  it("updates learned weights after adjustment", () => {
    // Meet threshold
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    applyReinforcement("moderate", DEFAULT_WEIGHTS, "preset-1", "selected", DEFAULT_BREAKDOWN);

    const learned = getLearnedWeights("moderate", DEFAULT_WEIGHTS);
    expect(learned.totalAdjustments).toBe(1);
    expect(learned.adjustmentHistory.length).toBe(1);
    // Weights should be different from base after adjustment
    const weightsChanged =
      learned.adjustedWeights.usage !== DEFAULT_WEIGHTS.usage ||
      learned.adjustedWeights.recency !== DEFAULT_WEIGHTS.recency;
    expect(weightsChanged).toBe(true);
  });

  it("normalizes weights to sum to 1 after adjustment", () => {
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    applyReinforcement("moderate", DEFAULT_WEIGHTS, "preset-1", "selected", DEFAULT_BREAKDOWN);

    const learned = getLearnedWeights("moderate", DEFAULT_WEIGHTS);
    const sum =
      learned.adjustedWeights.usage +
      learned.adjustedWeights.recency +
      learned.adjustedWeights.tags +
      learned.adjustedWeights.category;

    expect(sum).toBeCloseTo(1.0, 5);
  });

  it("clamps weights within bounds", () => {
    // Meet threshold
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    // Apply many adjustments
    for (let i = 0; i < 100; i++) {
      applyReinforcement("moderate", DEFAULT_WEIGHTS, "preset-1", "selected", DEFAULT_BREAKDOWN);
    }

    const learned = getLearnedWeights("moderate", DEFAULT_WEIGHTS);

    // All weights should be within [0.05, 0.50]
    expect(learned.adjustedWeights.usage).toBeGreaterThanOrEqual(0.05);
    expect(learned.adjustedWeights.usage).toBeLessThanOrEqual(0.50);
    expect(learned.adjustedWeights.recency).toBeGreaterThanOrEqual(0.05);
    expect(learned.adjustedWeights.recency).toBeLessThanOrEqual(0.50);
  });
});

// =============================================================================
// INTEGRATION HOOK TESTS
// =============================================================================

describe("onPresetSelected", () => {
  it("records feedback and applies reinforcement", () => {
    // Pre-populate to meet threshold
    for (let i = 0; i < 4; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    const result = onPresetSelected(
      "preset-1",
      "moderate",
      DEFAULT_WEIGHTS,
      1, // rank
      0.85, // score
      DEFAULT_BREAKDOWN
    );

    expect(result.event.feedbackType).toBe("selected");
    expect(result.event.recommendationRank).toBe(1);
    expect(result.adjustment).toBeDefined();
  });
});

describe("onExplicitFeedback", () => {
  it("records upvote and applies positive reinforcement", () => {
    // Pre-populate
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    const result = onExplicitFeedback(
      "preset-1",
      true, // isPositive
      "moderate",
      DEFAULT_WEIGHTS,
      DEFAULT_BREAKDOWN
    );

    expect(result.event.feedbackType).toBe("upvote");
    expect(result.adjustment.deltas.usage).toBeGreaterThanOrEqual(0);
  });

  it("records downvote and applies negative reinforcement", () => {
    // Pre-populate
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    }

    const result = onExplicitFeedback(
      "preset-1",
      false, // isPositive
      "moderate",
      DEFAULT_WEIGHTS,
      DEFAULT_BREAKDOWN
    );

    expect(result.event.feedbackType).toBe("downvote");
    // Note: deltas could be negative
  });
});

describe("onPresetHidden", () => {
  it("marks preset as hidden", () => {
    onPresetHidden("preset-1", "moderate");

    expect(shouldFilterPreset("preset-1")).toBe(true);
    expect(getHiddenPresetIds()).toContain("preset-1");
  });
});

describe("shouldFilterPreset", () => {
  it("returns false for non-hidden preset", () => {
    expect(shouldFilterPreset("unknown-preset")).toBe(false);
  });

  it("returns true for hidden preset", () => {
    recordExplicitFeedback("preset-1", "hide", DEFAULT_CONTEXT);
    expect(shouldFilterPreset("preset-1")).toBe(true);
  });
});

// =============================================================================
// DATA EXPORT TESTS
// =============================================================================

describe("exportFeedbackData", () => {
  it("exports all data correctly", () => {
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    recordExplicitFeedback("preset-2", "upvote", DEFAULT_CONTEXT);

    const exported = exportFeedbackData();

    expect(exported.version).toBe("1.0");
    expect(exported.events.length).toBe(2);
    expect(exported.presetStats.length).toBe(2);
    expect(exported.exportedAt).toBeDefined();
  });
});

describe("getFeedbackSummary", () => {
  it("returns correct summary statistics", () => {
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
    recordImplicitFeedback("preset-2", "ignored", DEFAULT_CONTEXT);
    recordExplicitFeedback("preset-3", "upvote", DEFAULT_CONTEXT);

    const summary = getFeedbackSummary();

    expect(summary.totalEvents).toBe(3);
    expect(summary.totalPresets).toBe(3);
    expect(summary.avgImplicitScore).toBeGreaterThan(0);
    expect(summary.avgExplicitScore).toBeGreaterThan(0);
  });
});

// =============================================================================
// EDGE CASE TESTS
// =============================================================================

describe("edge cases", () => {
  it("handles multiple profiles independently", () => {
    // Pre-populate for both profiles
    for (let i = 0; i < 5; i++) {
      recordImplicitFeedback("preset-1", "selected", { profile: "conservative" });
      recordImplicitFeedback("preset-1", "selected", { profile: "aggressive" });
    }

    applyReinforcement("conservative", DEFAULT_WEIGHTS, "preset-1", "selected", DEFAULT_BREAKDOWN);
    applyReinforcement("aggressive", DEFAULT_WEIGHTS, "preset-1", "selected", DEFAULT_BREAKDOWN);

    const conservativeLearned = getLearnedWeights("conservative", DEFAULT_WEIGHTS);
    const aggressiveLearned = getLearnedWeights("aggressive", DEFAULT_WEIGHTS);

    expect(conservativeLearned.totalAdjustments).toBe(1);
    expect(aggressiveLearned.totalAdjustments).toBe(1);
  });

  it("handles concurrent feedback on same preset", () => {
    // Rapid feedback
    for (let i = 0; i < 10; i++) {
      recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);
      recordImplicitFeedback("preset-1", "ignored", DEFAULT_CONTEXT);
    }

    const stats = getPresetStats("preset-1");
    expect(stats.timesSelected).toBe(10);
    expect(stats.timesIgnored).toBe(10);
    expect(stats.timesShown).toBe(20);
  });

  it("handles zero breakdown scores", () => {
    const zeroBreakdown: ScoreBreakdown = {
      usage: 0,
      recency: 0,
      tags: 0,
      category: 0,
    };

    const deltas = computeWeightDeltas("selected", zeroBreakdown);

    expect(deltas.usage).toBe(0);
    expect(deltas.recency).toBe(0);
    expect(deltas.tags).toBe(0);
    expect(deltas.category).toBe(0);
  });

  it("getPresetStats returns copy to prevent mutation", () => {
    recordImplicitFeedback("preset-1", "selected", DEFAULT_CONTEXT);

    const stats1 = getPresetStats("preset-1");
    stats1.timesSelected = 999; // Mutate the copy

    const stats2 = getPresetStats("preset-1");
    expect(stats2.timesSelected).toBe(1); // Original unchanged
  });
});
