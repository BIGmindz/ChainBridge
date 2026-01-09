/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Demo Components Index
 * PAC-BENSON-P35R: Operator + Auditor Demo Experience
 * 
 * Exports all demo experience components.
 * 
 * Author: SONNY (GID-02) — OCC Demo Flow
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// Main dashboard
export { DemoExperienceDashboard } from './DemoExperienceDashboard';

// Demo flows
export { OperatorHappyPath } from './OperatorHappyPath';
export { OperatorIntervention } from './OperatorIntervention';
export { AuditorReplay } from './AuditorReplay';

// Shared components
export { DemoStateBeacon, DemoBeaconGroup } from './DemoStateBeacon';
export { DemoStepProgress, DemoStepList } from './DemoStepIndicator';

// Types
export type * from './types';
