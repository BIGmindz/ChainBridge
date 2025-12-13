import { formatDistanceToNow } from "date-fns";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Flame,
  Wallet,
  Radio,
  User,
  MessageSquare,
  Plus,
} from "lucide-react";
import { useState, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ChainboardAPI } from "../core/api/client";
import { useNotifications } from "../core/notifications/NotificationContext";
import type {
  AlertWorkItem,
  AlertStatus,
  AlertSeverity,
  AlertSource
} from "../core/types/alerts";
import { useAlertWorkQueue } from "../hooks/useAlertWorkQueue";


// Mock current user (in production, this would come from auth context)
const CURRENT_USER = {
  id: "user-001",
  name: "Control Tower Operator",
  email: "operator@chainbridge.io",
  team: "Operations",
};

type ViewFilter = "my_alerts" | "all_open" | "critical" | "payment_holds" | "iot_anomalies";

const VIEW_CONFIGS: Record<ViewFilter, {
  label: string;
  icon: React.ElementType;
  params: {
    ownerId?: string;
    status?: AlertStatus;
    source?: AlertSource;
    severity?: AlertSeverity;
  };
}> = {
  my_alerts: {
    label: "My Alerts",
    icon: User,
    params: { ownerId: CURRENT_USER.id },
  },
  all_open: {
    label: "All Open",
    icon: AlertCircle,
    params: { status: "open" },
  },
  critical: {
    label: "Critical",
    icon: Flame,
    params: { severity: "critical" },
  },
  payment_holds: {
    label: "Payment Holds",
    icon: Wallet,
    params: { source: "payment" },
  },
  iot_anomalies: {
    label: "IoT Anomalies",
    icon: Radio,
    params: { source: "iot" },
  },
};

function getSeverityColor(severity: AlertSeverity): string {
  switch (severity) {
    case "critical":
      return "bg-red-100 text-red-800 border-red-300";
    case "warning":
      return "bg-amber-100 text-amber-800 border-amber-300";
    case "info":
      return "bg-blue-100 text-blue-800 border-blue-300";
  }
}

function getSourceColor(source: AlertSource): string {
  switch (source) {
    case "risk":
      return "bg-purple-100 text-purple-800";
    case "iot":
      return "bg-cyan-100 text-cyan-800";
    case "payment":
      return "bg-emerald-100 text-emerald-800";
    case "customs":
      return "bg-orange-100 text-orange-800";
  }
}

function getStatusIcon(status: AlertStatus): React.ReactNode {
  switch (status) {
    case "open":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case "acknowledged":
      return <Clock className="h-4 w-4 text-amber-500" />;
    case "resolved":
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  }
}

