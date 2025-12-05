/**
 * TimelineEvent Component
 *
 * Rich logistics-style event visualization for ChainIQ history timeline.
 * Classifies risk events into operational categories with contextual icons and styling.
 */

import React from "react";

export interface TimelineEventData {
  timestamp: string;
  score: number;
  severity: string;
  recommended_action: string;
  reasonCodes: string[];
  payload?: Record<string, unknown>;
}

interface TimelineEventProps {
  event: TimelineEventData;
  isLatest: boolean;
}

/**
 * Classify event type based on reason codes and severity changes
 */
function classifyEvent(event: TimelineEventData): {
  type: string;
  icon: JSX.Element;
  color: string;
  label: string;
} {
  const codes = event.reasonCodes.map(c => c.toUpperCase());

  // Severity-based icons
  if (event.severity === "CRITICAL") {
    return {
      type: "critical",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      color: "text-red-400 bg-red-950/40 border-red-800/50",
      label: "CRITICAL ALERT",
    };
  }

  // Sanctions / Compliance
  if (codes.some(c => c.includes("SANCTION") || c.includes("COMPLIANCE") || c.includes("OFAC"))) {
    return {
      type: "compliance",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
      color: "text-purple-400 bg-purple-950/40 border-purple-800/50",
      label: "COMPLIANCE CHECK",
    };
  }

  // Corridor / Route Risk
  if (codes.some(c => c.includes("CORRIDOR") || c.includes("ROUTE") || c.includes("GEOPOLITICAL"))) {
    return {
      type: "route",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
      ),
      color: "text-orange-400 bg-orange-950/40 border-orange-800/50",
      label: "HIGH-RISK CORRIDOR",
    };
  }

  // Delay / Transit Issues
  if (codes.some(c => c.includes("DELAY") || c.includes("LATE") || c.includes("OVERDUE"))) {
    return {
      type: "delay",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      color: "text-amber-400 bg-amber-950/40 border-amber-800/50",
      label: "CARRIER DELAY",
    };
  }

  // Documents / Paperwork
  if (codes.some(c => c.includes("DOCUMENT") || c.includes("PAPERWORK") || c.includes("INCOMPLETE"))) {
    return {
      type: "docs",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      color: "text-yellow-400 bg-yellow-950/40 border-yellow-800/50",
      label: "DOCS INCOMPLETE",
    };
  }

  // Customs Hold
  if (codes.some(c => c.includes("CUSTOMS") || c.includes("BORDER") || c.includes("INSPECTION"))) {
    return {
      type: "customs",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
        </svg>
      ),
      color: "text-indigo-400 bg-indigo-950/40 border-indigo-800/50",
      label: "CUSTOMS HOLD",
    };
  }

  // Payment Issues
  if (codes.some(c => c.includes("PAYMENT") || c.includes("SHIPPER") || c.includes("CREDIT"))) {
    return {
      type: "payment",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
      color: "text-rose-400 bg-rose-950/40 border-rose-800/50",
      label: "PAYMENT HOLD",
    };
  }

  // Carrier Issues
  if (codes.some(c => c.includes("CARRIER") || c.includes("UNVERIFIED") || c.includes("UNRELIABLE"))) {
    return {
      type: "carrier",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
        </svg>
      ),
      color: "text-orange-400 bg-orange-950/40 border-orange-800/50",
      label: "CARRIER RISK",
    };
  }

  // Default / General Risk Assessment
  if (event.severity === "HIGH") {
    return {
      type: "risk",
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      color: "text-orange-400 bg-orange-950/40 border-orange-800/50",
      label: "RISK ELEVATED",
    };
  }

  // Low/Medium - Standard Assessment
  return {
    type: "assessment",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    color: event.severity === "MEDIUM"
      ? "text-amber-400 bg-amber-950/40 border-amber-800/50"
      : "text-emerald-400 bg-emerald-950/40 border-emerald-800/50",
    label: event.severity === "MEDIUM" ? "RISK ASSESSMENT" : "CLEARED",
  };
}

const TimelineEvent: React.FC<TimelineEventProps> = ({ event, isLatest }) => {
  const eventClass = classifyEvent(event);

  // Format timestamp
  const timestamp = new Date(event.timestamp);
  const timeStr = timestamp.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });
  const dateStr = timestamp.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  return (
    <li className="relative">
      {/* Timeline connector dot */}
      <span className={`absolute -left-[9px] top-3 h-3 w-3 rounded-full border-2 ${
        isLatest ? 'bg-emerald-500 border-emerald-400' : 'bg-slate-900 border-slate-600'
      }`} />

      {/* Event card */}
      <div className={`rounded-lg border p-3 ${eventClass.color}`}>
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {eventClass.icon}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-[0.22em]">
                {eventClass.label}
              </span>
              {isLatest && (
                <span className="rounded-full bg-emerald-500 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-950">
                  LATEST
                </span>
              )}
            </div>

            {/* Timestamp */}
            <div className="text-[11px] opacity-80 mb-2">
              {dateStr} • {timeStr}
            </div>

            {/* Risk Score & Severity */}
            <div className="flex items-center gap-2 mb-2">
              <span className="rounded-full bg-slate-900/60 px-2.5 py-1 text-xs font-semibold">
                Score {event.score}
              </span>
              <span className="rounded-full bg-slate-900/60 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide">
                {event.severity}
              </span>
            </div>

            {/* Recommended Action */}
            <div className="text-xs mb-2">
              <span className="opacity-70">Action:</span>{" "}
              <span className="font-semibold">
                {event.recommended_action.replace(/_/g, ' ')}
              </span>
            </div>

            {/* Reason Codes */}
            {event.reasonCodes.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {event.reasonCodes.map((code, idx) => (
                  <span
                    key={idx}
                    className="rounded-full bg-slate-900/60 px-2 py-0.5 text-[9px] uppercase tracking-[0.18em] font-medium"
                  >
                    {code.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </li>
  );
};

export default TimelineEvent;
