/**
 * Core HTTP Client
 *
 * Strongly-typed fetch wrapper with:
 * - Automatic JSON parsing
 * - Timeout support (8s default)
 * - Global error typing
 * - Base URL configuration
 * - Request logging (DEV only)
 */

import { config } from "../../config/env";

const DEFAULT_TIMEOUT = 8000; // 8 seconds
const BASE_URL = config.apiBaseUrl || "http://localhost:8000";

export class HttpError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: unknown
  ) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = "HttpError";
  }
}

export class TimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`Request timeout after ${timeoutMs}ms`);
    this.name = "TimeoutError";
  }
}

export interface HttpOptions extends RequestInit {
  timeout?: number;
  baseUrl?: string;
}

/**
 * Strongly-typed HTTP request wrapper.
 *
 * @param path - API path (without base URL)
 * @param options - Fetch options + timeout
 * @returns Parsed JSON response
 * @throws HttpError on non-2xx responses
 * @throws TimeoutError on timeout
 */
export async function http<T>(
  path: string,
  options: HttpOptions = {}
): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, baseUrl = BASE_URL, ...fetchOptions } = options;

  const url = path.startsWith("http") ? path : `${baseUrl}${path}`;

  if (import.meta.env.DEV) {
    console.log(`[http] ${fetchOptions.method || "GET"} ${url}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        body = await response.text();
      }

      throw new HttpError(response.status, response.statusText, body);
    }

    const data = (await response.json()) as T;

    if (import.meta.env.DEV) {
      console.log(`[http] ✓ ${url}`, data);
    }

    return data;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof HttpError) {
      throw error;
    }

    if ((error as Error).name === "AbortError") {
      throw new TimeoutError(timeout);
    }

    if (import.meta.env.DEV) {
      console.error(`[http] ✗ ${url}`, error);
    }

    throw error;
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const httpClient = {
  get: <T>(path: string, options?: HttpOptions) =>
    http<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: HttpOptions) =>
    http<T>(path, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    }),

  put: <T>(path: string, body?: unknown, options?: HttpOptions) =>
    http<T>(path, {
      ...options,
      method: "PUT",
      body: JSON.stringify(body),
    }),

  delete: <T>(path: string, options?: HttpOptions) =>
    http<T>(path, { ...options, method: "DELETE" }),
};
