/**
 * Sandbox Page
 *
 * Component QA and visual testing environment for ChainBoard timeline system.
 * Mock data, loading/error states, and edge case testing.
 */

import { useState } from "react";

import { ShipmentTimeline } from "../components/ShipmentTimeline";
import type { TimelineEvent } from "../core/types/events";

// Mock timeline events for testing
const MOCK_TIMELINE_EVENTS: TimelineEvent[] = [
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "created",
    description: "Shipment created in system",
    occurredAt: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(), // 3 days ago
    source: "ChainBoard",
    severity: null,
  },
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "booked",
    description: "Booking confirmed with carrier MAERSK",
    occurredAt: new Date(Date.now() - 70 * 60 * 60 * 1000).toISOString(),
    source: "ChainFreight",
    severity: null,
  },
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "picked_up",
    description: "Container picked up from warehouse",
    occurredAt: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(), // 2 days ago
    source: "ChainSense",
    severity: null,
  },
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "departed_port",
    description: "Departed from Port of Los Angeles",
    occurredAt: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
    source: "ChainFreight",
    severity: null,
  },
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "iot_alert",
    description: "Temperature spike detected: 28°C (threshold: 25°C)",
    occurredAt: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), // 12 hours ago
    source: "ChainSense",
    severity: "high",
  },
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "customs_hold",
    description: "Container held at customs for inspection",
    occurredAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(), // 6 hours ago
    source: "ChainFreight",
    severity: "medium",
  },
  {
    shipmentId: "SHIP-TEST-001",
    reference: "TEST-REF-001",
    corridor: "LAX-SHA",
    eventType: "customs_released",
    description: "Customs inspection completed, container released",
    occurredAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
    source: "ChainFreight",
    severity: null,
  },
];

const EMPTY_EVENTS: TimelineEvent[] = [];

export default function SandboxPage(): JSX.Element {
  const [testCase, setTestCase] = useState<"normal" | "empty" | "loading" | "error">("normal");

  return (
    <div className="space-y-8 max-w-4xl mx-auto p-6">
      {/* Page Header */}
      <header className="border-b border-gray-300 pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          ChainBoard // Sandbox
        </p>
        <h1 className="mt-1 text-2xl font-bold text-gray-900">
          Component QA & Visual Testing
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Timeline system testing with mock data and edge cases
        </p>
      </header>

      {/* Test Case Controls */}
      <section className="rounded-lg border border-gray-300 bg-gray-50 p-4">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">Test Case</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setTestCase("normal")}
            className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
              testCase === "normal"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
            }`}
          >
            Normal (7 events)
          </button>
          <button
            onClick={() => setTestCase("empty")}
            className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
              testCase === "empty"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
            }`}
          >
            Empty
          </button>
          <button
            onClick={() => setTestCase("loading")}
            className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
              testCase === "loading"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
            }`}
          >
            Loading
          </button>
          <button
            onClick={() => setTestCase("error")}
            className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
              testCase === "error"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
            }`}
          >
            Error
          </button>
        </div>
      </section>

      {/* ShipmentTimeline Component Test */}
      <section className="rounded-lg border border-gray-300 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">ShipmentTimeline Component</h2>

        {testCase === "normal" && (
          <ShipmentTimeline events={MOCK_TIMELINE_EVENTS} loading={false} error={null} />
        )}

        {testCase === "empty" && (
          <ShipmentTimeline events={EMPTY_EVENTS} loading={false} error={null} />
        )}

        {testCase === "loading" && (
          <ShipmentTimeline events={[]} loading={true} error={null} />
        )}

        {testCase === "error" && (
          <ShipmentTimeline
            events={[]}
            loading={false}
            error={new Error("Failed to load timeline events from API")}
          />
        )}
      </section>

      {/* Event Type Badge Legend */}
      <section className="rounded-lg border border-gray-300 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Event Type Badge Colors</h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded border bg-red-100 text-red-800 border-red-300">
              iot_alert
            </span>
            <span className="text-gray-600">Critical/Alert Events</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded border bg-red-100 text-red-800 border-red-300">
              customs_hold
            </span>
            <span className="text-gray-600">Holds/Blocks</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded border bg-green-100 text-green-800 border-green-300">
              delivered
            </span>
            <span className="text-gray-600">Success/Completion</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded border bg-green-100 text-green-800 border-green-300">
              customs_released
            </span>
            <span className="text-gray-600">Release Events</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded border bg-blue-100 text-blue-800 border-blue-300">
              departed_port
            </span>
            <span className="text-gray-600">Transit Milestones</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded border bg-gray-100 text-gray-800 border-gray-300">
              created
            </span>
            <span className="text-gray-600">Default/Other</span>
          </div>
        </div>
      </section>

      {/* Implementation Notes */}
      <section className="rounded-lg border border-blue-200 bg-blue-50 p-6">
        <h2 className="text-lg font-semibold text-blue-900 mb-3">Implementation Notes</h2>
        <ul className="space-y-2 text-sm text-blue-800">
          <li>✅ Timeline events use <code className="bg-blue-100 px-1 rounded">occurredAt</code> for timestamps</li>
          <li>✅ Events sorted chronologically (oldest first in mock data)</li>
          <li>✅ Relative time formatting with <code className="bg-blue-100 px-1 rounded">date-fns</code></li>
          <li>✅ Loading, empty, and error states handled</li>
          <li>✅ Color-coded badges by event type severity</li>
          <li>✅ Source and corridor metadata displayed</li>
          <li>✅ Timeline visual with dots and connector lines</li>
        </ul>
      </section>

      {/* Command Palette & Views Demo */}
      <section className="rounded-lg border border-purple-200 bg-purple-50 p-6">
        <h2 className="text-lg font-semibold text-purple-900 mb-3">Operator Console Features</h2>
        <div className="space-y-3 text-sm text-purple-800">
          <div>
            <h3 className="font-semibold mb-1">Command Palette</h3>
            <p>Press <kbd className="px-2 py-1 bg-purple-100 rounded text-xs font-mono">Cmd+K</kbd> (Mac) or <kbd className="px-2 py-1 bg-purple-100 rounded text-xs font-mono">Ctrl+K</kbd> (Windows) to open quick navigation</p>
          </div>
          <div>
            <h3 className="font-semibold mb-1">Saved Views</h3>
            <p>Shipments page has view bar with system views: All Shipments, High Risk, Payment Holds, IoT Alerts, Customs Holds</p>
          </div>
          <div>
            <h3 className="font-semibold mb-1">Global Search</h3>
            <p>Search shipments by reference, corridor, or customer name on the Shipments page</p>
          </div>
        </div>
      </section>
    </div>
  );
}
