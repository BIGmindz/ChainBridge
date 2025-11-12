# Copilot Context for ChainBridge Platform

This document provides structured guidance for GitHub Copilot to help generate code and architecture aligned with the ChainBridge platform goals.

---

## 🎯 Global Context: ChainBridge Overview

**ChainBridge** is an operating system for logistics built around three core modules:

- **ChainBoard**: Driver and enterprise identity & onboarding
- **ChainFreight**: Shipment lifecycle & supply chain execution  
- **ChainPay**: Payments, settlement, working capital

**ChainIQ** is a machine learning / multi-signal decision engine that scores shipments, drivers, lanes, and payments (risk, reliability, ETA, anomaly detection).

### Technology Stack

- **Language**: Python
- **API Framework**: FastAPI (microservices architecture)
- **ORM**: SQLAlchemy (starting with SQLite, later Postgres)
- **ML Integration**: ChainIQ exposed via HTTP APIs to other services
- **Data Validation**: Pydantic models throughout

### Design Principles

1. **Clean Architecture**: Separate concerns (models, services, API endpoints)
2. **Type Safety**: Full type hints on all functions
3. **Testability**: Functions designed to be unit testable
4. **Extensibility**: Structured to add compliance, audit, and advanced features later
5. **Clarity over Cleverness**: Explicit code that team members can understand and modify

---

## 📋 Copilot Chat System Prompt

Paste this into **Copilot Chat** once per workspace session:

``` bash
You are an assistant developer working on the ChainBridge platform.

ChainBridge is an operating system for logistics built around three core modules:
* ChainBoard: driver and enterprise identity & onboarding
* ChainFreight: shipment lifecycle & supply chain execution
* ChainPay: payments, settlement, working capital

We are also building ChainIQ, a machine learning / multi-signal decision engine that scores 
shipments, drivers, lanes, and payments (risk, reliability, ETA, etc.).

Tech stack:
* Python, FastAPI for microservices (e.g. chainboard-service, chainiq-service)
* SQLAlchemy (starting with SQLite, later Postgres)
* ChainIQ is called from other services via HTTP APIs

Your goals:
* Help design and implement clean, well-structured FastAPI services for ChainBoard and ChainIQ
* Help refactor an existing multi-signal ML engine (from a crypto trading bot) into ChainIQ, 
  focusing on logistics use-cases (risk scoring, prediction, anomaly detection)
* Write idiomatic, production-ready Python with type hints, Pydantic models, and clear separation of concerns

When generating code, prefer:
* FastAPI, Pydantic, SQLAlchemy
* Clear domain models: Driver, Shipment, Event, Payment
* Functions that could later be unit tested

Ask for file context when needed and suggest improvements, not just minimal completions.
```

---

## 🏗️ Service-Specific Prompts

### ChainBoard Service (Driver Onboarding)

**File-level header** (top of `chainboard-service/app/main.py`):

```python
"""
ChainBoard Service (ChainBridge)

Goal:
- Provide an API for driver identity and onboarding.
- Expose endpoints to create and fetch driver records.
- Use SQLAlchemy and SQLite (for now) for persistence.
- This is the MVP for the ChainBridge 'identity layer'.

Tasks for Copilot:
- Keep endpoints simple: POST /drivers, GET /drivers, GET /drivers/{id}.
- Use Pydantic models for request/response schemas.
- Use dependency-injected DB sessions.
- Make the code clean, explicit, and easy to extend (we'll add compliance checks later).
"""
```

**Copilot Chat prompt** to extend ChainBoard:

``` text
In chainboard-service/app/main.py, extend the driver API by adding:
* a PUT /drivers/{id} endpoint to update a driver's basic info (first_name, last_name, phone)
* a DELETE /drivers/{id} endpoint to soft-delete a driver (add an is_active: bool flag 
  rather than removing the row).

Use SQLAlchemy + Pydantic and follow the existing style in the file.
```

---

### ChainIQ Service (ML Decision Engine)

**File-level header** (top of `chainiq-service/app/main.py`):

```python
"""
ChainIQ Service (ChainBridge)

Goal:
- Provide an AI/ML decision engine for logistics risk and optimization.
- For now, expose a simple endpoint /score/shipment that returns a risk score.
- Later, we will plug in a multi-signal ML engine repurposed from a crypto trading bot.

Tasks for Copilot:
- Keep the API surface small and clear: /health and /score/shipment.
- Use Pydantic models for request/response.
- Structure the code so we can later import a separate module like chainiq_engine 
  that performs feature engineering and model inference.
- Do NOT assume trading or exchanges; this is logistics: shipments, drivers, lanes, payments.
"""
```

**Copilot Chat prompt** to wire an engine:

``` python
Create a module chainiq-service/app/engine.py that defines a simple placeholder function:

def score_shipment(shipment_id: str) -> float:
    ...

For now, have it just generate a deterministic dummy score based on the shipment_id 
(e.g., hash → 0.0–1.0).
Later we will replace this with real ML logic and calls to a feature store.
Then update chainiq-service/app/main.py to call this function inside /score/shipment 
instead of returning a hard-coded 0.42.
```

