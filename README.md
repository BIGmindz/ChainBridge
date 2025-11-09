# ChainBridge

> **Verifiable freight + programmable payments for enterprise supply chains.**  
> Pipe real-world events (EDI/API) through proofs and policies, then settle cash—automatically.

[![Status](https://img.shields.io/badge/status-early%20alpha-orange)](#)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](#license)
[![Built for](https://img.shields.io/badge/domain-Logistics%20%7C%20Fintech%20%7C%20RWA-black)](#)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-lightgrey)](#)

---

## Table of Contents
- [Why ChainBridge](#why-chainbridge)
- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Canonical Flows](#canonical-flows)
- [Modules](#modules)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API (ChainFreight)](#api-chainfreight)
- [Milestone Payments (ChainPay)](#milestone-payments-chainpay)
- [Observability & Ops](#observability--ops)
- [Security & Compliance](#security--compliance)
- [Enterprise Readiness Matrix](#enterprise-readiness-matrix)
- [Roadmap (30/60/90)](#roadmap-306090)
- [Repository Layout](#repository-layout)
- [Contributing](#contributing)
- [License](#license)

---

## Why ChainBridge
Enterprises want the **benefits of blockchain** (auditability, automation, instant reconciliation) **without the drama** (vendor lock-in, privacy leaks, “blockchain theater”). ChainBridge is the practical middle layer that:
- **Ingests events** from legacy + modern systems (EDI 945/856, APIs, webhooks) via the **Unifier** (powered by SEEBURGER BizHub).
- **Attaches verifiable proofs** (verifiable compute / zk attestations) to each event.
- **Executes policy** to **settle payments** and/or **actuate** off-chain/on-chain systems.
- **Writes clean audit trails** your auditors will actually accept.

**Mantra:**  
*Speed without proof gets blocked. Proof without pipes doesn’t scale. Pipes without cash don’t settle. You need all three.*

**PoC Corridor:** USD→MXN with targets: **P95 < 90s**, **STP ≥ 95%**, **audit prep time −80%**.

---

## What It Does
- **Tokenize shipments** → create a **FreightToken** with immutable metadata + proofs + risk context.
- **Score operational risk** via **ChainIQ** (ML engine) to shape holdbacks & payment timing.
- **Prove data lineage** via **Space and Time** (verifiable compute / zk proofs).
- **Settle cash** on **Ripple/XRPL** (pluggable rails later) with **policy-driven milestone releases**.
- **Actuate off-chain systems** with **Chainlink** jobs or direct adapters.
- **Reconcile + report** back to ERP/TMS with artifacts suitable for compliance.

---

## Architecture

```mermaid
flowchart LR
    A[Enterprise Systems\nERP / TMS / WMS] -->|EDI 945/856, API| U[Unifier (BizHub)]
    U --> C[ChainBridge Core]
    C -->|Tokenize| CF[ChainFreight API]
    C -->|Risk| IQ[ChainIQ ML Scoring]
    C -->|Proof| SxT[Space & Time\nVerifiable Compute / zk]
    C -->|Actuate| CL[Chainlink\nJobs/EA]
    C -->|Settle| XRPL[Ripple / XRPL]
    C -->|Notify| AUD[Audit Store\nERP/TMS Receipts]
    CF -->|FreightToken + Proofs + Risk| C