function WorkItemRow({
  item,
  onAssignToMe,
  onAcknowledge,
  onResolve,
  onAddNote,
  onNavigateToShipment,
}: {
  item: AlertWorkItem;
  onAssignToMe: (id: string) => void;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
  onAddNote: (id: string, message: string) => void;
  onNavigateToShipment: (ref: string) => void;
}) {
  const [noteText, setNoteText] = useState("");
  const [showNoteInput, setShowNoteInput] = useState(false);

  const handleAddNote = () => {
    if (noteText.trim()) {
      onAddNote(item.alert.id, noteText);
      setNoteText("");
      setShowNoteInput(false);
    }
  };

  const isAssignedToMe = item.owner?.id === CURRENT_USER.id;
  const canAcknowledge = item.alert.status === "open";
  const canResolve = item.alert.status !== "resolved";

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-colors">
      {/* Header Row */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3 flex-1">
          {getStatusIcon(item.alert.status)}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getSeverityColor(item.alert.severity)}`}>
                {item.alert.severity}
              </span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getSourceColor(item.alert.source)}`}>
                {item.alert.source}
              </span>
              <button
                onClick={() => onNavigateToShipment(item.alert.shipment_reference)}
                className="text-sm text-blue-400 hover:text-blue-300 hover:underline"
              >
                {item.alert.shipment_reference}
              </button>
            </div>
            <h3 className="text-sm font-medium text-slate-200 mb-1">{item.alert.title}</h3>
            <p className="text-xs text-slate-400">{item.alert.description}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2 ml-4">
          {!isAssignedToMe && (
            <button
              onClick={() => onAssignToMe(item.alert.id)}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Assign to me
            </button>
          )}
          {canAcknowledge && (
            <button
              onClick={() => onAcknowledge(item.alert.id)}
              className="px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors"
            >
              Acknowledge
            </button>
          )}
          {canResolve && (
            <button
              onClick={() => onResolve(item.alert.id)}
              className="px-3 py-1 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700 transition-colors"
            >
              Resolve
            </button>
          )}
        </div>
      </div>

      {/* Metadata Row */}
      <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
        <div className="flex items-center space-x-4">
          {item.owner ? (
            <span className="flex items-center space-x-1">
              <User className="h-3 w-3" />
              <span>{item.owner.name}</span>
            </span>
          ) : (
            <span className="text-slate-500">Unassigned</span>
          )}
          <span>{formatDistanceToNow(new Date(item.alert.createdAt), { addSuffix: true })}</span>
        </div>
        <button
          onClick={() => setShowNoteInput(!showNoteInput)}
          className="flex items-center space-x-1 text-slate-400 hover:text-slate-300"
        >
          <MessageSquare className="h-3 w-3" />
          <span>{item.notes.length} {item.notes.length === 1 ? "note" : "notes"}</span>
        </button>
      </div>

      {/* Notes Section */}
      {(showNoteInput || item.notes.length > 0) && (
        <div className="border-t border-slate-700 pt-2 mt-2">
          {item.notes.length > 0 && (
            <div className="space-y-2 mb-2">
              {item.notes.slice(-3).map((note) => (
                <div key={note.id} className="bg-slate-900/50 rounded p-2">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-300 font-medium">{note.author.name}</span>
                    <span className="text-slate-500">
                      {formatDistanceToNow(new Date(note.createdAt), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{note.message}</p>
                </div>
              ))}
            </div>
          )}
          {showNoteInput && (
            <div className="flex space-x-2">
              <input
                type="text"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Add a note..."
                className="flex-1 px-3 py-1 text-xs bg-slate-900 border border-slate-700 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAddNote();
                  if (e.key === "Escape") setShowNoteInput(false);
                }}
              />
              <button
                onClick={handleAddNote}
                className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center space-x-1"
              >
                <Plus className="h-3 w-3" />
                <span>Add</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TriagePage(): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { notifySuccess, notifyError } = useNotifications();

  // Get view from URL or default to "all_open"
  const currentView = (searchParams.get("view") as ViewFilter) || "all_open";

  const viewConfig = VIEW_CONFIGS[currentView];
  const { data, loading, refetch } = useAlertWorkQueue(viewConfig.params);

  const handleViewChange = (view: ViewFilter) => {
    setSearchParams({ view });
  };

  const handleAssignToMe = async (alertId: string) => {
    try {
      await ChainboardAPI.assignAlert(alertId, {
        ownerId: CURRENT_USER.id,
        ownerName: CURRENT_USER.name,
        ownerEmail: CURRENT_USER.email,
        ownerTeam: CURRENT_USER.team,
      });
      notifySuccess("Alert assigned to you");
      refetch();
    } catch (err) {
      notifyError("Failed to assign alert");
      console.error(err);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      await ChainboardAPI.updateAlertStatus(alertId, {
        status: "acknowledged",
        actorId: CURRENT_USER.id,
        actorName: CURRENT_USER.name,
        actorEmail: CURRENT_USER.email,
        actorTeam: CURRENT_USER.team,
      });
      notifySuccess("Alert acknowledged");
      refetch();
    } catch (err) {
      notifyError("Failed to acknowledge alert");
      console.error(err);
    }
  };

  const handleResolve = async (alertId: string) => {
    try {
      await ChainboardAPI.updateAlertStatus(alertId, {
        status: "resolved",
        actorId: CURRENT_USER.id,
        actorName: CURRENT_USER.name,
        actorEmail: CURRENT_USER.email,
        actorTeam: CURRENT_USER.team,
      });
      notifySuccess("Alert resolved");
      refetch();
    } catch (err) {
      notifyError("Failed to resolve alert");
      console.error(err);
    }
  };

  const handleAddNote = async (alertId: string, message: string) => {
    try {
      await ChainboardAPI.addAlertNote(alertId, {
        message,
        authorId: CURRENT_USER.id,
        authorName: CURRENT_USER.name,
        authorEmail: CURRENT_USER.email,
        authorTeam: CURRENT_USER.team,
      });
      notifySuccess("Note added");
      refetch();
    } catch (err) {
      notifyError("Failed to add note");
      console.error(err);
    }
  };

  const handleNavigateToShipment = (shipmentRef: string) => {
    navigate(`/shipments?search=${encodeURIComponent(shipmentRef)}`);
  };

  const sortedItems = useMemo(() => {
    if (!data?.items) return [];

    // Sort by: critical first, then by createdAt descending
    return [...data.items].sort((a, b) => {
      // Critical alerts first
      if (a.alert.severity === "critical" && b.alert.severity !== "critical") return -1;
      if (b.alert.severity === "critical" && a.alert.severity !== "critical") return 1;

      // Then by date (newest first)
      return new Date(b.alert.createdAt).getTime() - new Date(a.alert.createdAt).getTime();
    });
  }, [data?.items]);

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Alert Triage Work Queue</h1>
            <p className="text-sm text-slate-400 mt-1">
              Assign, acknowledge, and resolve alerts across risk, IoT, payment, and customs domains.
            </p>
          </div>
          <div className="text-sm text-slate-400">
            {data?.total ?? 0} {data?.total === 1 ? "alert" : "alerts"}
          </div>
        </div>

        {/* View Filters */}
        <div className="flex space-x-2" data-triage-work-queue>
          {Object.entries(VIEW_CONFIGS).map(([key, config]) => {
            const Icon = config.icon;
            const isActive = currentView === key;
            return (
              <button
                key={key}
                onClick={() => handleViewChange(key as ViewFilter)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{config.label}</span>
              </button>
            );
          })}
        </div>

        {/* Work Queue List */}
        <div className="space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : sortedItems.length === 0 ? (
            <div className="text-center py-12 bg-slate-800/30 rounded-lg border border-slate-700">
              <AlertCircle className="h-12 w-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400">No alerts in this view</p>
            </div>
          ) : (
            sortedItems.map((item) => (
              <WorkItemRow
                key={item.alert.id}
                item={item}
                onAssignToMe={handleAssignToMe}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
                onAddNote={handleAddNote}
                onNavigateToShipment={handleNavigateToShipment}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
