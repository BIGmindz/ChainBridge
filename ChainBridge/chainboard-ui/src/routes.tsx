/**
 * AppRoutes Component
 *
 * Central routing configuration for the ChainBoard UI.
 * All components rendered here are within BrowserRouter context.
 *
 * NAVIGATION BOUNDARY RULES (PAC-BENSON-LIRA-PROOF-NAV-BOUNDARY-01):
 * - Routes are static declarations only — no conditional routing
 * - No validation logic in routing layer
 * - ProofPack routes treat data as opaque — existence only, not validity
 * - All routes are bookmarkable and work via direct URL entry
 * - Trust pages and Proof pages are fully decoupled
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01 — OC Governance route
 */

import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import ChainPayPage from "./pages/ChainPayPage";
import ExceptionsPage from "./pages/ExceptionsPage";
import IntelligencePage from "./pages/IntelligencePage";
import IqLabPage from "./pages/IqLabPage";
import OCExceptionCockpitPage from "./pages/OCExceptionCockpitPage";
import OCGovernancePage from "./pages/OCGovernancePage";
import OperatorConsolePage from "./pages/OperatorConsolePage";
import OverviewPage from "./pages/OverviewPage";
import SandboxPage from "./pages/SandboxPage";
import SettlementsPage from "./pages/SettlementsPage";
import ShadowPilotPage from "./pages/ShadowPilotPage";
import ShadowPage from "./pages/ShadowPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import TriagePage from "./pages/TriagePage";
import GovernancePage from "./pages/GovernancePage";
import ProofArtifactsPage from "./pages/ProofArtifactsPage";
import ProofPackDetailPage from "./pages/ProofPackDetailPage";
import RiskConsolePage from "./pages/RiskConsolePage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<IntelligencePage />} />
        <Route path="intelligence" element={<IntelligencePage />} />
        <Route path="iq-lab" element={<IqLabPage />} />
        <Route path="governance" element={<GovernancePage />} />
        <Route path="risk" element={<RiskConsolePage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="shipments" element={<ShipmentsPage />} />
        <Route path="oc" element={<OperatorConsolePage />} />
        <Route path="oc/governance" element={<OCGovernancePage />} />
        <Route path="oc-exceptions" element={<OCExceptionCockpitPage />} />
        <Route path="operator" element={<OperatorConsolePage />} />
        <Route path="chainpay" element={<ChainPayPage />} />
        <Route path="settlements" element={<SettlementsPage />} />
        <Route path="exceptions" element={<ExceptionsPage />} />
        <Route path="triage" element={<TriagePage />} />
        <Route path="shadow" element={<ShadowPage />} />
        <Route path="shadow-pilot" element={<ShadowPilotPage />} />
        <Route path="sandbox" element={<SandboxPage />} />
        <Route path="proof-artifacts" element={<ProofArtifactsPage />} />
        <Route path="proof-artifacts/:artifactId" element={<ProofPackDetailPage />} />
      </Route>
    </Routes>
  );
}
