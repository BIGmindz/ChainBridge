import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Menu, X, SearchIcon, ShieldAlert } from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Main Layout Component
 * Provides shell with top bar, navigation, and content area
 */
export default function Layout({ children }: LayoutProps): JSX.Element {
  const [navOpen, setNavOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const environment = import.meta.env.VITE_ENVIRONMENT || "sandbox";

  const navItems = [
    { label: "Overview", href: "/" },
    { label: "Shipments", href: "/shipments" },
    { label: "Exceptions", href: "/exceptions" },
    { label: "Risk & Governance", href: "/risk", disabled: true },
    { label: "Payments", href: "/payments", disabled: true },
  ];

  const handleSearch = (e: React.FormEvent): void => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    console.log("Search:", searchQuery);
    setSearchQuery("");
  };

  const isActive = (href: string): boolean => location.pathname === href;

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Top Bar */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="flex items-center justify-between px-6 py-4">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setNavOpen(!navOpen)}
              className="md:hidden p-2 hover:bg-gray-100 rounded-lg"
              aria-label="Toggle navigation"
            >
              {navOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                ChainBridge Control Tower
              </h1>
              <p className="text-xs text-gray-500">
                {apiBaseUrl.includes("localhost") ? "Development" : environment}
              </p>
            </div>
          </div>

          {/* Search Bar */}
          <form
            onSubmit={handleSearch}
            className="hidden md:flex flex-1 mx-8 max-w-md"
          >
            <div className="relative w-full">
              <input
                type="text"
                placeholder="Search shipment, token, or carrier..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="submit"
                className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-700"
                aria-label="Search"
              >
                <SearchIcon size={18} />
              </button>
            </div>
          </form>

          {/* Environment Badge */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-primary-50 border border-primary-200 rounded-lg">
              <ShieldAlert size={16} className="text-primary-600" />
              <span className="text-xs font-semibold text-primary-700 uppercase">
                {environment}
              </span>
            </div>
          </div>
        </div>

        {/* Mobile Search */}
        <form onSubmit={handleSearch} className="md:hidden px-6 pb-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              type="submit"
              className="absolute right-3 top-2.5 text-gray-500"
              aria-label="Search"
            >
              <SearchIcon size={18} />
            </button>
          </div>
        </form>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <aside
          className={`${
            navOpen ? "block" : "hidden"
          } md:block w-64 bg-white border-r border-gray-200 overflow-y-auto`}
        >
          <nav className="px-4 py-6 space-y-2">
            {navItems.map((item) => (
              <button
                key={item.href}
                onClick={() => {
                  navigate(item.href);
                  setNavOpen(false);
                }}
                disabled={item.disabled}
                className={`w-full text-left px-4 py-3 rounded-lg font-medium transition-colors ${
                  isActive(item.href)
                    ? "bg-primary-50 text-primary-700 border-l-4 border-primary-600"
                    : "text-gray-700 hover:bg-gray-50"
                } ${item.disabled ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {item.label}
                {item.disabled && (
                  <span className="ml-2 text-xs text-gray-500">(Coming soon)</span>
                )}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          <div className="p-4 md:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
