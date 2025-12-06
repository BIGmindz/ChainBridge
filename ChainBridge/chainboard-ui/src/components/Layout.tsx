import type { LucideIcon } from "lucide-react";
import {
    Activity,
    AlertTriangle,
    Coins,
    Command,
    FlaskConical,
    LayoutDashboard,
    ListTodo,
    Menu,
    PackageSearch,
    Radar,
    Search,
    Shield,
    TrendingUp,
    User,
    X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useDemo } from "../core/demo/DemoContext";

import { AlertsBell } from "./AlertsBell";
import { AlertsDrawer } from "./AlertsDrawer";
import { DemoControllerBar } from "./DemoControllerBar";
import { DemoSidebar } from "./DemoSidebar";

const navItems: { to: string; label: string; Icon: LucideIcon }[] = [
  { to: "/", label: "Global Intelligence", Icon: Radar },
  { to: "/risk", label: "Risk Console", Icon: Shield },
  { to: "/overview", label: "Overview", Icon: LayoutDashboard },
  { to: "/shipments", label: "Shipments", Icon: PackageSearch },
  { to: "/oc", label: "The OC", Icon: Command },
  { to: "/chainpay", label: "ChainPay", Icon: Coins },
  { to: "/settlements", label: "Settlements", Icon: Coins },
  { to: "/exceptions", label: "Exceptions", Icon: AlertTriangle },
  { to: "/triage", label: "Triage", Icon: ListTodo },
  { to: "/shadow-pilot", label: "Shadow Pilot", Icon: TrendingUp },
  { to: "/sandbox", label: "Sandbox", Icon: FlaskConical },
];

export default function Layout(): JSX.Element {
  const [searchValue, setSearchValue] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const { state: demoState } = useDemo();
  const highlightAlertsBell = demoState.currentStep?.highlightKey === "alerts_bell";

  const handleSearch = (event: React.FormEvent): void => {
    event.preventDefault();
    if (!searchValue.trim()) return;
    console.debug("Global search", searchValue);
    setSearchValue("");
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="hidden w-64 flex-col border-r border-slate-900/80 bg-slate-950/95 px-5 py-6 md:flex">
        <div className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            ChainBridge
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-100">Control Tower</p>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>

        <div className="mt-6 border-t border-slate-900/70 pt-4 text-[11px] text-slate-500">
          <p className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-emerald-400" />
            Monitoring 24/7
          </p>
          <p className="mt-1 text-[10px] text-slate-600">Freight · Risk · Payments</p>
        </div>
      </aside>

      <div className="relative flex flex-1 flex-col">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.07),_transparent_60%),radial-gradient(circle_at_bottom,_rgba(99,102,241,0.06),_transparent_55%)]"
        />
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,_rgba(15,23,42,0.6)_25%,_transparent_25%),linear-gradient(225deg,_rgba(15,23,42,0.5)_25%,_transparent_25%)] bg-[length:40px_40px] opacity-10" />

        <header className="relative z-10 flex items-center justify-between border-b border-slate-900/70 bg-slate-950/80 px-4 py-3 backdrop-blur">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-lg border border-slate-800 p-2 text-slate-100 md:hidden"
              aria-label="Open navigation"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <form
              onSubmit={handleSearch}
              className="flex items-center gap-2 rounded-lg border border-slate-800/70 bg-slate-950/70 px-3 py-2 text-xs"
            >
              <Search className="h-4 w-4 text-slate-400" />
              <input
                type="search"
                placeholder="Search shipments, events, references..."
                value={searchValue}
                onChange={(event) => setSearchValue(event.target.value)}
                className="w-56 bg-transparent text-xs text-slate-100 placeholder-slate-500 outline-none"
              />
            </form>
          </div>

          <div className="flex items-center gap-3">
            <SystemStatusPill label="Data Plane" status="online" />
            <SystemStatusPill label="Risk Engine" status="degraded" />
            <SystemStatusPill label="Payments" status="online" />
            <div className="hidden flex-col items-end text-[10px] text-slate-500 sm:flex">
              <span>Last sync: &lt;30s</span>
              <span>Environment: Sandbox</span>
            </div>
            <AlertsBell
              onClick={() => setAlertsOpen(true)}
              highlighted={highlightAlertsBell}
            />
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-800/80 bg-slate-950/80 text-slate-200"
              aria-label="User menu"
            >
              <User className="h-4 w-4" />
            </button>
          </div>
        </header>

        {sidebarOpen && (
          <div className="fixed inset-0 z-20 flex bg-black/60 md:hidden">
            <aside className="w-64 bg-slate-950/95 px-5 py-6 shadow-2xl">
              <div className="mb-8 flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    ChainBridge
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-100">Control Tower</p>
                </div>
                <button
                  type="button"
                  className="rounded-lg border border-slate-800 p-2 text-slate-200"
                  onClick={() => setSidebarOpen(false)}
                  aria-label="Close navigation"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <nav className="flex flex-col gap-1">
                {navItems.map((item) => (
                  <NavItem key={item.to} {...item} onNavigate={() => setSidebarOpen(false)} />
                ))}
              </nav>
            </aside>
            <div className="flex-1" onClick={() => setSidebarOpen(false)} />
          </div>
        )}

                <main className="relative z-0 flex-1 p-6">
          <Outlet />
        </main>
      </div>

      {/* Demo Mode Overlays */}
      <DemoControllerBar />
      <DemoSidebar />
      <AlertsDrawer open={alertsOpen} onClose={() => setAlertsOpen(false)} />
    </div>
  );
}

interface NavItemProps {
  to: string;
  label: string;
  Icon: LucideIcon;
  onNavigate?: () => void;
}

function NavItem({ to, label, Icon, onNavigate }: NavItemProps): JSX.Element {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        [
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition border border-transparent",
          "hover:border-slate-700 hover:bg-slate-900/70 hover:text-slate-50",
          isActive
            ? "bg-slate-900/90 text-slate-50 shadow-[0_0_0_1px_rgba(129,140,248,0.35)]"
            : "text-slate-400",
        ].join(" ")
      }
      onClick={onNavigate}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </NavLink>
  );
}

interface SystemStatusPillProps {
  label: string;
  status: "online" | "degraded" | "offline";
}

function SystemStatusPill({ label, status }: SystemStatusPillProps): JSX.Element {
  const base =
    "inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em]";
  const tones: Record<SystemStatusPillProps["status"], string> = {
    online: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
    degraded: "border-amber-500/50 bg-amber-500/10 text-amber-300",
    offline: "border-red-500/50 bg-red-500/10 text-red-300",
  };

  return (
    <span className={`${base} ${tones[status]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
