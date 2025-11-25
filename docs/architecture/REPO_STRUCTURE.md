# ChainBridge Repository Structure

ChainBridge is organized to highlight the platform services that power the Operator Console (ChainBoard), ChainIQ intelligence, ChainPay settlements, and the upcoming ChainSense insights. This document is the single source of truth for where code lives and what can be safely ignored.

## Top-Level Layout

```text
/
├── services/            # Runtime services that expose APIs or UIs
├── platform/            # Shared libraries, data models, and proof packs
├── infra/               # Docker, Kubernetes, and CI/CD assets
├── docs/                # Architecture, product, and flow documentation
├── scripts/             # Developer and demo automation entry points
├── tests/               # API, service, and end-to-end test suites
└── legacy/              # Quarantined historical bots and experiments
```

- **services/** – Everything a customer or integration touches. Each subfolder is a deployable unit with its own README and dev scripts.
- **platform/** – Shared code that multiple services consume (data contracts, proof packs, or cross-service libraries).
- **infra/** – Deployment infrastructure separated by concern (`infra/docker`, `infra/k8s`, `infra/ci-cd`).
- **docs/** – Curated documentation aligned with architecture, product storytelling, and process flows. Start here before diving into code.
- **scripts/** – One-step commands for developers and demo teams. Nothing in here should require tribal knowledge.
- **tests/** – Automated coverage that mirrors the runtime stack: API tests, individual service tests, and end-to-end simulations.
- **legacy/** – Everything BensonBot and prior trading prototypes. Keep for audit/history only.

## Services Overview

```text
services/
├── api-gateway/         # FastAPI gateway that unifies ChainBridge APIs
├── chainboard-service/  # ChainBoard Operator Console (React + Vite)
├── chainiq-service/     # Shipment health, analytics, and intelligence engine
├── chainpay-service/    # Settlements, milestone tracking, and disbursement APIs
└── chainsense-service/  # Forthcoming data ingestion and anomaly detection
```

- **api-gateway** – The single backend endpoint exposed to customers. Routes requests to ChainIQ, ChainPay, and future services. Runs on `http://localhost:8001` in development.
- **chainboard-service** – The Operator Console UI that surfaces ChainIQ, ChainPay, and ChainSense data. Talks only to the gateway via `VITE_API_BASE_URL`.
- **chainiq-service** – Intelligence layer that powers health scores, corridor metrics, and exception management.
- **chainpay-service** – Handles settlements, payment states, and cash flow visibility.
- **chainsense-service** – Pipeline for ingesting external signals (capacity, weather, IoT) and feeding ChainIQ.

Each service folder contains:

1. A service-specific README with dev commands.
2. Infrastructure manifests under `infra/` referencing the service name.
3. Tests in `tests/services/<service-name>/` that mirror runtime behaviour.

## Platform Components

```text
platform/
├── common-lib/          # Shared utilities (auth, telemetry, logging)
├── data-model/          # Pydantic/SQLAlchemy schemas shared across services
└── proofpack/           # Reusable analytics and customer proof artifacts
```

- **common-lib** – Source of truth for shared helpers. Import this package instead of duplicating utilities inside services.
- **data-model** – Canonical DTOs and database models so API responses stay consistent.
- **proofpack** – Assets used in demos and pilots (sample datasets, notebooks, KPI generators).

## Infrastructure Layout

```text
infra/
├── docker/              # Dockerfiles and compose stacks per service
├── k8s/                 # Kubernetes manifests and Helm charts
└── ci-cd/               # GitHub Actions, pipelines, and quality gates
```

- **docker** – Development containers and production images. Compose files live alongside service names for clarity.
- **k8s** – Cluster manifests grouped by service and environment. Values files reference the same service folders as `services/`.
- **ci-cd** – Automated workflows (lint, build, deploy) with pointers back to `services/` and `platform/` modules.

## Scripts Breakdown

```text
scripts/
├── dev/                 # Local development helpers (start API, start UI, etc.)
├── demo/                # Guided demo flows for sales and investor walkthroughs
└── ops/ (optional)      # Runbooks for operations (add when needed)
```

- Focus on one-command developer flow. Anything required to get a service running should live under `scripts/dev/` and be referenced from the README and VS Code tasks.
- Demo assets (`scripts/demo/`) showcase the platform narrative end-to-end.

## Test Suites

```text
tests/
├── api/                 # Gateway contract tests
├── services/            # Service-specific unit and integration tests
└── e2e/                 # Full platform scenarios (API ↔ UI ↔ data services)
```

- Keep mocks and fixtures close to the tests that consume them.
- E2E suites should launch via the same scripts used by developers locally.

## Legacy (What Is Not ChainBridge)

```text
legacy/
├── bensonbot/           # Historical crypto bot sources and docs
└── experiments/         # Prototypes that never graduated into the platform
```

- **Do not** pull dependencies or logic from `legacy/` into current services. Treat these artifacts as read-only.
- If you need a capability from legacy code, port it into `platform/` or a modern service with a fresh design review.

## Where to Work

- **Operator Console (ChainBoard UI):** `services/chainboard-service`
- **API Gateway / External Integrations:** `services/api-gateway`
- **Risk & Intelligence (ChainIQ):** `services/chainiq-service`
- **Settlements (ChainPay):** `services/chainpay-service`
- **Upcoming Insights (ChainSense):** `services/chainsense-service`

Everything outside these paths is either shared infrastructure (`platform/`, `infra/`) or legacy archive. Start here, build fast, and keep the platform story tight.
