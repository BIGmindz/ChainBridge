import { vi } from "vitest";

const defaultImplementation = () =>
  Promise.reject(new Error("Global fetch mock invoked without an implementation"));

type FetchType = typeof fetch;

type FetchParameters = Parameters<FetchType>;
type FetchReturn = ReturnType<FetchType>;

export const fetchMock = vi.fn(defaultImplementation);

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
