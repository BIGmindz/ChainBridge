import { beforeEach, describe, expect, it, vi } from "vitest";

import { config } from "../config/env";
import { fetchMock, mockJsonResponse } from "../test/mockFetch";

import { apiClient, getApiClient, mockApiClient } from "./api";

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
      expect(shipments[0]).toHaveProperty("shipmentId");
      expect(shipments[0]).toHaveProperty("carrier");
      expect(shipments[0]).toHaveProperty("customer");
    });

    it("should return mock proof pack data from getProofPack()", async () => {
      const proofPack = await mockApiClient.getProofPack("ship_test_001");

      expect(proofPack).toHaveProperty("shipmentId");
      expect(proofPack).toHaveProperty("generatedAt");
      expect(proofPack).toHaveProperty("version");
      expect(proofPack.risk_snapshot).toBeTruthy();
    });

    it("should generate unique proof pack IDs", async () => {
      const pack1 = await mockApiClient.getProofPack("ship_alpha");
      const pack2 = await mockApiClient.getProofPack("ship_beta");

      expect(pack1.shipmentId).not.toBe(pack2.shipmentId);
    });

    it("should return mock vitals data from getNetworkVitals()", async () => {
      const vitals = await mockApiClient.getNetworkVitals();

      expect(vitals).toHaveProperty("active_shipments");
      expect(vitals).toHaveProperty("on_time_percent");
      expect(vitals).toHaveProperty("at_risk_shipments");
      expect(vitals).toHaveProperty("open_payment_holds");
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
      const mockShipments = await mockApiClient.getShipments();
      const responsePayload = mockShipments.slice(0, 1);

      fetchMock.mockImplementationOnce(() => mockJsonResponse(responsePayload));

      const shipments = await apiClient.getShipments();

      expect(Array.isArray(shipments)).toBe(true);
      expect(shipments).toHaveLength(1);
      expect(shipments[0]).toMatchObject({ shipmentId: responsePayload[0].shipmentId });
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/shipments"), expect.anything());
    });

    it("should have ProofPack methods", async () => {
      const mockProofPack = await mockApiClient.getProofPack("ship_test_123");

      fetchMock.mockImplementationOnce(() => mockJsonResponse(mockProofPack));

      const proofPack = await apiClient.getProofPack("ship_test_123");

      expect(proofPack).toEqual(mockProofPack);
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/proofpacks/"), expect.anything());
    });
  });
});
