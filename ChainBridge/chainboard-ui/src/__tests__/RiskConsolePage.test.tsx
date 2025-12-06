import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RiskConsolePage from "../pages/RiskConsolePage";
import { fetchRiskEvaluations, fetchRiskMetricsLatest } from "../features/chainiq/risk/riskApi";
import { mockRiskEvaluations } from "../features/chainiq/risk/mockRiskEvaluations";
import { RiskModelMetrics } from "../features/chainiq/risk/types";

// Mock the API module
vi.mock("../features/chainiq/risk/riskApi", () => ({
  fetchRiskEvaluations: vi.fn(),
  fetchRiskMetricsLatest: vi.fn(),
}));

const mockMetrics: RiskModelMetrics = {
  id: "metrics-1",
  model_version: "v1.0",
  evaluation_window_start: "2025-01-01T00:00:00Z",
  evaluation_window_end: "2025-01-07T00:00:00Z",
  eval_count: 742,
  critical_incident_recall: 0.723,
  high_risk_precision: 0.85,
  ops_workload_percent: 0.14,
  loss_value_coverage_pct: 0.635,
  calibration_low_rate: 0.05,
  calibration_high_rate: 0.1,
  has_failures: false,
  has_warnings: false,
  fail_messages: [],
  warning_messages: [],
  created_at: "2025-01-08T00:00:00Z",
};

describe("RiskConsolePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);
    expect(screen.getByText("ChainIQ – Risk Console")).toBeDefined();
    // Wait for data to load
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());
  });

  it("renders the mock data table", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());
    expect(screen.getByText("SHP-1002")).toBeDefined();
  });

  it("opens details panel on row click", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());

    const row = screen.getByText("SHP-1001");
    fireEvent.click(row);

    // Check for details panel content
    expect(screen.getByText("Evaluation Details")).toBeDefined();
    expect(screen.getByText("Features Snapshot")).toBeDefined();
    expect(screen.getByText("$150,000")).toBeDefined(); // Value USD
  });

  it("filters by risk band", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());

    // Click "High" filter
    const highFilter = screen.getByText("High");
    fireEvent.click(highFilter);

    // SHP-1001 is HIGH, should be visible
    expect(screen.getByText("SHP-1001")).toBeDefined();

    // SHP-1003 is LOW, should NOT be visible
    expect(screen.queryByText("SHP-1003")).toBeNull();
  });

  it("filters by search query", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());

    // Type in search box
    const searchInput = screen.getByPlaceholderText("Search shipment, carrier...");
    fireEvent.change(searchInput, { target: { value: "SHP-1001" } });

    expect(screen.getByText("SHP-1001")).toBeDefined();
    expect(screen.queryByText("SHP-1002")).toBeNull();
  });

  it("handles pagination", async () => {
    // Create enough mock data to span 2 pages (limit is 10)
    const manyEvaluations = Array.from({ length: 15 }, (_, i) => ({
      ...mockRiskEvaluations[0],
      evaluation_id: `eval-${i}`,
      shipment_id: `SHP-TEST-${i}`,
    }));

    (fetchRiskEvaluations as any).mockResolvedValue(manyEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);

    await waitFor(() => expect(screen.getByText("SHP-TEST-0")).toBeDefined());

    // Page 1 should show 0-9
    expect(screen.getByText("SHP-TEST-9")).toBeDefined();
    expect(screen.queryByText("SHP-TEST-10")).toBeNull();

    // Go to next page
    const paginationButtons = screen.getAllByRole("button");
    const nextBtn = paginationButtons.find(btn => btn.querySelector("svg.lucide-chevron-right"));

    if (nextBtn) {
        fireEvent.click(nextBtn);
    } else {
        throw new Error("Next button not found");
    }

    // Page 2 should show 10-14
    await waitFor(() => expect(screen.getByText("SHP-TEST-10")).toBeDefined());
    expect(screen.queryByText("SHP-TEST-0")).toBeNull();
  });

  it("displays error message when API fails", async () => {
    (fetchRiskEvaluations as any).mockRejectedValue(new Error("API Error"));
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load risk evaluations.")).toBeDefined();
    });
  });

  it("renders model metrics happy path", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(mockMetrics);
    render(<RiskConsolePage />);

    await waitFor(() => expect(screen.getByText("Model Health (Maggie)")).toBeDefined());

    expect(screen.getByText("Critical Incident Recall")).toBeDefined();
    expect(screen.getByText("72.3%")).toBeDefined();
    expect(screen.getByText("Ops Workload")).toBeDefined();
    expect(screen.getByText("14.0%")).toBeDefined();
    expect(screen.getByText("742")).toBeDefined(); // Eval count
  });

  it("renders model metrics failure badge", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue({
      ...mockMetrics,
      has_failures: true,
      fail_messages: ["Calibration drift detected"],
    });
    render(<RiskConsolePage />);

    await waitFor(() => expect(screen.getByText("Failures Detected")).toBeDefined());
  });

  it("renders model metrics warning badge", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue({
      ...mockMetrics,
      has_warnings: true,
      warning_messages: ["Slight precision drop"],
    });
    render(<RiskConsolePage />);

    await waitFor(() => expect(screen.getByText("Warnings Present")).toBeDefined());
  });

  it("handles metrics error gracefully", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockRejectedValue(new Error("Metrics Error"));
    render(<RiskConsolePage />);

    await waitFor(() => expect(screen.getByText("Model metrics unavailable")).toBeDefined());
    // Table should still load
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());
  });

  it("handles missing metrics (null)", async () => {
    (fetchRiskEvaluations as any).mockResolvedValue(mockRiskEvaluations);
    (fetchRiskMetricsLatest as any).mockResolvedValue(null);
    render(<RiskConsolePage />);

    await waitFor(() => expect(screen.getByText("Awaiting first metrics run")).toBeDefined());
    // Table should still load
    await waitFor(() => expect(screen.getByText("SHP-1001")).toBeDefined());
  });
});
