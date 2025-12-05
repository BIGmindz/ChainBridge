import EventTypes, { ChainBridgeEvent } from './eventTypes';

const WS_URL = '/ws/events';
const SSE_URL = '/sse/events';

export type EventStreamCallback = (event: ChainBridgeEvent) => void;

export class EventStream {
  private ws: WebSocket | null = null;
  private sse: EventSource | null = null;
  private useSSE: boolean = false;
  private reconnectTimeout: number = 1000;
  private maxReconnect: number = 30000;
  private reconnectAttempts: number = 0;
  private listeners: Set<EventStreamCallback> = new Set();
  private isConnected: boolean = false;
  private authToken: string | null = null;

  constructor(authToken: string | null) {
    this.authToken = authToken;
    this.connect();
  }

  private connect() {
    if (this.useSSE) {
      this.initSSE();
    } else {
      this.initWS();
    }
  }

  private initWS() {
    const url = this.authToken ? `${WS_URL}?token=${encodeURIComponent(this.authToken)}` : WS_URL;
    this.ws = new WebSocket(url);
    this.ws.onopen = () => {
      this.isConnected = true;
      this.reconnectAttempts = 0;
    };
    this.ws.onmessage = (msg) => {
      try {
        const event: ChainBridgeEvent = JSON.parse(msg.data);
        this.listeners.forEach((cb) => cb(event));
      } catch (e) {
        // Ignore malformed events
      }
    };
    this.ws.onerror = () => {
      this.isConnected = false;
      this.fallbackToSSE();
    };
    this.ws.onclose = () => {
      this.isConnected = false;
      this.scheduleReconnect();
    };
  }

  private fallbackToSSE() {
    this.useSSE = true;
    this.initSSE();
  }

  private initSSE() {
    const url = this.authToken ? `${SSE_URL}?token=${encodeURIComponent(this.authToken)}` : SSE_URL;
    this.sse = new EventSource(url);
    this.sse.onmessage = (msg) => {
      try {
        const event: ChainBridgeEvent = JSON.parse(msg.data);
        this.listeners.forEach((cb) => cb(event));
      } catch (e) {
        // Ignore malformed events
      }
    };
    this.sse.onerror = () => {
      this.isConnected = false;
      this.scheduleReconnect();
    };
    this.sse.onopen = () => {
      this.isConnected = true;
      this.reconnectAttempts = 0;
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts * this.reconnectTimeout < this.maxReconnect) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, Math.min(this.reconnectTimeout * this.reconnectAttempts, this.maxReconnect));
    }
  }

  public subscribe(cb: EventStreamCallback) {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  public close() {
    if (this.ws) this.ws.close();
    if (this.sse) this.sse.close();
    this.listeners.clear();
  }
}
