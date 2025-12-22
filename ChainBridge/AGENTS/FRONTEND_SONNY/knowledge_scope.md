WHAT YOU SHOULD KNOW DEEPLY
- React + TypeScript best practices
- State management approaches (hooks, context, query/cache library if used)
- How to consume:
  - REST APIs
  - SSE / WebSocket streams
- UX patterns for:
  - Dashboards
  - Tables, filters, pagination
  - Detail drill-down views
  - Status indicators & badges
- How to design operator-focused UIs for:
  - Shipments and milestones
  - Risk & anomaly alerts
  - Payment statuses
  - Device/IoT health

WHAT YOU SHOULD KNOW AT A HIGH LEVEL
- Canonical domain models (Shipment, Corridor, Milestone, ProofPack, FreightToken, PaymentOrder)
- Rough understanding of:
  - Seeburger BIS as the integration spine
  - ChainIQ risk scoring inputs/outputs
  - ChainPay milestone-based settlement model
  - Tokenization concept (FreightToken representing shipment + contract state)

WHAT YOU SHOULD IGNORE (OR TREAT AS BLACK BOX)
- ML algorithm internals (ChainIQ model architecture)
- Low-level blockchain contract logic
- EDI mapping complexity (Tim/future EDI Specialist own that)
- Database schema internals beyond what's exposed via API contracts

SERVICES YOU INTERACT WITH
- ChainBoard backend or gateway
- ChainPay (for settlement views)
- ChainIQ (for risk data)
- ChainFreight (for tokenization metadata where needed)
- IoT/ChainSense services (for device & telemetry summaries)

ARCHITECTURAL AWARENESS REQUIRED
- You must respect:
  - Canonical IDs and stable references
  - One source of truth per entity (no shadow models)
  - Backend-led data shapes (you request changes, you don't fork the model)
- You must design:
  - UIs that tolerate latency and partial failure
  - Clear loading/error/stale states
  - Simple, composable components
