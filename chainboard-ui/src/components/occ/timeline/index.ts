/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Timeline Module — Barrel Export
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// Types
export type {
  TimelineEventCategory,
  TimelineEventSeverity,
  PACLifecycleState,
  TimelineEvent,
  AgentACKRecord,
  WRAPMilestone,
  ReviewGateRecord,
  BERTimelineRecord,
  PACTimelineState,
  TimelineFilterOptions,
  TimelineDisplayOptions,
  TimelineViewProps,
  TimelineSegment,
  TimelineVisualizationData,
} from './types';

// Components
export { TimelineEventCard } from './TimelineEventCard';
export { TimelineSegment as TimelineSegmentComponent } from './TimelineSegment';
export { TimelineView } from './TimelineView';
export { default } from './TimelineView';
