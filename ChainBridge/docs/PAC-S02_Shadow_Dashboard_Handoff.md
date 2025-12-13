# PAC-S02: Shadow Mode Dashboard - Handoff Document

**Status**: ✅ Scaffolding Complete - Ready for Backend Integration
**Engineer**: SONNY (GID-02)
**Date**: 2025-01-XX
**Build Status**: ✅ Passing
**Lint Status**: ⚠️ Clean (no new errors, pre-existing warnings in unrelated files)

---

## Executive Summary

Shadow Mode Dashboard v0.1 is fully scaffolded and ready for drop-in backend integration. All UI components, types, and API stubs are in place. The moment Cody/Dan expose REST endpoints, only minor wire-up is required.

### What Was Built

- **TypeScript API Client** (`api/shadow.ts`) with complete type definitions
- **Three Core Components**:
  - `ShadowStatsCard` - Aggregate metrics (total events, avg delta, P95/P99)
  - `ShadowCorridorTable` - Per-corridor breakdown with color-coded deltas
  - `ShadowEventsTable` - Scrollable event stream
- **Main Dashboard** (`ShadowDashboard.tsx`) orchestrating all components
- **Routing Integration** - Navigation item + page route at `/shadow`
- **Loading/Error/Empty States** - Full UX coverage for all scenarios

### What Was NOT Built (Reality Guardrail Respected)

- ❌ No fake data generation
- ❌ No invented API endpoints
- ❌ No mock implementations that would need removal
- ✅ Only clean stubs with clear TODO markers

---

## Architecture

### File Structure

```
chainboard-ui/
├── src/
│   ├── api/
│   │   └── shadow.ts                  # API client + TypeScript types
│   ├── features/
│   │   └── shadow/
│   │       ├── ShadowDashboard.tsx    # Main container
│   │       ├── ShadowStatsCard.tsx    # Stats display
│   │       ├── ShadowCorridorTable.tsx # Corridor breakdown
│   │       └── ShadowEventsTable.tsx  # Event stream
│   ├── pages/
│   │   └── ShadowPage.tsx             # Page wrapper
│   ├── routes.tsx                     # Added /shadow route
│   └── components/Layout.tsx          # Added navigation item
```

### Component Hierarchy

```
ShadowPage
└── ShadowDashboard
    ├── ShadowStatsCard
    ├── ShadowCorridorTable
    └── ShadowEventsTable
```

### Data Flow (When Backend Exists)

```
Backend (/iq/ml/shadow/*)
    ↓
API Client (api/shadow.ts)
    ↓
ShadowDashboard (state management)
    ↓
Individual Components (props)
    ↓
UI Rendering
```

---

## Backend Integration Checklist

### Required REST Endpoints

Backend team (Cody/Dan) needs to expose these endpoints:

1. **`GET /iq/ml/shadow/stats?window_hours=24`**
   - Returns: `ShadowStats` (total events, avg delta, P95/P99)
   - Current implementation: `shadow_repo.py::calculate_aggregate_stats()`

2. **`GET /iq/ml/shadow/events?limit=50&corridor=optional`**
   - Returns: `ShadowEvent[]` (event stream with dummy/real/delta)
   - Current implementation: `shadow_repo.py::get_recent_events()`

3. **`GET /iq/ml/shadow/corridors?window_hours=24`**
   - Returns: `CorridorStats[]` (per-corridor breakdown)
   - Current implementation: `shadow_repo.py::get_corridor_stats()`

4. **`GET /iq/ml/shadow/high-delta?threshold=0.2&limit=20`**
   - Returns: `ShadowEvent[]` (only high-delta anomalies)
   - Current implementation: `shadow_diff.py::find_high_delta_events()`

### Integration Steps

1. **Backend Team**:
   ```python
   # In chainiq-service/routes/shadow.py (or similar)
   from shadow_repo import ShadowRepo

   @router.get("/iq/ml/shadow/stats")
   def get_shadow_stats(window_hours: int = 24):
       repo = ShadowRepo()
       return repo.calculate_aggregate_stats(window_hours)
   ```

2. **Frontend Team**:
   ```typescript
   // In api/shadow.ts
   // 1. Uncomment the httpGet import
   import { httpGet } from "../services/apiClient";

   // 2. Replace throw statements with real calls
   export async function fetchShadowStats(windowHours: number = 24): Promise<ShadowStats> {
     return httpGet<ShadowStats>(`/iq/ml/shadow/stats?window_hours=${windowHours}`);
   }
   ```

3. **Remove warning banners** in `ShadowDashboard.tsx` (lines 105-124)

