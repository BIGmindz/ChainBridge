# Demo Script: Operator Console Settlement Intelligence Cockpit (M03)

## Setup

1. **Start Backend**:
   ```bash
   cd ChainBridge
   python -m chainboard.server
   ```

2. **Start Frontend**:
   ```bash
   cd chainboard-ui
   npm run dev
   ```

3. **Navigate to OC**:
   - Open `http://localhost:5173/oc`

## Demo Flow (10 minutes)

### 1. Layout Modes (2 min)

**Objective**: Show 3-way layout flexibility for different workflows

1. **Start in FULL_INTEL Mode** (🎯)
   - Point out balanced 3-panel view
   - Queue (left): Risk shipments with multi-select checkboxes
   - Detail (right): Shipment analysis
   - Money View (bottom): Payment intents

2. **Switch to HYBRID Mode** (⚡)
   - Click layout toggle → "Hybrid"
   - Note wider queue (50%) for scanning
   - Compact money view (25%)
   - Say: "Optimized for fast triage"

3. **Switch to CASH_OPS Mode** (💰)
   - Click layout toggle → "Cash Ops"
   - Money view now dominant (flex-1)
   - Queue minimal (w-80)
   - Say: "Payment operations focus"

4. **Verify Persistence**
   - Refresh page → mode persists
   - Check localStorage: `chainbridge.operator.layoutMode`

---

### 2. SLA Widget (1.5 min)

**Objective**: Real-time operational health visibility

1. **Point out SLA Widget** (top header, next to layout toggle)
   - Status badge: HEALTHY (green) | DEGRADED (amber) | CRITICAL (red)
   - Queue depth: Current items
   - P95: 95th percentile processing time
   - Ready/Blocked counts with colored dots
   - Heartbeat age

2. **Explain Polling**
   - "Updates every 30 seconds"
   - "Provides ops team instant visibility into system health"

3. **Simulate Load** (optional):
   - If backend supports it, trigger queue growth
   - Watch SLA status change from HEALTHY → DEGRADED

---

### 3. Queue Virtualization (1 min)

**Objective**: Smooth performance with large queues

1. **Load Large Queue** (>100 items)
   - Adjust filters or backend to show 100+ items
   - Point out virtualization indicator at top of queue:
     ```
     "Showing 61 of 237 items (window mode)"
     "#42 - #103"
     ```

2. **Navigate with Keyboard**
   - Press `J` / `K` to navigate
   - Watch window slide smoothly
   - Say: "Only renders ±30 rows around selection - handles 1000+ items"

---

### 4. Keyboard Navigation (2.5 min)

**Objective**: Enterprise-grade keyboard-first UX

1. **Basic Navigation**
   - `J` / `K` (or `↑` / `↓`): Navigate queue
   - `Enter`: Select shipment → detail panel updates
   - Show keyboard hints footer at bottom

2. **Export Workflow**
   - Navigate to shipment with "NEEDS SNAPSHOT" badge
   - Press `E` → Snapshot export created
   - Note: Green toast confirmation
   - Queue refreshes with updated status

3. **Multi-Select + Bulk Export**
   - Navigate to first shipment
   - Press `Space` → Row gets emerald tint
   - Navigate to second shipment
   - Press `Space` → Second row selected
   - Press `⇧ E` (Shift+E) → Bulk export
   - Say: "Console logs: Bulk export complete: 2 shipments"

4. **Checkboxes** (optional)
   - Hover over row → checkbox appears
   - Click checkbox → same multi-select behavior

---

### 5. Command Palette (1.5 min)

**Objective**: Quick actions without mouse

1. **Open Palette**
   - Press `⌘ K` (Mac) or `Ctrl K` (Windows/Linux)
   - Palette appears with backdrop blur

2. **Navigate Commands**
   - `↑` / `↓`: Navigate commands
   - Show available commands:
     - 💰 Go to ChainPay Cash View
     - 🚨 Filter: Critical Risk
     - ⚡ Toggle Layout Mode
     - 💵 Focus Money View Panel

3. **Execute Command**
   - Navigate to "Toggle Layout Mode"
   - Press `Enter`
   - Layout cycles: FULL_INTEL → HYBRID → CASH_OPS → repeat

