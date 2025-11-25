/**
 * AppRoutes Component
 *
 * Central routing configuration for the ChainBoard UI.
 * All components rendered here are within BrowserRouter context.
 */

import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import ChainPayPage from "./pages/ChainPayPage";
import ExceptionsPage from "./pages/ExceptionsPage";
import IntelligencePage from "./pages/IntelligencePage";
import OperatorConsolePage from "./pages/OperatorConsolePage";
import OverviewPage from "./pages/OverviewPage";
import SandboxPage from "./pages/SandboxPage";
import SettlementsPage from "./pages/SettlementsPage";
import ShadowPilotPage from "./pages/ShadowPilotPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import TriagePage from "./pages/TriagePage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<IntelligencePage />} />
        <Route path="intelligence" element={<IntelligencePage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="shipments" element={<ShipmentsPage />} />
        <Route path="oc" element={<OperatorConsolePage />} />
        <Route path="operator" element={<OperatorConsolePage />} />
        <Route path="chainpay" element={<ChainPayPage />} />
        <Route path="settlements" element={<SettlementsPage />} />
        <Route path="exceptions" element={<ExceptionsPage />} />
        <Route path="triage" element={<TriagePage />} />
        <Route path="shadow-pilot" element={<ShadowPilotPage />} />
        <Route path="sandbox" element={<SandboxPage />} />
      </Route>
    </Routes>
  );
}