4. **Test in UI**: Navigate to `/shadow` and verify data loads

---

## Type Definitions

All TypeScript interfaces are defined in [api/shadow.ts](../chainboard-ui/src/api/shadow.ts):

```typescript
export interface ShadowEvent {
  event_id: string;
  shipment_id: string;
  corridor: string;
  dummy_score: number;
  real_score: number;
  delta: number;
  timestamp: string;
}

export interface ShadowStats {
  total_events: number;
  avg_delta: number;
  max_delta: number;
  p95_delta: number;
  p99_delta: number;
  start_time: string;
  end_time: string;
}

export interface CorridorStats {
  corridor: string;
  event_count: number;
  avg_delta: number;
  max_delta: number;
  last_event: string;
}
```

---

## UX Design Patterns

### Color-Coded Deltas

- **Green** (<0.1): Models aligned
- **Yellow** (0.1-0.2): Minor drift
- **Red** (>0.2): Significant divergence

### State Handling

All components include:
- ⏳ **Loading skeletons** (animated placeholders)
- ❌ **Error states** (with backend unavailability notices)
- 📋 **Data states** (tables/cards with real content)
- 📭 **Empty states** (clear messaging when no data)

### Neurodivergent-Friendly Design

- Clear labels and minimal cognitive load
- Consistent layout patterns
- High-contrast color scheme (slate/indigo)
- Semantic HTML for screen readers

---

## Testing Strategy

### Pre-Backend Testing

1. **UI rendering**: ✅ Build passes, no TypeScript errors
2. **State management**: ✅ useState hooks correctly wired
3. **Error handling**: ✅ All API stubs throw descriptive errors
4. **Loading states**: ✅ Skeletons render correctly
5. **Routing**: ✅ Navigation link appears in sidebar

### Post-Backend Testing

Once endpoints exist:

```bash
# 1. Start backend services
docker-compose up chainiq-service

# 2. Start frontend dev server
cd chainboard-ui && npm run dev

# 3. Navigate to http://localhost:5173/shadow

# 4. Verify:
# - Stats card loads aggregate metrics
# - Corridor table shows per-lane breakdown
# - Events table populates with recent scorings
# - Refresh button re-fetches data
```

### Edge Cases to Test

- [ ] Empty database (zero shadow events)
- [ ] High-delta events (red badges appear)
- [ ] Corridor filtering (if implemented)
- [ ] Long event streams (scrolling behavior)
- [ ] Backend timeout/error handling

---

## Known Limitations

1. **Backend endpoints don't exist yet** - API calls will fail until Cody/Dan add routes
2. **No real-time updates** - Dashboard uses manual refresh, not WebSocket (future enhancement)
3. **No filtering UI** - Corridor/date filters could be added later
4. **No export functionality** - CSV/JSON export not implemented

---

## Future Enhancements (Post-v0.1)

1. **Real-time streaming** via WebSocket (`/iq/ml/shadow/stream`)
2. **Historical drift charts** (trend lines over time)
3. **Alerting** (notify when P95 delta exceeds threshold)
4. **Corridor filtering** (dropdown to focus on specific trade lanes)
5. **Export to CSV** (for offline analysis)

---

## Verification Commands

```bash
# Build check
cd chainboard-ui && npm run build
# Expected: ✅ Build succeeds in ~5 seconds

# Lint check (shadow files only)
npx eslint src/features/shadow src/api/shadow.ts src/pages/ShadowPage.tsx
# Expected: ✅ No errors (warnings acceptable)

# Dev server (to manually test routing)
npm run dev
# Expected: ✅ Navigate to /shadow, see backend unavailable notice
```

---

## Contact

- **Frontend (Scaffolding)**: SONNY (GID-02)
- **Backend (Integration)**: Cody/Dan (ChainIQ team)
- **QA (Final Testing)**: Dependent on backend deployment timeline

---

## References

- **Backend shadow code**:
  - `chainiq-service/models_shadow.py` (DB schema)
  - `chainiq-service/shadow_repo.py` (queries)
  - `chainiq-service/shadow_diff.py` (analytics)

- **Frontend patterns**:
  - `features/chainiq/IqLabPanel.tsx` (similar dashboard structure)
  - `api/iqLab.ts` (API client reference)

- **Design system**:
  - `components/ui/Card.tsx` (consistent card wrapper)
  - `components/ui/LoadingStates.tsx` (skeleton patterns)

---

**🎯 Next Action**: Backend team to expose `/iq/ml/shadow/*` REST endpoints, then frontend wires API calls (5 minutes of work).
