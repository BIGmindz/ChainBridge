import { describe, expect, it } from "vitest";
import livePositionsFixture from "../__fixtures__/live_positions_response.json";
import ocIntelFixture from "../__fixtures__/oc_intel_response.json";
import {
    LivePositionsMeta,
    LiveShipmentPosition,
    OCIntelFeedResponse,
    OCQueueCardMeta,
} from "../types/chainbridge";

function isLivePositionsMeta(value: unknown): value is LivePositionsMeta {
  const v = value as LivePositionsMeta;
  return (
    typeof value === "object" &&
    value !== null &&
    typeof v.activeShipments === "number" &&
    typeof v.corridorsCovered === "number" &&
    typeof v.portsCovered === "number"
  );
}

function isOCQueueCardMeta(value: unknown): value is OCQueueCardMeta {
  const v = value as OCQueueCardMeta;
  return (
    typeof value === "object" &&
    value !== null &&
    typeof v.shipmentId === "string" &&
    typeof v.corridorId === "string" &&
    (typeof v.mode === "string" || v.mode === null) &&
    (typeof v.riskBand === "string" || v.riskBand === null) &&
    (typeof v.settlementState === "string" || v.settlementState === null) &&
    (typeof v.etaIso === "string" || v.etaIso === null) &&
    (typeof v.nearestPort === "string" || v.nearestPort === null)
  );
}

function isLiveShipmentPosition(value: unknown): value is LiveShipmentPosition {
  const v = value as LiveShipmentPosition;
  // Basic check for required fields in the fixture
  return (
    typeof value === "object" &&
    value !== null &&
    typeof v.shipmentId === "string" &&
    (typeof v.corridorId === "string" || v.corridorId === undefined)
  );
}

describe("OC Intel contract", () => {
  it("matches OCIntelFeedResponse structure", () => {
    const data = ocIntelFixture as unknown as OCIntelFeedResponse;

    expect(Array.isArray(data.queueCards)).toBe(true);
    data.queueCards.forEach((card) => {
      expect(isOCQueueCardMeta(card)).toBe(true);
    });

    expect(isLivePositionsMeta(data.livePositionsMeta)).toBe(true);
    expect(data.livePositionsMeta.activeShipments).toBeGreaterThanOrEqual(0);
  });

  it("matches LiveShipmentPosition structure", () => {
      const data = livePositionsFixture as unknown as LiveShipmentPosition[];
      expect(Array.isArray(data)).toBe(true);
      data.forEach(pos => {
          expect(isLiveShipmentPosition(pos)).toBe(true);
      })
  })
});
