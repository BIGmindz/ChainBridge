

import create from 'zustand';
import { ChainBridgeEvent } from '../events/eventTypes';

export interface SettlementEvent extends ChainBridgeEvent {
  shipment_id: string;
  milestone: string;
  amount: number;
  risk_decision: string;
  rationale?: string;
}

export interface SettlementState {
  shipment_id: string;
  events: SettlementEvent[];
  last_milestone?: string;
  last_amount?: number;
  last_risk_decision?: string;
}




import { TokenEvent } from '../events/eventTypes';


interface EventBusState {
  events: ChainBridgeEvent[];
  eventIndex: Record<string, ChainBridgeEvent[]>;
  latestRiskScore: Record<string, number>;
  settlementProgress: Record<string, any>;
  systemEvents: ChainBridgeEvent[];
  settlementEvents: SettlementEvent[];
  tokenEvents: TokenEvent[];
  addEvent: (event: ChainBridgeEvent) => void;
  addSettlementEvent: (event: SettlementEvent) => void;
  addTokenEvent: (event: TokenEvent) => void;
  getSettlementStateByShipment: (id: string) => SettlementState | undefined;
  getTokenEventsByShipment: (id: string) => TokenEvent[];
  getTokensForShipment: (id: string) => TokenEvent[];
  getTokenTrajectory: (id: string) => { x: number, y: number, burn?: boolean, reliability?: number }[];
  clear: () => void;
}

const MAX_EVENTS = 500;

export const useEventBusStore = create<EventBusState>(
  (set: (partial: Partial<EventBusState> | ((state: EventBusState) => Partial<EventBusState>), replace?: boolean) => void,
   get: () => EventBusState
  ) => ({
    events: [],
    eventIndex: {},
    latestRiskScore: {},
    settlementProgress: {},
    systemEvents: [],
    settlementEvents: [],
    tokenEvents: [],
    addEvent: (event: ChainBridgeEvent) => {
      set((state: EventBusState) => {
        const events = [event, ...state.events].slice(0, MAX_EVENTS);
        const eventIndex = { ...state.eventIndex };
        if (event.canonical_shipment_id) {
          eventIndex[event.canonical_shipment_id] = [
            event,
            ...(eventIndex[event.canonical_shipment_id] || []),
          ].slice(0, MAX_EVENTS);
        }
        let latestRiskScore = { ...state.latestRiskScore };
        if (event.event_type === 'RISK_SCORE' && event.payload?.score !== undefined) {
          latestRiskScore[event.canonical_shipment_id] = event.payload.score;
        }
        let settlementProgress = { ...state.settlementProgress };
        if (event.event_type === 'SETTLEMENT_TRIGGER') {
          settlementProgress[event.canonical_shipment_id] = event.payload;
        }
        let systemEvents = state.systemEvents;
        if (event.event_type === 'SYSTEM_EVENT') {
          systemEvents = [event, ...systemEvents].slice(0, MAX_EVENTS);
        }
        return {
          events,
          eventIndex,
          latestRiskScore,
          settlementProgress,
          systemEvents,
          settlementEvents: state.settlementEvents,
          tokenEvents: state.tokenEvents,
        };
      });
    },
    addSettlementEvent: (event: SettlementEvent) => {
      set((state: EventBusState) => {
        const settlementEvents = [event, ...state.settlementEvents].slice(0, MAX_EVENTS);
        return { ...state, settlementEvents };
      });
    },
    getSettlementStateByShipment: (id: string) => {
      const events = get().settlementEvents.filter(e => e.shipment_id === id);
      if (events.length === 0) return undefined;
      const last = events[0];
      return {
        shipment_id: id,
        events,
        last_milestone: last.milestone,
        last_amount: last.amount,
        last_risk_decision: last.risk_decision,
      };
    },
    addTokenEvent: (event: TokenEvent) => {
      set((state: EventBusState) => {
        const tokenEvents = [event, ...state.tokenEvents].slice(0, MAX_EVENTS);
        return { ...state, tokenEvents };
      });
    },
    getTokenEventsByShipment: (id: string) => {
      return get().tokenEvents.filter(e => e.canonical_shipment_id === id);
    },
    getTokensForShipment: (id: string) => {
      return get().tokenEvents.filter(e => e.canonical_shipment_id === id);
    },
    getTokenTrajectory: (id: string) => {
      const events = get().tokenEvents
        .filter(e => e.canonical_shipment_id === id)
        .sort((a, b) => new Date(a.timestamp || a.timestamp || '').getTime() - new Date(b.timestamp || b.timestamp || '').getTime());
      let cumulative = 0;
      return events.map((e, idx) => {
        const net = (e.tokenAmount ?? 0) * (e.riskMultiplier ?? 1) * (e.mlAdjustment ?? 1) - (e.burnAmount ?? 0);
        cumulative += net;
        return {
          x: idx,
          y: cumulative,
          burn: !!e.burnAmount,
          reliability: e.economicReliability,
        };
      });
    },
    clear: () => set({
      events: [],
      eventIndex: {},
      latestRiskScore: {},
      settlementProgress: {},
      systemEvents: [],
      settlementEvents: [],
      tokenEvents: [],
    }),
  })
);
