/**
 * Shadow Pilot Mock Data Service
 *
 * Generates realistic Shadow Pilot data from demo CSV for immediate demonstration.
 * Simulates ChainBridge's commercial impact analysis without requiring backend.
 */

import type {
    PaginatedShadowPilotShipments,
    ShadowPilotShipmentResult,
    ShadowPilotSummary,
} from '../types/chainbridge';

// Demo shipment data based on the CSV
interface DemoShipment {
  shipmentId: string;
  corridor: string;
  mode: string;
  customerSegment: string;
  cargo_value: number;
  transit_days: number;
  days_to_payment: number;
  max_temp_deviation: number;
  exceptionFlag: number;
  lossFlag: number;
  loss_amount_usd: number;
}

const DEMO_SHIPMENTS: DemoShipment[] = [
  { shipmentId: 'SHP-1001', corridor: 'US-MX', mode: 'FCL', customerSegment: 'SME', cargo_value: 180000, transit_days: 32, days_to_payment: 60, max_temp_deviation: 1.2, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-1002', corridor: 'US-MX', mode: 'FCL', customerSegment: 'SME', cargo_value: 220000, transit_days: 35, days_to_payment: 65, max_temp_deviation: 0.8, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-1003', corridor: 'US-MX', mode: 'REEFER', customerSegment: 'SME', cargo_value: 260000, transit_days: 30, days_to_payment: 55, max_temp_deviation: 2.5, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-1004', corridor: 'US-MX', mode: 'REEFER', customerSegment: 'SME', cargo_value: 90000, transit_days: 28, days_to_payment: 55, max_temp_deviation: 6.8, exceptionFlag: 1, lossFlag: 1, loss_amount_usd: 90000 },
  { shipmentId: 'SHP-1005', corridor: 'US-MX', mode: 'FCL', customerSegment: 'Enterprise', cargo_value: 140000, transit_days: 33, days_to_payment: 60, max_temp_deviation: 3.2, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-2001', corridor: 'EU-US', mode: 'FCL', customerSegment: 'Enterprise', cargo_value: 300000, transit_days: 27, days_to_payment: 50, max_temp_deviation: 1.0, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-2002', corridor: 'EU-US', mode: 'AIR', customerSegment: 'Enterprise', cargo_value: 75000, transit_days: 10, days_to_payment: 35, max_temp_deviation: 0.5, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-2003', corridor: 'EU-US', mode: 'AIR', customerSegment: 'SME', cargo_value: 52000, transit_days: 12, days_to_payment: 40, max_temp_deviation: 4.5, exceptionFlag: 1, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-2004', corridor: 'EU-US', mode: 'FCL', customerSegment: 'SME', cargo_value: 48000, transit_days: 29, days_to_payment: 60, max_temp_deviation: 1.5, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-3001', corridor: 'APAC-US', mode: 'FCL', customerSegment: 'Enterprise', cargo_value: 410000, transit_days: 40, days_to_payment: 70, max_temp_deviation: 0.9, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-3002', corridor: 'APAC-US', mode: 'REEFER', customerSegment: 'SME', cargo_value: 195000, transit_days: 42, days_to_payment: 75, max_temp_deviation: 7.5, exceptionFlag: 1, lossFlag: 1, loss_amount_usd: 195000 },
  { shipmentId: 'SHP-3003', corridor: 'APAC-US', mode: 'FCL', customerSegment: 'SME', cargo_value: 130000, transit_days: 38, days_to_payment: 68, max_temp_deviation: 2.0, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-3004', corridor: 'APAC-US', mode: 'FCL', customerSegment: 'SME', cargo_value: 58000, transit_days: 36, days_to_payment: 65, max_temp_deviation: 3.8, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-4001', corridor: 'US-CAN', mode: 'LTL', customerSegment: 'SME', cargo_value: 38000, transit_days: 7, days_to_payment: 30, max_temp_deviation: 0.3, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-4002', corridor: 'US-CAN', mode: 'LTL', customerSegment: 'SME', cargo_value: 62000, transit_days: 9, days_to_payment: 32, max_temp_deviation: 5.2, exceptionFlag: 1, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-4003', corridor: 'US-CAN', mode: 'LTL', customerSegment: 'Enterprise', cargo_value: 97000, transit_days: 8, days_to_payment: 30, max_temp_deviation: 1.7, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-5001', corridor: 'US-DOMESTIC', mode: 'TRUCKLOAD', customerSegment: 'SME', cargo_value: 110000, transit_days: 5, days_to_payment: 25, max_temp_deviation: 0.4, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-5002', corridor: 'US-DOMESTIC', mode: 'TRUCKLOAD', customerSegment: 'SME', cargo_value: 49000, transit_days: 4, days_to_payment: 25, max_temp_deviation: 1.1, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-5003', corridor: 'US-DOMESTIC', mode: 'TRUCKLOAD', customerSegment: 'Enterprise', cargo_value: 205000, transit_days: 6, days_to_payment: 28, max_temp_deviation: 2.9, exceptionFlag: 0, lossFlag: 0, loss_amount_usd: 0 },
  { shipmentId: 'SHP-5004', corridor: 'US-DOMESTIC', mode: 'TRUCKLOAD', customerSegment: 'SME', cargo_value: 150000, transit_days: 6, days_to_payment: 32, max_temp_deviation: 8.2, exceptionFlag: 1, lossFlag: 1, loss_amount_usd: 150000 },
];

// ChainBridge business logic constants
const MIN_FINANCEABLE_VALUE = 50000; // $50K minimum
const MAX_TEMP_DEVIATION_THRESHOLD = 5.0; // Quality score threshold
const LTV_RATIO = 0.7; // 70% loan-to-value
const PROTOCOL_FEE_RATE = 0.01; // 1% take rate
const DAILY_WC_COST_RATE = 0.12 / 365; // 12% annual cost of capital
const AVERAGE_DAYS_PULLED_FORWARD = 28; // Days financing accelerates payment

function calculateEventTruthScore(shipment: DemoShipment): number {
  // Event truth score based on temperature deviation and exceptions
  let baseScore = 1.0;

  // Reduce score for temperature deviations
  if (shipment.max_temp_deviation > MAX_TEMP_DEVIATION_THRESHOLD) {
    baseScore -= 0.3;
  } else if (shipment.max_temp_deviation > 2.0) {
    baseScore -= 0.1;
  }

  // Reduce score for exceptions
  if (shipment.exceptionFlag === 1) {
    baseScore -= 0.15;
  }

  // Add some randomness to make it realistic
  const randomFactor = (Math.random() - 0.5) * 0.1;
  return Math.max(0.1, Math.min(1.0, baseScore + randomFactor));
}

function processShipmentForFinancing(shipment: DemoShipment): ShadowPilotShipmentResult {
  const eventTruthScore = calculateEventTruthScore(shipment);
  const isFinanceable = shipment.cargo_value >= MIN_FINANCEABLE_VALUE &&
                       eventTruthScore >= 0.6 &&
                       shipment.lossFlag === 0;

  const financedAmount = isFinanceable ? shipment.cargo_value * LTV_RATIO : 0;
  const protocolRevenue = financedAmount * PROTOCOL_FEE_RATE;
  const daysPulledForward = isFinanceable ? AVERAGE_DAYS_PULLED_FORWARD : 0;
  const wcSaved = financedAmount * DAILY_WC_COST_RATE * daysPulledForward;
  const avoidedLoss = shipment.lossFlag === 1 ? shipment.loss_amount_usd : 0;

  return {
    shipmentId: shipment.shipmentId,
    corridor: shipment.corridor,
    cargoValueUsd: shipment.cargo_value,
    eventTruthScore: eventTruthScore,
    eligibleForFinance: isFinanceable,
    financedAmountUsd: financedAmount,
    daysPulledForward: daysPulledForward,
    wcSavedUsd: wcSaved,
    protocolRevenueUsd: protocolRevenue,
    avoidedLossUsd: avoidedLoss,
    salvageRevenueUsd: avoidedLoss * 0.1, // 10% salvage recovery
    exceptionFlag: shipment.exceptionFlag,
    lossFlag: shipment.lossFlag,
    mode: shipment.mode,
    customerSegment: shipment.customerSegment,
  };
}

export function generateMockShadowPilotSummary(): ShadowPilotSummary {
  const processedShipments = DEMO_SHIPMENTS.map(processShipmentForFinancing);

  const totalGmv = processedShipments.reduce((sum, s) => sum + s.cargoValueUsd, 0);
  const financeableGmv = processedShipments
    .filter(s => s.eligibleForFinance)
    .reduce((sum, s) => sum + s.cargoValueUsd, 0);
  const financedGmv = processedShipments.reduce((sum, s) => sum + s.financedAmountUsd, 0);
  const protocolRevenue = processedShipments.reduce((sum, s) => sum + s.protocolRevenueUsd, 0);
  const workingCapitalSaved = processedShipments.reduce((sum, s) => sum + s.wcSavedUsd, 0);
  const lossesAvoided = processedShipments.reduce((sum, s) => sum + s.avoidedLossUsd, 0);
  const salvageRevenue = processedShipments.reduce((sum, s) => sum + s.salvageRevenueUsd, 0);
  const avgDaysPulledForward = processedShipments
    .filter(s => s.daysPulledForward > 0)
    .reduce((sum, s, _, arr) => sum + s.daysPulledForward / arr.length, 0);

  return {
    run_id: 'acme_logistics_demo_12m',
    prospect_name: 'ACME Logistics (Demo)',
    period_months: 12,
    total_gmv_usd: totalGmv,
    financeable_gmv_usd: financeableGmv,
    financed_gmv_usd: financedGmv,
    protocolRevenueUsd: protocolRevenue,
    working_capital_saved_usd: workingCapitalSaved,
    losses_avoided_usd: lossesAvoided,
    salvageRevenueUsd: salvageRevenue,
    average_daysPulledForward: avgDaysPulledForward,
    shipments_evaluated: processedShipments.length,
    shipments_financeable: processedShipments.filter(s => s.eligibleForFinance).length,
    createdAt: new Date().toISOString(),
  };
}

export const MOCK_SHADOW_PILOT_SUMMARIES: ShadowPilotSummary[] = [
  generateMockShadowPilotSummary(),
];

export function getMockShadowPilotShipments(runId: string): PaginatedShadowPilotShipments {
  if (runId !== 'acme_logistics_demo_12m') {
    return { items: [] };
  }

  const processedShipments = DEMO_SHIPMENTS.map(processShipmentForFinancing);

  return {
    items: processedShipments,
    next_cursor: null,
  };
}
