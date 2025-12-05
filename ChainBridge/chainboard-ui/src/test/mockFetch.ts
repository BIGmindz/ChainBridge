import { vi } from "vitest";

type FetchType = typeof fetch;

const defaultImplementation: FetchType = () =>
  Promise.reject(new Error("Global fetch mock invoked without an implementation"));

export const fetchMock = vi.fn<FetchType>().mockImplementation(defaultImplementation);

export function resetFetchMock(): void {
  fetchMock.mockReset();
  fetchMock.mockImplementation(defaultImplementation);
}

export function mockJsonResponse<T>(data: T, init?: ResponseInit): Promise<Response> {
  const headers = new Headers(init?.headers || {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const responseInit: ResponseInit = {
    status: init?.status ?? 200,
    statusText: init?.statusText,
    headers,
  };

  return Promise.resolve(new Response(JSON.stringify(data), responseInit));
}
