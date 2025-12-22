
import { useEffect, useRef } from 'react';
import { EventStream, EventStreamCallback } from './eventStream';
import { ChainBridgeEvent } from './eventTypes';
import { useEventBusStore } from '../state/eventBusStore';
import { TokenEvent } from './eventTypes';

export function useEventStream(
  onEvent: (event: ChainBridgeEvent) => void,
  authToken: string | null
) {
  const streamRef = useRef<EventStream | null>(null);
  const addSettlementEvent = useEventBusStore((s) => s.addSettlementEvent);
  const addTokenEvent = useEventBusStore((s) => s.addTokenEvent);

  useEffect(() => {
    streamRef.current = new EventStream(authToken);
    const unsubscribe = streamRef.current.subscribe((event: ChainBridgeEvent) => {
      if (event.event_type && event.event_type.startsWith('SETTLEMENT_')) {
        addSettlementEvent({
          ...event,
          shipment_id: event.canonical_shipment_id,
          milestone: event.payload?.milestone || '',
          amount: event.payload?.amount || 0,
          risk_decision: event.payload?.risk_decision || '',
          rationale: event.payload?.rationale,
        });
      }
      if (
        event.event_type === 'TOKEN_EARNED' ||
        event.event_type === 'TOKEN_FINAL' ||
        event.event_type === 'TOKEN_BURN' ||
        event.event_type === 'TOKEN_PENALTY'
      ) {
        const tokenEvent: TokenEvent = {
          ...event,
          tokenAmount: event.payload?.tokenAmount ?? 0,
          burnAmount: event.payload?.burnAmount ?? 0,
          finalAmount: event.payload?.finalAmount ?? undefined,
          riskMultiplier: event.payload?.riskMultiplier ?? 1,
          mlAdjustment: event.payload?.mlAdjustment ?? 1,
          netToken:
            (event.payload?.tokenAmount ?? 0) * (event.payload?.riskMultiplier ?? 1) * (event.payload?.mlAdjustment ?? 1) - (event.payload?.burnAmount ?? 0),
          severity: event.severity,
          rationale: event.rationale ?? event.payload?.rationale,
          traceId: event.trace_id,
          economicReliability: event.payload?.economicReliability ?? undefined,
          timestamp: event.timestamp,
        };
        addTokenEvent(tokenEvent);
      }
      onEvent(event);
    });
    return () => {
      unsubscribe();
      streamRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken]);
}
