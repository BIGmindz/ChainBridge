/**
 * Shadow Mode Dashboard Page
 *
 * Page wrapper for the Shadow Mode Dashboard.
 * Handles layout context and provides consistent navigation integration.
 *
 * Updated PAC-SONNY-020: Wired to /iq/shadow/* endpoints with Intelligence Panel.
 *
 * @module pages/ShadowPage
 */

import { ShadowIntelligencePanel } from "../components/intel/ShadowIntelligencePanel";
import ShadowDashboard from "../features/shadow/ShadowDashboard";

export default function ShadowPage(): JSX.Element {
  return (
    <div className="space-y-6">
      {/* New Intelligence Panel - Wired to live endpoints */}
      <ShadowIntelligencePanel />

      {/* Legacy Dashboard (will show placeholder until fully deprecated) */}
      <ShadowDashboard />
    </div>
  );
}
