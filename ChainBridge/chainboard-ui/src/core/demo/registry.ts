/**
 * Demo Scenario Registry
 *
 * Pre-built demo walkthroughs for different audiences.
 */

import type { DemoScenario } from "./types";

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "investor_hot_shipment",
    name: "Investor: Hot Shipment Walkthrough",
    description:
      "Walk through a high-risk, high-value shipment with IoT anomalies and payment holds.",
    heroShipmentHint: "high",
    steps: [
      {
        id: "overview_kpis",
        title: "Control Tower KPIs",
        description:
          "Start on the Overview. Call out the KPI strip: total shipments, high-risk count, payments on hold, and IoT coverage.",
        targetRoute: "/",
      },
      {
        id: "overview_insights",
        title: "Risk Insights Feed",
        description:
          "Scroll to the Insights Feed and show how ChainIQ translates risk data into narratives and recommended actions.",
        targetRoute: "/",
        highlightKey: "insights_feed",
      },
      {
        id: "shipments_view",
        title: "Operator Views",
        description:
          "Switch to the Shipments page and select the 'High Risk' view. Explain how operators can pivot by view and search.",
        targetRoute: "/shipments",
        highlightKey: "view_bar",
      },
      {
        id: "shipments_hot_shipment",
        title: "Pick the Hot Shipment",
        description:
          "Click the top high-risk shipment in the table. This is our 'hero' shipment for the story.",
        targetRoute: "/shipments",
        highlightKey: "hero_shipment",
      },
      {
        id: "shipment_drawer_intel",
        title: "Unified Intelligence",
        description:
          "In the drawer, walk through the Control Tower Intelligence section: ChainIQ risk, ChainPay holds, and IoT health.",
        targetRoute: "/shipments",
        highlightKey: "intel_panel",
      },
      {
        id: "shipment_timeline",
        title: "Timeline of Events",
        description:
          "Scroll down to the Timeline to show how status, IoT alerts, and customs/payment events are stitched into a single narrative.",
        targetRoute: "/shipments",
        highlightKey: "timeline",
      },
      {
        id: "payment_queue",
        title: "Payment Queue Context",
        description:
          "Jump back to Overview and point to the Payment Hold Queue, tying the shipment's status to cash flow impact.",
        targetRoute: "/",
        highlightKey: "payment_queue",
      },
      {
        id: "iot_health",
        title: "IoT Fleet Health",
        description:
          "Highlight the IoT Health panel to show coverage and alerts at the fleet level, not just per-shipment.",
        targetRoute: "/",
        highlightKey: "iot_panel",
      },
      {
        id: "alerts_console",
        title: "Alerts & Triage Console",
        description:
          "Use the alerts console (bell icon) to see all open issues across risk, IoT, payments, and customs, and quickly triage them with Acknowledge/Resolve actions.",
        targetRoute: "/",
        highlightKey: "alerts_bell",
      },
      {
        id: "triage_playbook",
        title: "Triage Playbook: Assign, Note, Resolve",
        description:
          "Navigate to the Triage Work Queue to show operator playbooks: filter by severity or source, assign alerts to yourself, add triage notes, and mark as acknowledged or resolved.",
        targetRoute: "/triage",
        highlightKey: "triage_work_queue",
      },
    ],
  },
];
