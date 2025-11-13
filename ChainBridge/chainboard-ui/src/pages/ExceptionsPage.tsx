import { useEffect, useState } from "react";
import ExceptionsTable from "../components/ExceptionsTable";
import { ExceptionRow } from "../types";
import { apiClient } from "../services/api";

/**
 * Exceptions Page
 * Full-screen exceptions view with saved presets and export
 */
export default function ExceptionsPage(): JSX.Element {
  const [exceptions, setExceptions] = useState<ExceptionRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchExceptions = async (): Promise<void> => {
      setLoading(true);
      try {
        const data = await apiClient.getExceptions();
        setExceptions(data);
      } finally {
        setLoading(false);
      }
    };

    void fetchExceptions();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Exceptions</h1>
        <p className="text-gray-600 mt-2">
          Comprehensive view of all active exceptions with filtering, presets,
          and export
        </p>
      </div>
      <ExceptionsTable exceptions={exceptions} />
    </div>
  );
}
