/**
 * MAGGIE PAC-004 — Weight Layering, KPIs & Sync Tests
 * ===================================================
 * Comprehensive tests for weight blending, KPI tracking, and sync infrastructure.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  blendWeights,
  getEffectiveWeights,
  invalidateWeightsCache,
  recordImpression,
  recordSelection,
  getKPIMetrics,
  getHitRates,
  resetKPIMetrics,
  syncToLocalStorage,
  loadFromLocalStorage,
  registerBackendSyncHook,
  registerSupabaseSyncHook,
  registerErrorHook,
  syncToBackend,
  syncToSupabase,
  getSyncState,
  buildAnalyticsExport,
  exportAnalyticsJSON,
  resetWeightSyncState,
  getInternalState,
  DEFAULT_BLEND_CONFIG,
  type LayerBlendConfig,
  type AnalyticsExport,
} from "./weightSync";
import type { ScoringWeights, RecommendationProfile } from "./presetRecommender";
import { getDefaultWeights } from "./presetRecommender";
import {
  recordImplicitFeedback,
  applyReinforcement,
  recordExplicitFeedback,
} from "./feedbackTracker";

// =============================================================================
// TEST SETUP
// =============================================================================

beforeEach(() => {
  resetWeightSyncState();
});

// =============================================================================
// WEIGHT BLENDING TESTS
// =============================================================================

describe("blendWeights", () => {
  const global: ScoringWeights = { usage: 0.25, recency: 0.30, tags: 0.30, category: 0.15 };
  const local: ScoringWeights = { usage: 0.35, recency: 0.25, tags: 0.25, category: 0.15 };

  it("blends weights with default alpha=0.7, beta=0.3", () => {
    const result = blendWeights(global, local);

    // effective = normalize(0.7 * global + 0.3 * local)
    // usage: 0.7 * 0.25 + 0.3 * 0.35 = 0.175 + 0.105 = 0.28
    // recency: 0.7 * 0.30 + 0.3 * 0.25 = 0.21 + 0.075 = 0.285
    // tags: 0.7 * 0.30 + 0.3 * 0.25 = 0.21 + 0.075 = 0.285
    // category: 0.7 * 0.15 + 0.3 * 0.15 = 0.105 + 0.045 = 0.15
    // Sum = 1.0 (already normalized)

    expect(result.usage).toBeCloseTo(0.28, 2);
    expect(result.recency).toBeCloseTo(0.285, 2);
    expect(result.tags).toBeCloseTo(0.285, 2);
    expect(result.category).toBeCloseTo(0.15, 2);

    // Must sum to 1
    const sum = result.usage + result.recency + result.tags + result.category;
    expect(sum).toBeCloseTo(1.0, 5);
  });

  it("blends with custom alpha=0.5, beta=0.5 (equal weight)", () => {
    const config: LayerBlendConfig = { alpha: 0.5, beta: 0.5 };
    const result = blendWeights(global, local, config);

    // Simple average
    expect(result.usage).toBeCloseTo(0.30, 2);      // (0.25 + 0.35) / 2 = 0.30
    expect(result.recency).toBeCloseTo(0.275, 2);   // (0.30 + 0.25) / 2 = 0.275
    expect(result.tags).toBeCloseTo(0.275, 2);      // (0.30 + 0.25) / 2 = 0.275
    expect(result.category).toBeCloseTo(0.15, 2);   // (0.15 + 0.15) / 2 = 0.15

    const sum = result.usage + result.recency + result.tags + result.category;
    expect(sum).toBeCloseTo(1.0, 5);
  });

  it("blends with alpha=1.0, beta=0.0 (pure global)", () => {
    const config: LayerBlendConfig = { alpha: 1.0, beta: 0.0 };
    const result = blendWeights(global, local, config);

    expect(result.usage).toBeCloseTo(global.usage, 5);
    expect(result.recency).toBeCloseTo(global.recency, 5);
    expect(result.tags).toBeCloseTo(global.tags, 5);
    expect(result.category).toBeCloseTo(global.category, 5);
  });

  it("blends with alpha=0.0, beta=1.0 (pure local)", () => {
    const config: LayerBlendConfig = { alpha: 0.0, beta: 1.0 };
    const result = blendWeights(global, local, config);

    expect(result.usage).toBeCloseTo(local.usage, 5);
    expect(result.recency).toBeCloseTo(local.recency, 5);
    expect(result.tags).toBeCloseTo(local.tags, 5);
    expect(result.category).toBeCloseTo(local.category, 5);
  });

  it("normalizes result when raw sum is not 1.0", () => {
    // Weights that don't sum to 1 before blending
    const unbalancedGlobal: ScoringWeights = { usage: 0.5, recency: 0.5, tags: 0.5, category: 0.5 };
    const unbalancedLocal: ScoringWeights = { usage: 0.3, recency: 0.3, tags: 0.3, category: 0.3 };

    const result = blendWeights(unbalancedGlobal, unbalancedLocal);

    const sum = result.usage + result.recency + result.tags + result.category;
    expect(sum).toBeCloseTo(1.0, 5);
    expect(result.usage).toBeCloseTo(0.25, 2); // All equal after normalization
  });

  it("handles zero weights gracefully", () => {
    const zeroGlobal: ScoringWeights = { usage: 0, recency: 0, tags: 0, category: 0 };
    const result = blendWeights(zeroGlobal, local);

    // Should still produce valid normalized weights
    const sum = result.usage + result.recency + result.tags + result.category;
    expect(sum).toBeCloseTo(1.0, 5);
  });
});

describe("getEffectiveWeights", () => {
  it("returns effective weights for moderate profile", () => {
    const effective = getEffectiveWeights("moderate");

    expect(effective.profile).toBe("moderate");
    expect(effective.globalWeights).toBeDefined();
    expect(effective.localWeights).toBeDefined();
    expect(effective.effectiveWeights).toBeDefined();
    expect(effective.blendConfig).toEqual(DEFAULT_BLEND_CONFIG);
    expect(effective.computedAt).toBeDefined();
  });

  it("returns effective weights for conservative profile", () => {
    const effective = getEffectiveWeights("conservative");
    expect(effective.profile).toBe("conservative");
    expect(effective.globalWeights.category).toBe(0.35); // Conservative has high category
  });

  it("returns effective weights for aggressive profile", () => {
    const effective = getEffectiveWeights("aggressive");
    expect(effective.profile).toBe("aggressive");
    expect(effective.globalWeights.tags).toBe(0.35); // Aggressive has high tags
  });

  it("caches results within TTL", () => {
    const first = getEffectiveWeights("moderate");
    const second = getEffectiveWeights("moderate");

    // Should be same timestamp (cached)
    expect(second.computedAt).toBe(first.computedAt);
  });

  it("respects cache invalidation", async () => {
    const first = getEffectiveWeights("moderate");
    invalidateWeightsCache("moderate");

    // Wait a tiny bit to ensure different timestamp
    await new Promise(resolve => setTimeout(resolve, 5));

    const second = getEffectiveWeights("moderate");
    // After invalidation, should recompute
    expect(second.computedAt).not.toBe(first.computedAt);
  });

  it("accepts custom blend config", () => {
    const customConfig: LayerBlendConfig = { alpha: 0.5, beta: 0.5 };
    const effective = getEffectiveWeights("moderate", customConfig);

    expect(effective.blendConfig).toEqual(customConfig);
  });

  it("reflects local adjustments after feedback", () => {
    const globalWeights = getDefaultWeights("moderate");
    const presetId = "feedback_test_preset";

    // Record feedback to single preset to accumulate count
    for (let i = 0; i < 10; i++) {
      recordImplicitFeedback(
        presetId,
        "selected",
        { profile: "moderate" },
        { rank: 1, score: 0.9, breakdown: { usage: 0.9, recency: 0.8, tags: 0.7, category: 0.6 } }
      );
    }

    // Now apply reinforcement (after meeting minimum threshold)
    applyReinforcement(
      "moderate",
      globalWeights,
      presetId,
      "selected",
      { usage: 0.9, recency: 0.8, tags: 0.7, category: 0.6 }
    );

    invalidateWeightsCache("moderate");
    const effective = getEffectiveWeights("moderate");

    expect(effective.localAdjustmentCount).toBeGreaterThan(0);
  });
});

// =============================================================================
// KPI TRACKING TESTS
// =============================================================================

describe("KPI Tracking", () => {
  describe("recordImpression", () => {
    it("increments impression count", () => {
      recordImpression(["preset1", "preset2", "preset3"]);

      const kpis = getKPIMetrics();
      expect(kpis.impressions).toBe(1);
    });

    it("tracks multiple impressions", () => {
      recordImpression(["preset1"]);
      recordImpression(["preset2"]);
      recordImpression(["preset3"]);

      const kpis = getKPIMetrics();
      expect(kpis.impressions).toBe(3);
    });

    it("stores timestamps for time-to-preset calculation", () => {
      recordImpression(["preset1", "preset2"]);

      const state = getInternalState();
      expect(state.impressionCount).toBe(2);
    });
  });

  describe("recordSelection", () => {
    it("updates CTR correctly", () => {
      recordImpression(["preset1", "preset2"]);
      recordSelection("preset1", 1);

      const kpis = getKPIMetrics();
      expect(kpis.selections).toBe(1);
      expect(kpis.ctr).toBe(1); // 1 selection / 1 impression = 1.0
    });

    it("calculates CTR across multiple impressions", () => {
      recordImpression(["preset1"]);
      recordImpression(["preset2"]);
      recordImpression(["preset3"]);
      recordSelection("preset2", 1);

      const kpis = getKPIMetrics();
      expect(kpis.ctr).toBeCloseTo(1/3, 5); // 1 selection / 3 impressions
    });

    it("tracks Hit@1 correctly", () => {
      recordImpression(["preset1", "preset2", "preset3"]);
      recordSelection("preset1", 1); // Rank 1

      const kpis = getKPIMetrics();
      expect(kpis.hitAt1).toBe(1);
      expect(kpis.hitAt3).toBe(1);
    });

    it("tracks Hit@3 correctly", () => {
      recordImpression(["preset1", "preset2", "preset3"]);
      recordSelection("preset3", 3); // Rank 3

      const kpis = getKPIMetrics();
      expect(kpis.hitAt1).toBe(0);
      expect(kpis.hitAt3).toBe(1);
    });

    it("does not count rank > 3 in Hit@3", () => {
      recordImpression(["preset1", "preset2", "preset3", "preset4"]);
      recordSelection("preset4", 4); // Rank 4

      const kpis = getKPIMetrics();
      expect(kpis.hitAt1).toBe(0);
      expect(kpis.hitAt3).toBe(0);
    });

    it("calculates time-to-preset", () => {
      // Simulate impression then delayed selection
      vi.useFakeTimers();

      recordImpression(["preset1"]);

      // Wait 500ms
      vi.advanceTimersByTime(500);

      recordSelection("preset1", 1);

      const kpis = getKPIMetrics();
      expect(kpis.avgTimeToPresetMs).toBeCloseTo(500, -1);
      expect(kpis.timeToPresetSamples.length).toBe(1);

      vi.useRealTimers();
    });

    it("averages multiple time-to-preset samples", () => {
      vi.useFakeTimers();

      recordImpression(["preset1"]);
      vi.advanceTimersByTime(100);
      recordSelection("preset1", 1);

      recordImpression(["preset2"]);
      vi.advanceTimersByTime(300);
      recordSelection("preset2", 1);

      const kpis = getKPIMetrics();
      expect(kpis.avgTimeToPresetMs).toBeCloseTo(200, -1); // (100 + 300) / 2
      expect(kpis.timeToPresetSamples.length).toBe(2);

      vi.useRealTimers();
    });
  });

  describe("getHitRates", () => {
    it("returns 0 when no selections", () => {
      const rates = getHitRates();
      expect(rates.hitRate1).toBe(0);
      expect(rates.hitRate3).toBe(0);
    });

    it("calculates hit rates correctly", () => {
      recordImpression(["p1"]);
      recordSelection("p1", 1);

      recordImpression(["p2"]);
      recordSelection("p2", 2);

      recordImpression(["p3"]);
      recordSelection("p3", 4);

      const rates = getHitRates();
      expect(rates.hitRate1).toBeCloseTo(1/3, 5); // 1 hit@1 / 3 selections
      expect(rates.hitRate3).toBeCloseTo(2/3, 5); // 2 hits@3 / 3 selections
    });
  });

  describe("resetKPIMetrics", () => {
    it("resets all KPI values", () => {
      recordImpression(["p1"]);
      recordSelection("p1", 1);

      resetKPIMetrics();

      const kpis = getKPIMetrics();
      expect(kpis.impressions).toBe(0);
      expect(kpis.selections).toBe(0);
      expect(kpis.ctr).toBe(0);
      expect(kpis.hitAt1).toBe(0);
      expect(kpis.hitAt3).toBe(0);
    });

    it("generates new session ID", () => {
      const before = getKPIMetrics().sessionId;
      resetKPIMetrics();
      const after = getKPIMetrics().sessionId;

      expect(after).not.toBe(before);
    });
  });
});

// =============================================================================
// SYNC INFRASTRUCTURE TESTS
// =============================================================================

describe("Sync Infrastructure", () => {
  describe("getSyncState", () => {
    it("returns initial sync state", () => {
      const state = getSyncState();

      expect(state.lastLocalStorageSync).toBeNull();
      expect(state.lastBackendSync).toBeNull();
      expect(state.lastSupabaseSync).toBeNull();
      expect(state.pendingChanges).toBe(0);
      expect(state.syncErrors).toHaveLength(0);
    });
  });

  describe("registerBackendSyncHook", () => {
    it("registers and calls backend sync hooks", async () => {
      const mockHook = vi.fn().mockResolvedValue(undefined);
      registerBackendSyncHook(mockHook);

      await syncToBackend();

      expect(mockHook).toHaveBeenCalledTimes(1);
      expect(mockHook).toHaveBeenCalledWith(expect.objectContaining({
        version: "1.0",
        presets: expect.any(Array),
        profiles: expect.any(Array),
        kpis: expect.any(Object),
      }));
    });

    it("updates lastBackendSync timestamp", async () => {
      const mockHook = vi.fn().mockResolvedValue(undefined);
      registerBackendSyncHook(mockHook);

      await syncToBackend();

      const state = getSyncState();
      expect(state.lastBackendSync).not.toBeNull();
    });

    it("records error when hook fails", async () => {
      const failingHook = vi.fn().mockRejectedValue(new Error("Backend error"));
      registerBackendSyncHook(failingHook);

      await syncToBackend();

      const state = getSyncState();
      expect(state.syncErrors.length).toBeGreaterThan(0);
      expect(state.syncErrors[0].layer).toBe("backend");
    });
  });

  describe("registerSupabaseSyncHook", () => {
    it("registers and calls supabase sync hooks", async () => {
      const mockHook = vi.fn().mockResolvedValue(undefined);
      registerSupabaseSyncHook(mockHook);

      await syncToSupabase();

      expect(mockHook).toHaveBeenCalledTimes(1);
    });

    it("updates lastSupabaseSync timestamp", async () => {
      const mockHook = vi.fn().mockResolvedValue(undefined);
      registerSupabaseSyncHook(mockHook);

      await syncToSupabase();

      const state = getSyncState();
      expect(state.lastSupabaseSync).not.toBeNull();
    });
  });

  describe("registerErrorHook", () => {
    it("calls error hooks on sync errors", async () => {
      const errorHandler = vi.fn();
      registerErrorHook(errorHandler);

      const failingHook = vi.fn().mockRejectedValue(new Error("Test error"));
      registerBackendSyncHook(failingHook);

      await syncToBackend();

      expect(errorHandler).toHaveBeenCalledWith(expect.objectContaining({
        layer: "backend",
        error: expect.stringContaining("Test error"),
      }));
    });
  });

  describe("localStorage sync", () => {
    beforeEach(() => {
      // Mock localStorage
      const store: Record<string, string> = {};
      vi.stubGlobal("window", {
        localStorage: {
          getItem: (key: string) => store[key] ?? null,
          setItem: (key: string, value: string) => { store[key] = value; },
          removeItem: (key: string) => { delete store[key]; },
          key: (i: number) => Object.keys(store)[i] ?? null,
          get length() { return Object.keys(store).length; },
          clear: () => { Object.keys(store).forEach(k => delete store[k]); },
        },
      });
    });

    it("syncs to localStorage", () => {
      recordImpression(["p1"]);
      recordSelection("p1", 1);

      syncToLocalStorage();

      const state = getSyncState();
      expect(state.lastLocalStorageSync).not.toBeNull();
    });

    it("loads from localStorage", () => {
      recordImpression(["p1"]);
      recordSelection("p1", 1);
      syncToLocalStorage();

      // Reset in-memory state
      resetKPIMetrics();
      expect(getKPIMetrics().selections).toBe(0);

      // Load from storage
      const loaded = loadFromLocalStorage();
      expect(loaded).toBe(true);
      // Note: sessionId is preserved from reset, but other values loaded
    });
  });
});

// =============================================================================
// ANALYTICS EXPORT TESTS
// =============================================================================

describe("Analytics Export", () => {
  describe("buildAnalyticsExport", () => {
    it("exports all required fields", () => {
      const exported = buildAnalyticsExport();

      expect(exported.exportedAt).toBeDefined();
      expect(exported.version).toBe("1.0");
      expect(exported.presets).toBeInstanceOf(Array);
      expect(exported.profiles).toBeInstanceOf(Array);
      expect(exported.kpis).toBeDefined();
      expect(exported.feedbackExport).toBeDefined();
    });

    it("includes all three profiles", () => {
      const exported = buildAnalyticsExport();

      const profileNames = exported.profiles.map(p => p.profile);
      expect(profileNames).toContain("conservative");
      expect(profileNames).toContain("moderate");
      expect(profileNames).toContain("aggressive");
    });

    it("includes per-preset data when feedback exists", () => {
      recordImplicitFeedback(
        "test_preset",
        "selected",
        { profile: "moderate" },
        { rank: 1, score: 0.8, breakdown: { usage: 0.8, recency: 0.7, tags: 0.9, category: 0.6 } }
      );

      const exported = buildAnalyticsExport();

      const presetData = exported.presets.find(p => p.presetId === "test_preset");
      expect(presetData).toBeDefined();
      expect(presetData?.clicks).toBe(1);
      expect(presetData?.posterior).toBeDefined();
    });

    it("includes KPI metrics", () => {
      recordImpression(["p1"]);
      recordSelection("p1", 1);

      const exported = buildAnalyticsExport();

      expect(exported.kpis.impressions).toBe(1);
      expect(exported.kpis.selections).toBe(1);
      expect(exported.kpis.ctr).toBe(1);
    });

    it("includes votes in preset data", () => {
      // Record implicit feedback first
      recordImplicitFeedback(
        "voted_preset",
        "selected",
        { profile: "moderate" }
      );

      // Record explicit votes
      recordExplicitFeedback("voted_preset", "upvote", { profile: "moderate" });
      recordExplicitFeedback("voted_preset", "downvote", { profile: "moderate" });

      const exported = buildAnalyticsExport();
      const presetData = exported.presets.find(p => p.presetId === "voted_preset");

      expect(presetData?.votes.up).toBe(1);
      expect(presetData?.votes.down).toBe(1);
    });
  });

  describe("exportAnalyticsJSON", () => {
    it("returns valid JSON string", () => {
      const json = exportAnalyticsJSON();

      expect(() => JSON.parse(json)).not.toThrow();
    });

    it("contains formatted output", () => {
      const json = exportAnalyticsJSON();

      // Should have indentation (pretty printed)
      expect(json).toContain("\n");
    });

    it("parses back to AnalyticsExport structure", () => {
      const json = exportAnalyticsJSON();
      const parsed: AnalyticsExport = JSON.parse(json);

      expect(parsed.version).toBe("1.0");
      expect(parsed.presets).toBeInstanceOf(Array);
      expect(parsed.profiles).toBeInstanceOf(Array);
    });
  });
});

// =============================================================================
// RESET & STATE TESTS
// =============================================================================

describe("Reset & State", () => {
  describe("resetWeightSyncState", () => {
    it("clears all state", () => {
      recordImpression(["p1"]);
      recordSelection("p1", 1);

      resetWeightSyncState();

      const kpis = getKPIMetrics();
      expect(kpis.impressions).toBe(0);
      expect(kpis.selections).toBe(0);

      const state = getSyncState();
      expect(state.pendingChanges).toBe(0);
      expect(state.syncErrors).toHaveLength(0);
    });

    it("clears registered hooks", async () => {
      const mockHook = vi.fn().mockResolvedValue(undefined);
      registerBackendSyncHook(mockHook);

      resetWeightSyncState();

      await syncToBackend();
      expect(mockHook).not.toHaveBeenCalled();
    });
  });

  describe("getInternalState", () => {
    it("reports impression timestamps", () => {
      recordImpression(["p1", "p2"]);

      const state = getInternalState();
      expect(state.impressionCount).toBe(2);
    });

    it("reports cached profile count", () => {
      getEffectiveWeights("moderate");
      getEffectiveWeights("aggressive");

      const state = getInternalState();
      expect(state.cachedProfileCount).toBe(2);
    });
  });
});

// =============================================================================
// EDGE CASES
// =============================================================================

describe("Edge Cases", () => {
  it("handles selection without prior impression", () => {
    // No impression recorded
    recordSelection("unknown_preset", 1);

    const kpis = getKPIMetrics();
    expect(kpis.selections).toBe(1);
    expect(kpis.ctr).toBe(0); // 0 impressions
    expect(kpis.avgTimeToPresetMs).toBe(0); // No time sample
  });

  it("handles very large number of impressions", () => {
    for (let i = 0; i < 1000; i++) {
      recordImpression([`preset_${i}`]);
    }

    const kpis = getKPIMetrics();
    expect(kpis.impressions).toBe(1000);
  });

  it("handles concurrent profile weight queries", () => {
    const profiles: RecommendationProfile[] = ["conservative", "moderate", "aggressive"];
    const results = profiles.map(p => getEffectiveWeights(p));

    expect(results.length).toBe(3);
    results.forEach(r => {
      const sum = r.effectiveWeights.usage + r.effectiveWeights.recency +
                  r.effectiveWeights.tags + r.effectiveWeights.category;
      expect(sum).toBeCloseTo(1.0, 5);
    });
  });

  it("preserves weight bounds after blending extreme values", () => {
    const extreme: ScoringWeights = { usage: 1.0, recency: 0, tags: 0, category: 0 };
    const result = blendWeights(extreme, extreme);

    // All weight should go to usage, but normalized
    expect(result.usage).toBeCloseTo(1.0, 5);
    expect(result.recency).toBeCloseTo(0, 5);
  });

  it("DEFAULT_BLEND_CONFIG sums to 1.0", () => {
    expect(DEFAULT_BLEND_CONFIG.alpha + DEFAULT_BLEND_CONFIG.beta).toBeCloseTo(1.0, 5);
  });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe("Integration", () => {
  it("full workflow: impression → selection → sync → export", async () => {
    vi.useFakeTimers();

    // Setup sync hook
    const syncedData: AnalyticsExport[] = [];
    registerBackendSyncHook(async (data) => {
      syncedData.push(data);
    });

    // Record activity
    recordImpression(["preset_a", "preset_b", "preset_c"]);
    vi.advanceTimersByTime(250);
    recordSelection("preset_b", 2);

    // Sync
    await syncToBackend();

    // Verify
    expect(syncedData.length).toBe(1);
    expect(syncedData[0].kpis.impressions).toBe(1);
    expect(syncedData[0].kpis.selections).toBe(1);
    expect(syncedData[0].kpis.hitAt3).toBe(1);

    vi.useRealTimers();
  });

  it("weight evolution through feedback cycle", () => {
    const profile: RecommendationProfile = "moderate";
    const baseWeights = getDefaultWeights(profile);
    const presetId = "evolution_test_preset";

    // Initial effective weights
    const initial = getEffectiveWeights(profile);
    expect(initial.localAdjustmentCount).toBe(0);

    // Simulate feedback cycle - record feedback to single preset to accumulate count
    for (let i = 0; i < 10; i++) {
      recordImplicitFeedback(
        presetId,
        "selected",
        { profile },
        {
          rank: 1,
          score: 0.85,
          breakdown: { usage: 0.3, recency: 0.9, tags: 0.8, category: 0.4 }
        }
      );
    }

    // Now apply reinforcement (after meeting minimum feedback threshold of 5)
    applyReinforcement(
      profile,
      baseWeights,
      presetId,
      "selected",
      { usage: 0.3, recency: 0.9, tags: 0.8, category: 0.4 }
    );

    // Check evolution
    invalidateWeightsCache(profile);
    const evolved = getEffectiveWeights(profile);

    expect(evolved.localAdjustmentCount).toBeGreaterThan(0);
    // Weights should have shifted slightly toward high recency (which scored 0.9)
  });
});
