import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChainboardAPI } from "../../core/api/client";
import { cacheStore } from "../../core/cache";
import type { AgentHealthSummary } from "../../core/types/agents";
import { useAgentHealth } from "../useAgentHealth";

describe("AgentHealth hook", () => {
  const mockSummary: AgentHealthSummary = {
    total: 12,
    valid: 10,
    invalid: 2,
    invalidRoles: ["AI_AGENT_TIM", "ML_PLATFORM_ENGINEER"],
  };

  beforeEach(() => {
    cacheStore.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns agent health data including invalid roles", async () => {
    vi.spyOn(ChainboardAPI, "getAgentHealthSummary").mockResolvedValue(mockSummary);

    const { result } = renderHook(() => useAgentHealth());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.data).toEqual(mockSummary);
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("exposes error state and recovers on refetch", async () => {
    const failingSpy = vi
      .spyOn(ChainboardAPI, "getAgentHealthSummary")
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(mockSummary);

    const { result } = renderHook(() => useAgentHealth());

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });

    await act(async () => {
      await result.current.refetch();
    });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockSummary);
      expect(result.current.error).toBeNull();
    });

    expect(failingSpy).toHaveBeenCalledTimes(2);
  });
});
