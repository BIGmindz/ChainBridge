import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchSettlementEvents } from "../services/apiClient";
import type { SettlementEvent } from "../types/chainbridge";

// Legacy query-based hook for compatibility
export function useSettlementEvents(paymentIntentId?: string) {
  return useQuery<SettlementEvent[], Error>({
    queryKey: ["settlementEvents", paymentIntentId],
    queryFn: () => fetchSettlementEvents(paymentIntentId as string),
    enabled: !!paymentIntentId,
    staleTime: 10_000,
    retry: 1,
  });
}

// Enhanced real-time settlement event interface
export interface RealtimeSettlementEvent {
  type: 'SETTLEMENT:COMPLETE' | 'SETTLEMENT:FAILED' | 'SETTLEMENT:PROGRESS';
  intentId: string;
  data: {
    txHash?: string;
    status: 'pending' | 'settling' | 'settled' | 'failed';
    error?: string;
    timestamp: string;
    finalPrice?: number;
  };
}

export type SettlementEventListener = (event: RealtimeSettlementEvent) => void;

interface UseRealtimeSettlementOptions {
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

/**
 * Real-time settlement event listener via WebSocket
 */
export function useRealtimeSettlement(options: UseRealtimeSettlementOptions = {}) {
  const {
    autoConnect = true,
    reconnectAttempts = 3,
    reconnectDelay = 2000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Set<SettlementEventListener>>(new Set());
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<number>();

  // Get WebSocket URL based on environment
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/settlements`;
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Settlement WebSocket connected');
        reconnectCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Parse settlement event
          if (data.type && data.type.startsWith('SETTLEMENT:')) {
            const settlementEvent: RealtimeSettlementEvent = {
              type: data.type,
              intentId: data.intent_id || data.intentId,
              data: {
                txHash: data.tx_hash || data.txHash,
                status: data.status || 'pending',
                error: data.error,
                timestamp: data.timestamp || new Date().toISOString(),
                finalPrice: data.final_price || data.finalPrice,
              },
            };

            // Notify all listeners
            listenersRef.current.forEach(listener => {
              try {
                listener(settlementEvent);
              } catch (error) {
                console.error('Settlement event listener error:', error);
              }
            });
          }
        } catch (error) {
          console.error('Failed to parse settlement event:', error);
        }
      };

      ws.onclose = () => {
        console.log('Settlement WebSocket disconnected');

        // Attempt reconnection if within limits
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log(`Attempting to reconnect (${reconnectCountRef.current}/${reconnectAttempts})`);
            connect();
          }, reconnectDelay);
        }
      };

      ws.onerror = (error) => {
        console.error('Settlement WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to create settlement WebSocket:', error);
    }
  }, [getWebSocketUrl, reconnectAttempts, reconnectDelay]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Add event listener
  const addListener = useCallback((listener: SettlementEventListener) => {
    listenersRef.current.add(listener);

    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  // Subscribe to specific intent ID
  const subscribeToIntent = useCallback((intentId: string, listener: SettlementEventListener) => {
    const wrappedListener = (event: RealtimeSettlementEvent) => {
      if (event.intentId === intentId) {
        listener(event);
      }
    };

    return addListener(wrappedListener);
  }, [addListener]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    connect,
    disconnect,
    addListener,
    subscribeToIntent,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}

/**
 * Simplified hook for tracking a specific settlement intent
 */
export function useSettlementIntent(intentId: string | null) {
  const [status, setStatus] = useState<RealtimeSettlementEvent['data']['status']>('pending');
  const [txHash, setTxHash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finalPrice, setFinalPrice] = useState<number | null>(null);

  const { subscribeToIntent, isConnected } = useRealtimeSettlement();

  useEffect(() => {
    if (!intentId) {
      setStatus('pending');
      setTxHash(null);
      setError(null);
      setFinalPrice(null);
      return;
    }

    const unsubscribe = subscribeToIntent(intentId, (event) => {
      const { data } = event;

      setStatus(data.status);
      if (data.txHash) setTxHash(data.txHash);
      if (data.error) setError(data.error);
      if (data.finalPrice) setFinalPrice(data.finalPrice);
    });

    return unsubscribe;
  }, [intentId, subscribeToIntent]);

  return {
    status,
    txHash,
    error,
    finalPrice,
    isConnected,
  };
}