---

## 🚀 Example "Do This Next" Prompts

### Build More ChainBoard Functionality

``` text
Look at chainboard-service/app/main.py and chainboard-service/models/driver.py.
Add an endpoint GET /drivers/search that:
* accepts email and dot_number as query params (both optional)
* returns a list of matching drivers
* if no filters are provided, returns 400.

Keep the style consistent with existing endpoints.
```

### Start ChainFreight Service (Shipments)

``` text
Create a new FastAPI service under chainfreight-service/app/main.py and 
chainfreight-service/models/shipment.py.

Requirements:
* A Shipment model with fields: id, shipper_name, origin, destination, pickup_date, 
  delivery_date (planned), status.
* Endpoints:
  * POST /shipments → create a shipment
  * GET /shipments → list all shipments
  * GET /shipments/{id} → get one shipment
* Use SQLAlchemy and SQLite like ChainBoard.
* Add a /health endpoint.

Follow the patterns used in ChainBoard (DB session dependency, Pydantic schemas, etc.).
```

### Refactor Multi-Signal Engine into ChainIQ

``` text
Open the files that implement the multi-signal trading engine from the old bot 
(e.g. benson_system.py, tv_engine.py, feature_engineer.py).
I want to extract the generic parts into a new module under chainiq-service/app 
that does not depend on crypto exchanges or trading.

Create:
* chainiq-service/app/features.py → feature engineering utilities for generic time-series data
* chainiq-service/app/models.py → a simple ML wrapper with train() and predict() functions
* chainiq-service/app/risk_engine.py → a function score_shipment(features: dict) -> float

Focus on the structure first; we will plug in real training data later.
```

---

## 💡 Inline Comment Prompts for Functions

When writing a function and wanting Copilot to help, write a spec comment above it:

**Example: Scoring function**

```python
# This function will:
# - Accept a shipment_id and DB session
# - Load recent events for that shipment (status, timestamps)
# - Compute simple features like total transit time, delay vs planned, and number of exceptions
# - Return a risk score between 0.0 and 1.0 where higher = more risky
def score_shipment_from_db(shipment_id: str, db: Session) -> float:
    ...
```

Copilot uses this as its mini-spec and typically fills in a solid implementation you can then refine.

---

## 🎯 Master Prompt (Use When Stuck)

When unsure what to ask, paste this into **Copilot Chat**:

``` text
You are helping me build the ChainBridge platform.

Current focus:
* ChainBoard (driver onboarding, FastAPI + SQLAlchemy)
* ChainIQ (AI scoring service for shipments/drivers)

I am in file <FILE_PATH>.

1. Briefly explain what this file is doing.
2. Suggest the next concrete function or endpoint I should add.
3. Generate the code for that function, following the existing style.

Keep things simple and explicit; assume this is an MVP that we will harden later.
```

---

## 📂 Repository Structure (Target)

``` text
ChainBridge/
├── chainboard-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, routes
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── database.py          # DB session management
│   ├── requirements.txt
│   └── README.md
├── chainfreight-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── requirements.txt
│   └── README.md
├── chainpay-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── requirements.txt
│   └── README.md
├── chainiq-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # API endpoints
│   │   ├── engine.py            # Scoring logic
│   │   ├── features.py          # Feature engineering
│   │   ├── models.py            # ML model wrappers
│   │   └── database.py
│   ├── requirements.txt
│   └── README.md
├── COPILOT_CONTEXT.md           # This file
└── README.md                     # Main platform docs
```

---

## ✅ Quick Start with Copilot

1. **Initialize workspace context**: Paste the Global Copilot prompt (Section 1) into Copilot Chat.
2. **Pick a service**: Start with ChainBoard or ChainIQ.
3. **Create the file structure**: Ask Copilot to generate `main.py`, `models.py`, `schemas.py`.
4. **Use file-level headers**: Add the service-specific header comments to `main.py`.
5. **Build incrementally**: Use example prompts to add endpoints one by one.
6. **Reference this doc**: If Copilot drifts, paste a relevant section from this doc into chat.

---

## 🔄 Refactoring the Old ML Engine

The existing ChainBridge repo includes a sophisticated multi-signal crypto trading bot with:

- **Adaptive weight module** (`modules/adaptive_weight_module/`)
- **Market regime detection** (`modules/market_regime_module/`)
- **Risk management** (`modules/risk_management/`)
- **Multiple data sources** (alternative data, global macro, etc.)

**Strategy for reuse**:

1. Extract **generic feature engineering** (time-series processing, signal aggregation) into `chainiq-service/app/features.py`
2. Extract **regime detection logic** into `chainiq-service/app/risk_engine.py` (apply to logistics instead of markets)
3. Extract **adaptive weighting** into a generic scoring function
4. Replace exchange-specific code with logistics domain models (shipments, drivers, lanes)
5. Expose scoring via REST API in `chainiq-service/app/main.py`

---

**Last updated**: November 7, 2025  
**Maintained by**: ChainBridge Development Team
