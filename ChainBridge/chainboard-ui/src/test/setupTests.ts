import { afterAll, beforeAll, beforeEach, vi } from "vitest";

import { fetchMock, resetFetchMock } from "./mockFetch";

beforeAll(() => {
  vi.stubGlobal("fetch", fetchMock);
});

beforeEach(() => {
  resetFetchMock();
});

afterAll(() => {
  vi.unstubAllGlobals();
});
