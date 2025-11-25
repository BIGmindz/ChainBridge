# Operator Console - Settlement Intelligence Cockpit

## Overview

The Operator Console (OC) has been transformed into a comprehensive Settlement Intelligence Cockpit with enterprise-grade UX, keyboard-first navigation, and real-time operational health monitoring.

## Architecture

### Layout Modes (3-Way Toggle)

The OC now supports three distinct layout modes optimized for different workflows:

#### 1. FULL_INTEL (🎯 Full Intel)
**Balanced settlement intelligence cockpit**
- Queue: 384px fixed width (`w-96`)
- Detail: Flex-1 (takes remaining space)
- Money View: 33% height (`h-1/3`)
- Use Case: Maximum visibility across all dimensions

#### 2. HYBRID (⚡ Hybrid)
**Operator triage mode**
- Queue: 50% width (`w-1/2`) - wider for scanning
- Detail: Flex-1
- Money View: 25% height (`h-1/4`) - compact
- Use Case: Fast queue triage with quick detail reference

#### 3. CASH_OPS (💰 Cash Ops)
**Payment operations focus**
- Queue: 320px fixed width (`w-80`) - minimal
- Detail: 384px fixed width (`w-96`)
- Money View: Flex-1 (takes most space)
- Use Case: Settlement timeline and payment intent focus

### Layout Persistence

Layout mode preferences are persisted to `localStorage` under key:
```
chainbridge.operator.layoutMode
```

Automatic migration from legacy modes:
- `WIDE_OPS` → `FULL_INTEL`
- `COMPACT_LIST` → `HYBRID`

## SLA Widget

Real-time operational health monitoring in the OC header.

### Metrics Displayed
- **Status**: `healthy` | `degraded` | `critical`
- **Queue Depth**: Total items in operator queue
- **P95 Processing Time**: 95th percentile latency (seconds)
- **Ready Count**: Items ready for processing (green dot)
- **Blocked Count**: Items blocked by gaps/risk (red dot)
- **Heartbeat Age**: Time since last system heartbeat (seconds)

### API Endpoint
```
GET /sla/operator
```

### Polling Strategy
- Interval: 30 seconds
- Stale Time: 25 seconds
- Retry: 2 attempts with 2s delay

### Status Colors
- **Healthy**: Emerald (green) - all systems nominal
- **Degraded**: Amber (yellow) - performance issues detected
- **Critical**: Rose (red) - immediate attention required

## Queue Virtualization

Optimizes rendering for large queues (500-2000+ items).

### Activation Threshold
```typescript
VIRTUALIZATION_THRESHOLD = 100 items
```

### Window Size
```typescript
WINDOW_SIZE = 30 rows (±30 around selected index)
```

### Behavior
- When queue > 100 items: Renders only 61 rows (focusIndex - 30 to focusIndex + 30)
- Displays indicator: "Showing 61 of N items (window mode)"
- Shows range: "#42 - #103"
- Maintains keyboard navigation alignment
- Multi-select IDs preserved (ID-based, not index-based)

### Performance Impact
- Smooth scrolling with 1000+ items
- Reduced DOM nodes by ~95% for large queues
- Maintained full keyboard navigation UX

## Keyboard Shortcuts

All shortcuts work globally when OC has focus:

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑` / `↓` | Navigate | Move selection up/down in queue |
| `J` / `K` | Navigate (Vim) | Vim-style navigation |
| `Enter` | Select | Open selected shipment in detail panel |
| `E` | Export | Export snapshot for focused shipment |
| `Space` | Multi-select | Toggle multi-select on focused row |
| `⇧ E` | Bulk Export | Export all multi-selected shipments |
| `⌘ K` / `Ctrl K` | Command Palette | Open command palette |
| `/` | Focus Search | Focus search input (future) |

### Multi-Select Workflow
1. Navigate to shipment with `J/K` or arrow keys
2. Press `Space` to toggle selection (emerald background tint)
3. Repeat for additional shipments
4. Press `⇧ E` to bulk export all selected

### Command Palette (⌘ K)
- **Go to ChainPay Cash View** - Navigate to /chainpay
- **Filter: Critical Risk** - Apply critical filter
- **Toggle Layout Mode** - Cycle FULL_INTEL → HYBRID → CASH_OPS
- **Focus Money View Panel** - Scroll to payment intents

## Accessibility (A11y)

### ARIA Roles
- Queue: `role="list"` with `role="listitem"` rows
- Command Palette: `role="dialog"` with focus trap
- Buttons: `aria-pressed` states on toggle controls

### Focus Management
- Command Palette auto-focuses search input on open
- Focus returns to trigger on close
- Keyboard hints footer always visible

### Visual Feedback
- Keyboard focus: Emerald ring with 2px border
- Mouse hover: Slate-700 background
- Multi-select: Emerald tint background
- Loading: Skeleton states
- Error: Rose-tinted cards with icons

### Keyboard-Only Navigation
All features fully accessible without mouse:
- Queue navigation
- Detail panel browsing
- Layout mode switching
- Snapshot export
- Multi-select operations
- Command palette

## Components Added/Modified

### New Components
- `SLAWidget.tsx` - Operational health display
- `KeyboardHintsFooter.tsx` - Shortcut reference
- `OperatorCommandPalette.tsx` - Command palette (Ctrl+K)

### Modified Components
- `OCLayout.tsx` - Added SLA widget and keyboard hints footer
- `OCQueueTable.tsx` - Added virtualization and multi-select
- `LayoutModeToggle.tsx` - 3-way segmented control
- `OperatorConsolePage.tsx` - Integrated all features
- `useKeyboardNavigation.ts` - Enhanced with multi-select + palette triggers

### New Hooks
- `useSLA.ts` - SLA status polling hook

### Configuration
- `layoutConfig.ts` - Expanded to 3 modes with explicit dimensions

## Bundle Impact

### Before
- 547 KB (145.17 KB gzipped)
- 1913 modules

### After
- 556.68 KB (146.14 KB gzipped)
- 1916 modules

### Delta
- **+9.68 KB** (+0.97 KB gzipped)
- **+3 modules**
- **~1.77% increase** - well within acceptable range

## Future Enhancements

### Detail Panel Tabs (Deferred)
- Overview | Settlement | Risk | Docs
- Tab-based navigation with keyboard support
- Integration with SettlementTimeline, PricingBreakdownCard, RiskBlocksCard

### Search/Filter UI
- Global search input
- `/` keyboard shortcut to focus
- Filter by risk level, corridor, mode

### Advanced Virtualization
- Bi-directional scrolling
- Dynamic row heights
- Smooth scroll-to-index

## Testing Checklist

- [ ] Layout modes persist across sessions
- [ ] SLA widget updates every 30s
- [ ] Virtualization activates at 100+ items
- [ ] All keyboard shortcuts work
- [ ] Multi-select + bulk export functional
- [ ] Command palette opens/closes correctly
- [ ] Focus returns after palette close
- [ ] Keyboard hints visible in footer
- [ ] Build succeeds with 0 errors
- [ ] Bundle size < 600KB gzipped
