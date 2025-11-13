import { useState, useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { NetworkVitals } from "../types";
import { apiClient } from "../services/api";
import ExceptionsPanel from "../components/ExceptionsPanel";
import ShipmentDetailDrawer from "../components/ShipmentDetailDrawer";
import KPIStrip from "../components/KPIStrip";

/**
 * Overview Page
 * Displays network vital signs, exceptions, and shipment detail
 */
export default function OverviewPage(): JSX.Element {
  const [vitals, setVitals] = useState<NetworkVitals | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | null>(null);

  useEffect(() => {
    const fetchVitals = async (): Promise<void> => {
      try {
        const data = await apiClient.getNetworkVitals();
        setVitals(data);
      } catch (error) {
        console.error("Failed to load vitals:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchVitals();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading vitals...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Overview</h2>
        <p className="text-gray-600 mt-1">
          Real-time view of network health, risks, and exceptions
        </p>
      </div>

      {/* KPI Strip */}
      {vitals && <KPIStrip vitals={vitals} />}

      {/* Exceptions and Detail Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Exceptions Panel (2/3 width on desktop) */}
        <div className="lg:col-span-2">
          <ExceptionsPanel onSelectShipment={setSelectedShipmentId} />
        </div>

        {/* Detail Drawer (1/3 width on desktop) */}
        <div className="lg:col-span-1">
          {selectedShipmentId ? (
            <ShipmentDetailDrawer
              shipmentId={selectedShipmentId}
              onClose={() => setSelectedShipmentId(null)}
            />
          ) : (
            <div className="card p-8 text-center">
              <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">
                Select a shipment from the exceptions list to view details
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
