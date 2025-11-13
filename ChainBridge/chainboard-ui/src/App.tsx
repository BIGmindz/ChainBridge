import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import ExceptionsPage from "./pages/ExceptionsPage";

/**
 * Main App Component
 * Defines routing, global search, and layout structure
 */
export default function App(): JSX.Element {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/shipments" element={<ShipmentsPage />} />
        <Route path="/exceptions" element={<ExceptionsPage />} />
      </Routes>
    </Layout>
  );
}
