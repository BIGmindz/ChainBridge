/**
 * Environment Configuration
 *
 * Centralizes access to environment variables with validation,
 * defaults, and type safety.
 *
 * Supports:
 * - VITE_API_BASE_URL: Backend API endpoint
 * - VITE_USE_MOCKS: Force mock data (overrides API_BASE_URL)
 * - VITE_ENVIRONMENT_LABEL: Environment badge label
 */

/**
 * Get the API base URL from environment.
 *
 * Priority:
 * 1. VITE_API_BASE_URL env variable
 * 2. Default: http://127.0.0.1:8000 (local dev)
 *
 * Logs warning in dev if unset.
 */
export function getApiBaseUrl(): string {
  const url = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  if (!import.meta.env.VITE_API_BASE_URL && import.meta.env.DEV) {
    console.warn(
      "⚠️  VITE_API_BASE_URL not set. Using default: http://127.0.0.1:8000"
    );
  }

  return url;
}

/**
 * Check if mocks should be used regardless of API availability.
 *
 * Priority:
 * 1. VITE_USE_MOCKS = "true"
 * 2. Default: false (use real API)
 *
 * Useful for:
 * - Offline development
 * - Demo mode
 * - Testing without backend
 */
export function shouldUseMocks(): boolean {
  return import.meta.env.VITE_USE_MOCKS === "true";
}

/**
 * Get the environment label for UI display.
 *
 * Priority:
 * 1. VITE_ENVIRONMENT_LABEL env variable
 * 2. API_BASE_URL detection (localhost → "Sandbox", otherwise → "Production")
 * 3. Default: "Development"
 */
export function getEnvironmentLabel(): string {
  if (import.meta.env.VITE_ENVIRONMENT_LABEL) {
    return import.meta.env.VITE_ENVIRONMENT_LABEL;
  }

  const apiUrl = getApiBaseUrl();
  if (apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1")) {
    return "Sandbox";
  }

  return "Production";
}

/**
 * Configuration object bundling all env settings.
 *
 * Usage:
 *   import { config } from '@/config/env';
 *   console.log(config.apiBaseUrl);
 */
export const config = {
  apiBaseUrl: getApiBaseUrl(),
  useMocks: shouldUseMocks(),
  environmentLabel: getEnvironmentLabel(),
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
} as const;

/**
 * Feature flags for progressive rollout.
 */
export const FEATURES = {
  insightsFeed: true, // ChainIQ risk stories feed
  shipmentIntelligence: true, // Unified shipment detail intelligence
  notifications: true, // Toast notification system
} as const;

/**
 * Log configuration status (dev only).
 */
if (import.meta.env.DEV) {
  console.log(
    `🔧 ChainBridge UI Configuration:
  - API Base URL: ${config.apiBaseUrl}
  - Use Mocks: ${config.useMocks}
  - Environment: ${config.environmentLabel}
  - Mode: ${config.isDevelopment ? "DEV" : "PROD"}`
  );
}
