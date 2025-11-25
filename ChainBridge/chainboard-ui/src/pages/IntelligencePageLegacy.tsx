/**
 * IntelligencePage Component
 *
 * SONNY PAC Global Intelligence - The new default home page.
 * Interactive geospatial console with money and risk awareness.
 *
 * This now serves as the main entry point showing the Global Intelligence view.
 *
 * V2: Adds drilldown navigation, operator preferences, and enhanced map visualization.
 */

import { Eye, EyeOff, Settings } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import AlertsIntelPanel from "../components/intel/AlertsIntelPanel";
import ChainTicker from "../components/intel/ChainTicker";
import IntelMapPanel from "../components/intel/IntelMapPanel";
import IoTIntelPanel from "../components/intel/IoTIntelPanel";
import RecommendationsIntelPanel from "../components/intel/RecommendationsIntelPanel";
import RiskIntelPanel from "../components/intel/RiskIntelPanel";
import SettlementsIntelPanel from "../components/intel/SettlementsIntelPanel";
import {
    loadIntelPrefs,
    saveIntelPrefs,
    type IntelligencePanelPrefs
} from "../core/preferences/intelligencePrefs";
import type { ControlTowerEvent } from "../core/types/realtime";

type IntelMode = "standard" | "full";

export default function IntelligencePage(): JSX.Element {
  const navigate = useNavigate();
  const [intelMode, setIntelMode] = useState<IntelMode>("standard");
  const [panelPrefs, setPanelPrefs] = useState<IntelligencePanelPrefs>(() => loadIntelPrefs());
  const [showPreferences, setShowPreferences] = useState(false);

  const emphasizeProblems = intelMode === "full";

  // Navigation callbacks for drilldowns
  const handleAlertClick = (alertId: string) => {
    // Navigate to Triage page
    navigate("/triage");
    // TODO: Add support for focusing a specific alert by id (query param or state)
    console.debug("[Intelligence] Navigate to alert:", alertId);
  };

  const handleAnomalyClick = () => {
    // Navigate to Intelligence (stay on page for now)
    navigate("/intelligence");
    // TODO: Deep-link into IoT anomalies view when available
    console.debug("[Intelligence] Navigate to IoT anomalies");
  };

  const handleBlockedCapitalClick = (milestoneId?: string) => {
    // Navigate to Settlements Console with optional deep-link
    if (milestoneId) {
      navigate(`/settlements?milestoneId=${encodeURIComponent(milestoneId)}`);
      console.debug("[Intelligence] Navigate to settlements with milestone:", milestoneId);
    } else {
      navigate("/settlements");
      console.debug("[Intelligence] Navigate to settlements (no specific milestone)");
    }
  };

  const handleTickerNavigate = (event: ControlTowerEvent) => {
    // Route based on event type
    switch (event.type) {
      case "alert_created":
      case "alert_status_changed":
      case "alert_updated":
        navigate("/triage");
        console.debug("[Intelligence] Ticker -> Triage for alert event");
        break;

      case "iot_reading":
        navigate("/intelligence");
        // TODO: Deep-link to IoT section or shipment detail
        console.debug("[Intelligence] Ticker -> IoT event");
        break;

      case "payment_state_changed": {
        const payload = event.payload as {
          milestone_id?: string;
          shipment_reference?: string;
          proofpack_hint?: { milestone_id?: string; has_proofpack?: boolean };
        };
        // Use canonical milestoneId from proofpack_hint if available, else fallback to payload.milestone_id
        const canonicalMilestoneId = payload.proofpack_hint?.milestone_id ?? payload.milestone_id;

        if (canonicalMilestoneId && payload.shipment_reference) {
          navigate(`/settlements?milestoneId=${encodeURIComponent(canonicalMilestoneId)}`);
          console.debug("[Intelligence] Ticker -> Settlements (payment event)", {
            canonical_milestone_id: canonicalMilestoneId,
            shipment_ref: payload.shipment_reference,
            has_proofpack: payload.proofpack_hint?.has_proofpack ?? false,
          });
        } else {
          navigate("/settlements");
          console.debug("[Intelligence] Ticker -> Settlements (no milestone ID in payload)");
        }
        break;
      }

      default:
        console.debug("[Intelligence] Ticker event (no navigation):", event.type);
    }
  };

  const handleTogglePanel = (panel: keyof IntelligencePanelPrefs) => {
    const updated = {
      ...panelPrefs,
      [panel]: !panelPrefs[panel],
    };
    setPanelPrefs(updated);
    saveIntelPrefs(updated);
  };

  const visiblePanelCount = Object.values(panelPrefs).filter(Boolean).length;

  return (
    <div className="space-y-6">
      {/* Page Header with Intel Mode Toggle and Preferences */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Intelligence</h1>
          <p className="mt-1 text-sm text-slate-400">
            Real-time operational intelligence across all systems
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Panel Preferences Toggle */}
          <button
            type="button"
            onClick={() => setShowPreferences(!showPreferences)}
            className="flex items-center gap-2 rounded-lg border border-slate-800/70 bg-slate-900/50 px-3 py-2 text-xs font-medium text-slate-300 transition-colors hover:border-slate-700 hover:bg-slate-900"
          >
            <Settings className="h-3.5 w-3.5" />
            Customize ({visiblePanelCount}/5)
          </button>

          {/* Intel Mode Toggle */}
          <div className="flex items-center gap-2 rounded-lg border border-slate-800/70 bg-slate-900/50 p-1">
            <button
              type="button"
              onClick={() => setIntelMode("standard")}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                intelMode === "standard"
                  ? "bg-slate-800 text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              <Eye className="h-3.5 w-3.5" />
              Standard
            </button>
            <button
              type="button"
              onClick={() => setIntelMode("full")}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                intelMode === "full"
                  ? "bg-amber-500/20 text-amber-300 shadow-sm"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              <EyeOff className="h-3.5 w-3.5" />
              Full Intel Mode
            </button>
          </div>
        </div>
      </div>

      {/* Panel Preferences Dropdown */}
      {showPreferences && (
        <div className="rounded-lg border border-slate-800/70 bg-slate-900/90 p-4">
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Visible Intelligence Panels
          </h4>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={panelPrefs.alerts}
                onChange={() => handleTogglePanel("alerts")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-300">Alerts</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={panelPrefs.risk}
                onChange={() => handleTogglePanel("risk")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-300">Risk</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={panelPrefs.iot}
                onChange={() => handleTogglePanel("iot")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-300">IoT</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={panelPrefs.settlements}
                onChange={() => handleTogglePanel("settlements")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-300">Settlements</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={panelPrefs.recommendations}
                onChange={() => handleTogglePanel("recommendations")}
                className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm text-slate-300">Recommendations</span>
            </label>
          </div>
        </div>
      )}

      {/* Chain Ticker - Live Event Feed */}
      <ChainTicker onNavigateFromEvent={handleTickerNavigate} />

      {/* Live Intelligence Map */}
      <IntelMapPanel />

      {/* Middle Intelligence Strip: Alerts, Risk, IoT */}
      <div className="grid gap-4 md:grid-cols-3">
        {panelPrefs.alerts && (
          <AlertsIntelPanel
            emphasize={emphasizeProblems}
            onAlertClick={handleAlertClick}
          />
        )}
        {panelPrefs.risk && (
          <RiskIntelPanel emphasize={emphasizeProblems} />
        )}
        {panelPrefs.iot && (
          <IoTIntelPanel
            emphasize={emphasizeProblems}
            onAnomalyClick={handleAnomalyClick}
          />
        )}
      </div>

      {/* Bottom Intelligence Strip: Settlements, Recommendations */}
      <div className="grid gap-4 md:grid-cols-2">
        {panelPrefs.settlements && (
          <SettlementsIntelPanel
            emphasize={emphasizeProblems}
            onBlockedCapitalClick={handleBlockedCapitalClick}
          />
        )}
        {panelPrefs.recommendations && (
          <RecommendationsIntelPanel emphasize={emphasizeProblems} />
        )}
      </div>
    </div>
  );
}
