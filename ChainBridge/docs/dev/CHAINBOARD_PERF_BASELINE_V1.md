# CHAINBOARD_PERF_BASELINE_V1

## 1. Purpose

This document captures the **initial performance baseline** for the ChainBridge Operator Console (ChainBoard UI / OC).

The goal is not heavy optimization yet — it’s to establish:
- A concrete **“Version 1” snapshot** of performance.
- A reference point for future UI/UX and performance improvements.
- A shared place to record how changes affect load time and perceived speed.

---

## 2. Test Context

**Date of measurement:** `YYYY-MM-DD`
**Tester:** `Your name / environment`
**Branch/commit:**
- Branch: `feature/chainpay-consumer` (or current)
- Commit: `` `<short SHA>` ``

**Environment:**
- Mode: `local dev / local prod build / hosted preview`
- URL tested: `http://localhost:5173/...` or preview URL
- Node version: `vXX`
- Browser: `Chrome <version>` (desktop)
- Machine: `MacBook <specs>` (optional but useful)

**Screen under test:**
- Route: **Operator Console**
- Panels currently in play:
  - Guardrails – USD→MXN
  - ChainPay Settlement
  - ChainPay Analytics
  - Any additional widgets/features loaded by default on OC

---

## 3. Measurement Setup

**Tool used:**
- `Lighthouse / Chrome DevTools / WebPageTest / other`

**Profile:**
- Device: `Desktop` (primary)
- Throttling: `Default Lighthouse settings / none / custom`
- Runs:
  - Number of runs: `N` (e.g. 3)
  - Notes: `Used best-of / median / single run`

Optional notes:
- Any extensions disabled?
- Any ad-blockers/caching affecting results?

---

## 4. Lighthouse / Performance Summary

> Paste key metrics from your report here.

**Overall Performance Score (Desktop):** `XX / 100`

**Core Metrics (from primary/best run):**

| Metric              | Value       | Notes                                 |
|---------------------|------------:|----------------------------------------|
| LCP (Largest Contentful Paint) | `X.XX s` |                                  |
| FID / INP           | `XXX ms`    | or “not available”, depending on tool |
| CLS (Cumulative Layout Shift) | `0.0X` |                                      |
| TBT / TTI           | `X.XX s`    |                                      |
| First Contentful Paint | `X.XX s` |                                      |
| Time to Interactive | `X.XX s`    |                                      |

If your tool gives additional numbers, add them below or expand the table.

---

## 5. Bundle / Network Snapshot

*(From Chrome DevTools → Network / Coverage / Lighthouse details)*

**High-level notes:**

- Main JS bundle size: `~X.X MB`
- Total transferred (initial load): `~X.X MB`
- Number of requests on first load: `N`
- Any obviously large libs:
  - `e.g. @loaders.gl/*, some charting lib, etc. (if identified)`

You can also paste a short list of the **top 3–5 largest bundles** by size.

---

## 6. Observations

Short bullet list of what you saw:

- ✅ OC is fully usable within `~X sec` on desktop.
- ⚠️ Noted Vite warning: `spawn not exported by __vite-browser-external` from `@loaders.gl/worker-utils` (non-blocking).
- ⚠️ Bundle size warnings (~1.6 MB chunks) — acceptable for now, but flagged as tech debt.
- UX notes:
  - e.g. “Guardrail/Analytics panels render in under 1s after main shell appears.”
  - e.g. “No noticeable layout jank / CLS is very low.”

---

## 7. Known Warnings / Tech Debt (Linked Issues)

- Build warning tracking:
  - **Issue:** _Tech Debt: Chainboard UI build warnings (Vite + loaders.gl + bundle size)_
  - Notes: loaders.gl + chunk size; non-blocking but logged.
- Baseline perf tracking (this doc):
  - **Issue:** _Add baseline performance profile for Chainboard UI (OC)_

Add GitHub issue links here once they exist.

---

## 8. Future Optimization Ideas (Not Action Items Yet)

Just a parking lot — no commitment yet:

- Route-level code splitting or lazy loading for heavy panels (e.g., advanced analytics).
- Review large third-party libs (e.g., loaders.gl, charting libs) for possible lighter alternatives.
- Consider prefetching / caching strategies once we know typical OC usage patterns.
- Synthetic perf tests in CI (optional, long-term).

---

## 9. Version History

- **V1 – `YYYY-MM-DD` – Initial baseline on `feature/chainpay-consumer`**
  - First recorded Lighthouse run and metrics.
  - Warnings logged, no optimizations applied yet.
