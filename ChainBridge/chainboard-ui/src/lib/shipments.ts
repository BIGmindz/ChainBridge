/**
 * Shipment helpers + legacy mappers.
 * Keep all conversion logic here so services/components stay lean.
 */

import { classifyCorridor } from "../utils/corridors";
import type { CorridorId } from "../utils/corridors";

import { formatHoursAsAge, formatLane } from "./formatters";
import type {
  Shipment,
  ShipmentEvent as CanonicalShipmentEvent,
  PaymentMilestone as CanonicalPaymentMilestone,
  PaymentState,
  ShipmentStatus,
  RiskCategory,
  ExceptionRow,
  ExceptionCode,
  FreightMode,
} from "./types";

export type ProofpackStatus = "VERIFIED" | "FAILED" | "PENDING";

export interface LegacyShipmentEvent {
  eventType: string;
  timestamp: string;
}

export interface LegacyRiskAssessment {
  riskScore: number;
  riskCategory: RiskCategory;
  recommended_action: string;
  confidence: number;
}

export interface LegacyPaymentMilestone {
  milestone: string;
  percentage: number;
  status: "released" | "pending" | "blocked";
  amount_usd: number;
  released_at?: string;
}

export interface LegacyProofPackSummary {
  pack_id: string;
  manifest_hash: string;
  signature_status: ProofpackStatus;
  createdAt: string;
}

export interface LegacyShipment {
  shipmentId: string;
  token_id: string;
  carrier: string;
  customer: string;
  origin: string;
  destination: string;
  current_status: ShipmentStatus;
  current_event: string;
  last_update_timestamp: string;
  createdAt: string;
  events: LegacyShipmentEvent[];
  risk: LegacyRiskAssessment;
  payment_state: PaymentState;
  payment_schedule: LegacyPaymentMilestone[];
  total_valueUsd: number;
  proofpack: LegacyProofPackSummary;
}

export interface CreateProofPackPayload {
  shipmentId: string;
  events: LegacyShipmentEvent[];
  riskScore?: number;
  policy_version?: string;
}

export interface ShipmentsFilter {
  corridorId?: CorridorId;
  riskCategory?: RiskCategory;
  paymentState?: PaymentState;
  hasIoT?: boolean;
}

export interface ExceptionsFilter {
  corridorId?: CorridorId;
  severity?: RiskCategory;
  acknowledged?: boolean;
}

export function toCanonicalShipment(legacy: LegacyShipment): Shipment {
  const events = legacy.events.map((event) => toCanonicalShipmentEvent(event, legacy));
  const milestones = legacy.payment_schedule.map((milestone, index) =>
    toCanonicalPaymentMilestone(milestone, legacy.shipmentId, index)
  );
  const releasedPercentage = calculateReleasedPercentage(milestones);
  const totalValueUsd = legacy.total_valueUsd;
  const releasedUsd = Math.round((totalValueUsd * releasedPercentage) / 100);

  return {
    id: legacy.shipmentId,
    reference: legacy.token_id,
    status: legacy.current_status,
    origin: legacy.origin,
    destination: legacy.destination,
    corridor: formatLane(legacy.origin, legacy.destination),
    carrier: legacy.carrier,
    customer: legacy.customer,
    freight: {
      mode: inferFreightMode(legacy),
      incoterm: "FOB",
      vessel: `Vessel-${legacy.shipmentId.slice(-4)}`,
      container: legacy.token_id,
      lane: formatLane(legacy.origin, legacy.destination),
      departure: legacy.createdAt,
      eta: events.length > 0 ? events[events.length - 1].at : legacy.last_update_timestamp,
      events,
    },
    risk: {
      score: legacy.risk.riskScore,
      category: legacy.risk.riskCategory,
      drivers: [legacy.risk.recommended_action],
      assessed_at: legacy.last_update_timestamp,
      watchlisted: legacy.risk.riskCategory === "high",
    },
    payment: {
      state: legacy.payment_state,
      total_valueUsd: totalValueUsd,
      released_usd: releasedUsd,
      released_percentage: releasedPercentage,
      holds_usd: legacy.payment_state === "blocked" ? Math.round(totalValueUsd * 0.35) : 0,
      milestones,
      updatedAt: legacy.last_update_timestamp,
    },
    governance: {
      proofpack_status: legacy.proofpack.signature_status,
      last_audit: legacy.proofpack.createdAt,
      exceptions: deriveGovernanceExceptions(legacy),
    },
  };
}

export function toCanonicalShipments(source: LegacyShipment[]): Shipment[] {
  return source.map(toCanonicalShipment);
}

