// COPILOT SYSTEM BRIEFING – CHAINBRIDGE INTELLIGENCE UI
// ChainTicker Component
// =====================
//
// Real-time event ticker showing live freight, settlement, and alert activity.
// Surfaces tokenized freight movements, smart settlement events, and operational alerts.
//
// Design:
// - Slim horizontal bar with LIVE badge
// - Shows 5 most recent high-value events
// - Event types: alerts, IoT anomalies, payment settlements
// - Integrates with existing SSE infrastructure (useEventStream)
// - Tokenized freight flavor: emphasize shipment refs, capital movement, risk context

/**
 * ChainTicker Component
 *
 * Live event ticker bar displaying recent high-value Control Tower events.
 * Powered by SSE event stream for real-time freight and settlement intelligence.
 */

import { Activity, AlertTriangle, Radio, DollarSign } from "lucide-react";
import { useState } from "react";

import type { ControlTowerEvent, PaymentSettlementEventPayload } from "../../core/types/realtime";
import { useEventStream } from "../../hooks/useEventStream";

interface ChainTickerProps {
  onNavigateFromEvent?: (event: ControlTowerEvent) => void;
}

interface TickerItem {
  id: string;
  category: "alert" | "iot" | "settlement";
  message: string;
  timestamp: string;
  severity?: "critical" | "warning" | "info";
  hasProofpack?: boolean; // ProofPack available indicator
  milestoneId?: string; // Canonical milestone ID for navigation
  originalEvent: ControlTowerEvent;
}

const MAX_TICKER_ITEMS = 10;
const DISPLAY_ITEMS = 5;

export default function ChainTicker({ onNavigateFromEvent }: ChainTickerProps = {}): JSX.Element {
  const [tickerItems, setTickerItems] = useState<TickerItem[]>([]);

  // Subscribe to SSE events
  useEventStream({
    enabled: true,
    filter: {
      types: ["alert_created", "alert_status_changed", "iot_reading", "payment_state_changed"],
    },
    onEvent: (event: ControlTowerEvent) => {
      const newItem = parseEventToTickerItem(event);
      if (newItem) {
        setTickerItems((prev) => {
          const updated = [newItem, ...prev];
          return updated.slice(0, MAX_TICKER_ITEMS);
        });
      }
    },
  });

  const displayItems = tickerItems.slice(0, DISPLAY_ITEMS);

  return (
    <div className="border-b border-slate-800/70 bg-slate-900/50 px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-4">
        {/* Ticker Header */}
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Chain Ticker
          </span>
          <div className="flex items-center gap-1 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-2 py-0.5">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-wider text-emerald-300">
              LIVE
            </span>
          </div>
        </div>

        {/* Ticker Items */}
        <div className="flex-1 overflow-hidden">
          <div className="flex gap-4 overflow-x-auto scrollbar-hide">
            {displayItems.length === 0 ? (
              <span className="text-xs text-slate-600">Waiting for events...</span>
            ) : (
              displayItems.map((item) => (
                <TickerItemDisplay
                  key={item.id}
                  item={item}
                  onClick={() => onNavigateFromEvent?.(item.originalEvent)}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface TickerItemDisplayProps {
  item: TickerItem;
  onClick?: () => void;
}

function TickerItemDisplay({ item, onClick }: TickerItemDisplayProps): JSX.Element {
  const categoryConfig = {
    alert: {
      icon: AlertTriangle,
      label: "ALERT",
      baseColor: "text-red-400",
      bgColor: "bg-red-500/10",
      borderColor: "border-red-500/30",
    },
    iot: {
      icon: Radio,
      label: "IOT",
      baseColor: "text-blue-400",
      bgColor: "bg-blue-500/10",
      borderColor: "border-blue-500/30",
    },
    settlement: {
      icon: DollarSign,
      label: "SETTLEMENT",
      baseColor: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/30",
    },
  };

  const config = categoryConfig[item.category];
  const Icon = config.icon;

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 whitespace-nowrap transition-opacity hover:opacity-80"
    >
      <div className={`flex items-center gap-1.5 rounded-full border ${config.borderColor} ${config.bgColor} px-2 py-1`}>
        <Icon className={`h-3 w-3 ${config.baseColor}`} />
        <span className={`text-[9px] font-semibold uppercase tracking-wider ${config.baseColor}`}>
          {config.label}
        </span>
      </div>
      {/* PROOF badge when ProofPack is available */}
      {item.hasProofpack && (
        <div className="flex items-center gap-0.5 rounded-full border border-purple-500/50 bg-purple-500/20 px-1.5 py-0.5">
          <span className="text-[8px] font-bold uppercase tracking-wider text-purple-300">
            PROOF
          </span>
        </div>
      )}
      <span className="text-xs text-slate-300">{item.message}</span>
      <span className="text-[10px] text-slate-600">
        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </button>
  );
}

/**
 * Parse SSE event into ticker display item
 */
function parseEventToTickerItem(event: ControlTowerEvent): TickerItem | null {
  const timestamp = event.timestamp;
  const id = `${event.id}-${Date.now()}`;

  switch (event.type) {
    case "alert_created":
    case "alert_status_changed": {
      const payload = event.payload as {
        shipment_reference?: string;
        title?: string;
        severity?: "critical" | "warning" | "info";
        status?: string;
      };

      const shipRef = payload.shipment_reference || event.key;
      const title = payload.title || "Alert triggered";
      const severity = payload.severity || "info";

      return {
        id,
        category: "alert",
        message: `${shipRef} · ${title}`,
        timestamp,
        severity,
        originalEvent: event,
      };
    }

    case "iot_reading": {
      const payload = event.payload as {
        shipment_reference?: string;
        sensor_type?: string;
        value?: number;
        threshold_exceeded?: boolean;
      };

      const shipRef = payload.shipment_reference || event.key;
      const anomaly = payload.threshold_exceeded
        ? `${payload.sensor_type || "Sensor"} anomaly detected`
        : `${payload.sensor_type || "IoT"} reading`;

      return {
        id,
        category: "iot",
        message: `${shipRef} · ${anomaly}`,
        timestamp,
        originalEvent: event,
      };
    }

    case "payment_state_changed": {
      const payload = event.payload as unknown as PaymentSettlementEventPayload;

      const shipRef = payload.shipment_reference;
      const milestone = payload.milestone_name;
      const amount = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: payload.currency || "USD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(payload.amount);

      let action = "updated";
      if (payload.event_kind === "milestone_released") {
        action = `released · ${amount} unlocked`;
      } else if (payload.event_kind === "milestone_settled") {
        action = `settled · ${amount}`;
      } else if (payload.event_kind === "milestone_blocked") {
        action = `blocked · ${amount} held`;
      }

      return {
        id,
        category: "settlement",
        message: `${shipRef} · ${milestone} ${action}`,
        timestamp,
        hasProofpack: payload.proofpack_hint?.has_proofpack ?? false,
        milestoneId: payload.proofpack_hint?.milestone_id ?? payload.milestone_id,
        originalEvent: event,
      };
    }

    default:
      return null;
  }
}
