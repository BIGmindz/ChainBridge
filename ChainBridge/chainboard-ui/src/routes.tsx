/**
 * AppRoutes Component
 *
 * Central routing configuration for the ChainBoard UI.
 * All components rendered here are within BrowserRouter context.
 */

import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import { OCCDashboard } from "./occ";
import AuditGovernancePage from "./pages/audit/AuditGovernancePage";
import ProofPackPage from "./pages/audit/ProofPackPage";
import ChainPayPage from "./pages/ChainPayPage";
import ExceptionsPage from "./pages/ExceptionsPage";
import IntelligencePage from "./pages/IntelligencePage";
import IqLabPage from "./pages/IqLabPage";
import OCExceptionCockpitPage from "./pages/OCExceptionCockpitPage";
import OCShellPage from "./pages/OCShellPage";
import OperatorConsolePage from "./pages/OperatorConsolePage";
import OverviewPage from "./pages/OverviewPage";
import SandboxPage from "./pages/SandboxPage";
import SettlementsPage from "./pages/SettlementsPage";
import ShadowPilotPage from "./pages/ShadowPilotPage";
import ShadowPage from "./pages/ShadowPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import TriagePage from "./pages/TriagePage";
import GovernancePage from "./pages/GovernancePage";
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
        <Route path="oc" element={<OCShellPage />} />
        <Route path="oc-legacy" element={<OperatorConsolePage />} />
        <Route path="occ" element={<OCCDashboard />} />
        <Route path="oc-exceptions" element={<OCExceptionCockpitPage />} />
        <Route path="operator" element={<OperatorConsolePage />} />
        <Route path="chainpay" element={<ChainPayPage />} />
        <Route path="settlements" element={<SettlementsPage />} />
        <Route path="exceptions" element={<ExceptionsPage />} />
        <Route path="triage" element={<TriagePage />} />
        <Route path="shadow" element={<ShadowPage />} />
        <Route path="shadow-pilot" element={<ShadowPilotPage />} />
        <Route path="sandbox" element={<SandboxPage />} />
      </Route>
      {/* Audit routes - standalone pages without Layout shell */}
      <Route path="/audit/governance/:artifactId" element={<AuditGovernancePage />} />
      <Route path="/audit/proofpack/:artifactId" element={<ProofPackPage />} />
      <Route path="/audit/settlements/:artifactId" element={<AuditGovernancePage />} />
      <Route path="/audit/exceptions/:artifactId" element={<AuditGovernancePage />} />
      <Route path="/audit/decisions/:artifactId" element={<AuditGovernancePage />} />
      <Route path="/audit/proofpacks/:artifactId" element={<AuditGovernancePage />} />
      <Route path="/audit/risk/:artifactId" element={<AuditGovernancePage />} />
    </Routes>
  );
}
