import { render, screen, fireEvent } from "@testing-library/react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IoTHealthPanel } from "../IoTHealthPanel";
import { useIoTHealth } from "../../../hooks/useIoTHealth";

vi.mock("../../../hooks/useIoTHealth");

const mockedUseIoTHealth = useIoTHealth as unknown as Mock;

describe("IoTHealthPanel", () => {
  beforeEach(() => {
    mockedUseIoTHealth.mockReset();
  });

  it("renders fleet health metrics and anomalies", () => {
    mockedUseIoTHealth.mockReturnValue({
      data: {
        fleetId: "CHAINBOARD-FLEET-01",
        asOf: "2025-11-28T12:00:00Z",
        deviceCount: 120,
        online: 108,
        offline: 6,
        degraded: 4,
        latencySeconds: 12,
        anomalies: [
          {
            deviceId: "CB-IOT-2001",
            severity: "HIGH",
            label: "Temp excursion",
            lastSeen: "2025-11-28T11:58:00Z",
            shipmentReference: "SHP-2001",
            lane: "Shanghai → LA",
          },
          {
            deviceId: "CB-IOT-2002",
            severity: "MEDIUM",
            label: "GPS jitter",
            lastSeen: "2025-11-28T11:55:00Z",
          },
        ],
      },
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<IoTHealthPanel />);

    // Header + key metrics
    expect(screen.getByText("IoT Fleet Health")).toBeInTheDocument();
    expect(screen.getByText("Devices Monitored")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();

    // Anomalies section
    expect(screen.getByText("Active Anomalies")).toBeInTheDocument();
    expect(screen.getByText("Temp excursion")).toBeInTheDocument();
    expect(screen.getByText("GPS jitter")).toBeInTheDocument();

    // Count label ("2 issues") – tolerate internal whitespace
    expect(screen.getByText(/2\s+issues/i)).toBeInTheDocument();
  });

  it("renders error state with retry", () => {
    const refetch = vi.fn();
    mockedUseIoTHealth.mockReturnValue({
      data: undefined,
      isLoading: false,
      isFetching: false,
      error: new Error("Network down"),
      refetch,
    });

    render(<IoTHealthPanel />);

    expect(screen.getByText("IoT feed unavailable")).toBeInTheDocument();
    expect(screen.getByText("Network down")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Retry"));
    expect(refetch).toHaveBeenCalled();
  });
});
