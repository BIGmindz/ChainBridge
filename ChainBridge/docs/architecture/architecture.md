# ChainBridge Architecture

This diagram summarizes how the primary subsystems interact today. The flow highlights ChainBoard as the customer-facing surface, the unified API tier, and the downstream intelligence + payments stacks (ChainIQ, ChainDocs, ChainPay) sharing snapshots and export events for Control Tower visibility.

```mermaid
graph LR
    subgraph UX[Experience Layer]
        CB[ChainBoard UI]
        Demo[Command Palette / Demo Controls]
    end

    subgraph API[ChainBridge API Gateway]
        APIServer[FastAPI Server / Routers]
        ChainDocsRouter[ChainDocs Router]
        ChainPayRouter[ChainPay Router]
        ChainIQRouter[ChainIQ Router]
    end

    subgraph IQ[ChainIQ Intelligence]
        Resolver[Template Resolver]
        HealthEngine[Shipment Health Engine]
        Snapshots[(DocumentHealthSnapshot)]
        ExportEvents[(SnapshotExportEvent Outbox)]
    end

    subgraph Docs[ChainDocs Spine]
        Shipments[(Shipments Table)]
        Documents[(Documents + Versions)]
    end

    subgraph Pay[ChainPay]
        Plans[(SettlementPlan + Milestones)]
    end

    subgraph Workers[Export Workers / Integrations]
        BIS[BIS Adapter]
        SXT[SxT Adapter]
        ML[ML Pipeline]
    end

    CB -->|fetch data| APIServer
    Demo --> APIServer
    APIServer -->|/chaindocs| ChainDocsRouter --> Shipments
    ChainDocsRouter --> Documents
    APIServer -->|/chainpay| ChainPayRouter --> Plans
    APIServer -->|/chainiq| ChainIQRouter --> HealthEngine
    HealthEngine --> Resolver
    HealthEngine --> Shipments
    HealthEngine --> Documents
    HealthEngine --> Plans
    HealthEngine --> Snapshots
    HealthEngine --> ExportEvents
    ExportEvents --> Workers
    Workers -->|status updates| APIServer
    CB -->|control tower views| ChainIQRouter
```

Use VS Code with “Markdown Preview Mermaid Support” (Cmd/Ctrl + Shift + V) or https://mermaid.live to render the diagram.
