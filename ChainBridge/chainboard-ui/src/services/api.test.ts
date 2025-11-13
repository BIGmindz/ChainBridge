import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient, getApiClient, mockApiClient } from "./api";
import { config } from "../config/env";

/**
 * API Service Tests
 *
 * Tests the API client factory, mock client, and integration with config.
 */

describe("API Client Factory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getApiClient()", () => {
    it("should return mockApiClient when useMocks is true", () => {
      // When using mocks (default in tests)
      const client = getApiClient();

      // Verify it has the expected methods
      expect(client).toHaveProperty("getNetworkVitals");
      expect(client).toHaveProperty("getExceptions");
      expect(client).toHaveProperty("getShipments");
      expect(client).toHaveProperty("getShipmentDetail");
      expect(client).toHaveProperty("getProofPack");
      expect(client).toHaveProperty("createProofPack");
    });

    it("should have consistent API client interface", () => {
      const client = getApiClient();

      // All methods should be functions
      expect(typeof client.getNetworkVitals).toBe("function");
      expect(typeof client.getExceptions).toBe("function");
      expect(typeof client.getShipments).toBe("function");
      expect(typeof client.getShipmentDetail).toBe("function");
      expect(typeof client.getProofPack).toBe("function");
      expect(typeof client.createProofPack).toBe("function");
    });
  });

  describe("MockApiClient", () => {
    it("should return mock shipment data from getShipments()", async () => {
      const shipments = await mockApiClient.getShipments();

      expect(Array.isArray(shipments)).toBe(true);
      expect(shipments.length).toBeGreaterThan(0);
      expect(shipments[0]).toHaveProperty("shipment_id");
      expect(shipments[0]).toHaveProperty("carrier");
      expect(shipments[0]).toHaveProperty("customer");
    });

    it("should return mock proof pack data from getProofPack()", async () => {
      const proofPack = await mockApiClient.getProofPack("pp_test_001");

      expect(proofPack).toHaveProperty("pack_id");
      expect(proofPack).toHaveProperty("shipment_id");
      expect(proofPack).toHaveProperty("generated_at");
      expect(proofPack).toHaveProperty("manifest_hash");
      expect(proofPack).toHaveProperty("status");
      expect(
        ["SUCCESS", "ERROR", "PENDING"].includes(proofPack.status)
      ).toBe(true);
    });

    it("should generate unique proof pack IDs", async () => {
      const pack1 = await mockApiClient.getProofPack("pp_001");
      const pack2 = await mockApiClient.getProofPack("pp_002");

      expect(pack1.pack_id).not.toBe(pack2.pack_id);
    });

    it("should return mock vitals data from getNetworkVitals()", async () => {
      const vitals = await mockApiClient.getNetworkVitals();

      expect(vitals).toHaveProperty("total_shipments");
      expect(vitals).toHaveProperty("in_transit");
      expect(vitals).toHaveProperty("delayed");
      expect(vitals).toHaveProperty("delivered");
      expect(vitals).toHaveProperty("flagged_for_review");
    });
  });

  describe("Config Integration", () => {
    it("should have config object with correct properties", () => {
      expect(config).toHaveProperty("apiBaseUrl");
      expect(config).toHaveProperty("useMocks");
      expect(config).toHaveProperty("environmentLabel");
      expect(config).toHaveProperty("isDevelopment");
      expect(config).toHaveProperty("isProduction");
    });

    it("should have valid apiBaseUrl", () => {
      expect(typeof config.apiBaseUrl).toBe("string");
      expect(config.apiBaseUrl.startsWith("http")).toBe(true);
    });

    it("should have useMocks as boolean", () => {
      expect(typeof config.useMocks).toBe("boolean");
    });
  });

  describe("apiClient (default export)", () => {
    it("should be a valid API client instance", async () => {
      // Get a shipment via the default client
      const shipments = await apiClient.getShipments();

      expect(Array.isArray(shipments)).toBe(true);
      expect(shipments.length).toBeGreaterThan(0);
    });

    it("should have ProofPack methods", async () => {
      // Test that proof pack methods exist and work
      const proofPack = await apiClient.getProofPack("pp_test_123");

      expect(proofPack).toHaveProperty("pack_id");
      expect(proofPack).toHaveProperty("manifest_hash");
      expect(proofPack.status).toBeDefined();
    });
  });
});
