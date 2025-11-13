import { useState, useEffect } from "react";
import { Shipment } from "../types";
import { apiClient } from "../services/api";
import ShipmentsTable from "../components/ShipmentsTable";

/**
 * Shipments Page
 * Full shipment manifest with filtering and detailed view
 */
export default function ShipmentsPage(): JSX.Element {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchShipments = async (): Promise<void> => {
      try {
        const data = await apiClient.getShipments();
        setShipments(data);
      } catch (error) {
        console.error("Failed to load shipments:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchShipments();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Shipments</h2>
        <p className="text-gray-600 mt-1">Full shipment manifest with filtering</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading shipments...</p>
          </div>
        </div>
      ) : (
        <ShipmentsTable shipments={shipments} />
      )}
    </div>
  );
}
