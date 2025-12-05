import type { SettlementStatus } from '../../types/chainpay';

// MOCK: Story/demo helper. The Operator Console now uses the live
// /api/chainpay/settlements/{shipment_id} endpoint by default.
export const mockSettlementStatus: SettlementStatus = {
  shipmentId: 'SHIP-12345',
  corridor: 'US-CA',
  cbUsd: {
    total: 10000,
    released: 6500,
    reserved: 3500,
  },
  currentMilestone: 'DELIVERED',
  riskScore: 28,
  events: [
    {
      id: 'evt-1',
      shipmentId: 'SHIP-12345',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
      milestone: 'PICKUP',
      riskTier: 'LOW',
      notes: 'Origin hub transfer complete',
    },
    {
      id: 'evt-2',
      shipmentId: 'SHIP-12345',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
      milestone: 'IN_TRANSIT',
      riskTier: 'LOW',
      notes: 'Multi-hop handoff verified',
    },
    {
      id: 'evt-3',
      shipmentId: 'SHIP-12345',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
      milestone: 'DELIVERED',
      riskTier: 'MEDIUM',
      notes: 'Proof of delivery captured; awaiting claim window',
    },
  ],
};