export function legacyShipmentToExceptionRow(shipment: LegacyShipment): ExceptionRow {
  const hoursAgo =
    (Date.now() - new Date(shipment.last_update_timestamp).getTime()) / 3600000;

  return {
    shipmentId: shipment.shipmentId,
    lane: formatLane(shipment.origin, shipment.destination),
    current_status: shipment.current_status,
    riskScore: shipment.risk.riskScore,
    payment_state: shipment.payment_state,
    age_of_issue: formatHoursAsAge(hoursAgo),
    issue_types: [],
    last_update: new Date(shipment.last_update_timestamp).toISOString(),
  };
}

export function filterShipments(
  shipments: Shipment[],
  filters?: ShipmentsFilter
): Shipment[] {
  if (!filters) return shipments;

  return shipments.filter((shipment) => {
    if (filters.corridorId) {
      const { id } = classifyCorridor({
        origin: shipment.origin,
        destination: shipment.destination,
      });
      if (id !== filters.corridorId) {
        return false;
      }
    }

    if (filters.riskCategory && shipment.risk.category !== filters.riskCategory) {
      return false;
    }

    if (filters.paymentState && shipment.payment.state !== filters.paymentState) {
      return false;
    }

    if (filters.hasIoT !== undefined) {
      const hasIoT = hasIoTSensors(shipment);
      if (filters.hasIoT !== hasIoT) {
        return false;
      }
    }

    return true;
  });
}

export function filterExceptionsBySeverity(
  exceptions: ExceptionRow[],
  filters?: ExceptionsFilter
): ExceptionRow[] {
  if (!filters) return exceptions;

  return exceptions.filter((exception) => {
    if (filters.corridorId) {
      const [originRaw, destinationRaw] = exception.lane.split("→").map((token) => token.trim());
      const { id } = classifyCorridor({
        origin: originRaw ?? "",
        destination: destinationRaw ?? "",
      });
      if (id !== filters.corridorId) {
        return false;
      }
    }

    if (filters.severity) {
      const severity: RiskCategory =
        exception.riskScore >= 70
          ? "high"
          : exception.riskScore >= 35
            ? "medium"
            : "low";
      if (severity !== filters.severity) {
        return false;
      }
    }

    if (filters.acknowledged === true) {
      // Mock data does not yet track acknowledgment state.
      return false;
    }

    return true;
  });
}

export function hasIoTSensors(shipment: Shipment): boolean {
  return shipment.freight.events.length >= 4;
}

function toCanonicalShipmentEvent(
  event: LegacyShipmentEvent,
  shipment: LegacyShipment
): CanonicalShipmentEvent {
  const descriptions: Record<string, string> = {
    pickup: "Pickup confirmed",
    in_transit: "Shipment in transit",
    delivery: "Delivery event",
    order_placed: "Order placed",
    pickup_scheduled: "Pickup scheduled",
  };

  const location =
    event.eventType === "pickup"
      ? shipment.origin
      : event.eventType === "delivery"
        ? shipment.destination
        : formatLane(shipment.origin, shipment.destination);

  return {
    code: event.eventType,
    description: descriptions[event.eventType] ?? event.eventType,
    at: event.timestamp,
    location,
  };
}

function toCanonicalPaymentMilestone(
  milestone: LegacyPaymentMilestone,
  shipmentId: string,
  index: number
): CanonicalPaymentMilestone {
  let state: CanonicalPaymentMilestone["state"] = "pending";
  if (milestone.status === "released") {
    state = "released";
  } else if (milestone.status === "blocked") {
    state = "blocked";
  }

  return {
    milestone_id: `${shipmentId}-${index}`,
    label: milestone.milestone,
    percentage: milestone.percentage,
    state,
    released_at: milestone.released_at,
  };
}

function calculateReleasedPercentage(
  milestones: CanonicalPaymentMilestone[]
): number {
  return milestones
    .filter((milestone) => milestone.state === "released")
    .reduce((sum, milestone) => sum + milestone.percentage, 0);
}

function inferFreightMode(shipment: LegacyShipment): FreightMode {
  const origin = shipment.origin.toLowerCase();
  const destination = shipment.destination.toLowerCase();
  const oceanIndicators = ["shanghai", "singapore", "rotterdam", "hamburg"];
  const airIndicators = ["airport", "air", "intl", "express"];

  if (oceanIndicators.some((token) => origin.includes(token) || destination.includes(token))) {
    return "ocean";
  }

  if (airIndicators.some((token) => origin.includes(token) || destination.includes(token))) {
    return "air";
  }

  if (origin.includes("los angeles") && destination.includes("houston")) {
    return "ground";
  }

  return "ground";
}

function deriveGovernanceExceptions(shipment: LegacyShipment): ExceptionCode[] {
  const exceptions: ExceptionCode[] = [];

  if (shipment.risk.riskCategory === "high") {
    exceptions.push("risk_spike");
  }

  if (shipment.payment_state === "blocked") {
    exceptions.push("payment_blocked");
  }

  return exceptions;
}
