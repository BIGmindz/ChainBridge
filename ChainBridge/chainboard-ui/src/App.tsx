import React, { useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { SearchIcon } from "lucide-react";
import Layout from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import ShipmentsPage from "./pages/ShipmentsPage";
import ExceptionsPage from "./pages/ExceptionsPage";

/**
 * Main App Component
 * Defines routing, global search, and layout structure
 */
export default function App(): JSX.Element {
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent): void => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    // For now, just log the query - can be enhanced to search within pages
    console.log("Search query:", searchQuery);
    setSearchQuery("");
  };

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