4. **Search**
   - Type "chain" → filters to "Go to ChainPay"
   - Press `Enter` → navigates to `/chainpay`

5. **Close**
   - Press `Esc` → palette closes
   - Focus returns to queue

---

### 6. Detail Panel + Deep Linking (1.5 min)

**Objective**: Settlement intelligence integration

1. **Select Shipment**
   - Click or press `Enter` on shipment
   - Detail panel shows:
     - Shipment header (ID, corridor, mode, risk badge)
     - Risk summary
     - Event timeline
     - Actions (Export Snapshot button)

2. **Money View Panel**
   - Scroll to bottom → MoneyViewPanel
   - Click payment intent row
   - Note deep link: `/chainpay?intent=xyz123&highlight=ready`
   - Navigates to ChainPay with auto-selection

3. **Return to OC**
   - Browser back button → returns to OC
   - Selection preserved if deep-linked from specific shipment

---

## Key Talking Points

### Architecture
- **3 Layout Modes**: Optimized for different workflows (Intel / Triage / Cash Ops)
- **SLA Widget**: Real-time health monitoring (queue depth, p95, ready/blocked counts)
- **Virtualization**: Renders only visible window for 1000+ item queues
- **Keyboard-First**: Full feature parity without mouse

### Performance
- **Bundle**: 556KB (146KB gzipped) - only +9.68KB increase (~1.77%)
- **Virtualization**: 95% DOM reduction for large queues
- **Polling**: Intelligent intervals (5s queue, 15s summary, 30s SLA)

### UX Highlights
- **Multi-Select**: Space to toggle, Shift+E for bulk export
- **Command Palette**: Cmd+K for quick actions
- **Focus Management**: Returns focus after modal close
- **Visual Feedback**: Emerald ring for keyboard focus, tints for states
- **Keyboard Hints**: Always-visible footer with shortcuts

### Enterprise-Ready
- **Accessibility**: ARIA roles, keyboard-only navigation, focus traps
- **Persistence**: Layout mode saved to localStorage
- **Error Handling**: Skeleton states, error cards with retry
- **Migration**: Auto-migrates legacy WIDE_OPS/COMPACT_LIST modes

---

## Common Questions

**Q: Can I still use the mouse?**
A: Yes! All features work with mouse. Keyboard is optional but recommended for speed.

**Q: What happens if the queue has 2000 items?**
A: Virtualization activates automatically. Only 61 rows rendered at a time. Smooth performance.

**Q: Does multi-select work across pages?**
A: Multi-select is ID-based (not index-based), so yes - selections persist even with virtualization.

**Q: Can I customize keyboard shortcuts?**
A: Not yet, but it's on the roadmap for a future release.

**Q: What's the /sla/operator endpoint format?**
A: Returns JSON:
```json
{
  "queue_depth": 42,
  "p95_processing_time_seconds": 2.3,
  "ready_count": 35,
  "blocked_count": 7,
  "heartbeat_age_seconds": 15,
  "status": "healthy"
}
```

---

## Troubleshooting

**SLA Widget shows "SLA Unavailable"**
→ Check backend `/sla/operator` endpoint is running

**Virtualization not activating**
→ Queue must have >100 items. Check filters/backend data.

**Keyboard shortcuts not working**
→ Ensure OC has focus (click in queue area)

**Layout mode not persisting**
→ Check browser localStorage is enabled

**Build fails**
→ Run `npm run lint` first, fix any TypeScript errors

---

## Demo Checklist

Before demo:
- [ ] Backend running and `/sla/operator` endpoint live
- [ ] Frontend built: `npm run build` succeeds
- [ ] Queue has 50+ items (some with NEEDS_SNAPSHOT)
- [ ] At least 2-3 payment intents in Money View
- [ ] Browser localStorage cleared (to show fresh default)

During demo:
- [ ] Show all 3 layout modes
- [ ] Demonstrate SLA widget (point out each metric)
- [ ] Navigate with J/K keys
- [ ] Multi-select + bulk export
- [ ] Open command palette (Cmd+K)
- [ ] Show virtualization with 100+ items
- [ ] Verify keyboard hints footer visible

After demo:
- [ ] Answer questions
- [ ] Share OPERATOR_VIEW_NOTES.md for reference
- [ ] Highlight bundle size impact (+1.77%)
