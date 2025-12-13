/**
 * ChainIQ Lab Panel Component
 *
 * Interactive debugging panel for ChainIQ ML risk and anomaly scoring.
 * Allows operators to test ML endpoints with sample or custom payloads.
 *
 * UX designed for neurodivergent users (ADHD/autism-friendly):
 * - Clear step-by-step workflow
 * - Obvious calls to action
 * - Friendly error messages
 * - No automatic behavior or hidden state
 *
 * @module features/chainiq/IqLabPanel
 */

import { useState, useEffect } from "react";

import type {
  RiskScoreResult,
  AnomalyScoreResult,
  ShipmentFeaturesV0Like,
  IqMetrics,
} from "../../api/chainiq";
import {
  fetchRiskScore,
  fetchAnomalyScore,
  fetchIqMetrics,
} from "../../api/chainiq";
import { Card, CardHeader, CardContent } from "../../components/ui/Card";

import { SAMPLE_PAYLOADS } from "./samplePayloads";

type ScoreType = "risk" | "anomaly";

interface ScoringResult {
  type: ScoreType;
  data: RiskScoreResult | AnomalyScoreResult;
}

export default function IqLabPanel(): JSX.Element {
  // Payload management
  const [payloadText, setPayloadText] = useState<string>(
    JSON.stringify(SAMPLE_PAYLOADS[0].payload, null, 2)
  );
  const [parseError, setParseError] = useState<string | null>(null);

  // Scoring state
  const [isLoadingRisk, setIsLoadingRisk] = useState(false);
  const [isLoadingAnomaly, setIsLoadingAnomaly] = useState(false);
  const [scoringError, setScoringError] = useState<string | null>(null);
  const [result, setResult] = useState<ScoringResult | null>(null);

  // Metrics state
  const [metrics, setMetrics] = useState<IqMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  /**
   * Load a sample payload into the editor
   */
  const handleLoadSample = (index: number) => {
    const sample = SAMPLE_PAYLOADS[index];
    setPayloadText(JSON.stringify(sample.payload, null, 2));
    setParseError(null);
    setScoringError(null);
    setResult(null);
  };

  /**
   * Load IQ metrics from observability endpoint
   */
  const loadMetrics = async () => {
    try {
      setMetricsLoading(true);
      setMetricsError(null);
      const data = await fetchIqMetrics();
      setMetrics(data);
    } catch (error) {
      console.error("Failed to load IQ metrics", error);
      setMetricsError("Could not load metrics");
    } finally {
      setMetricsLoading(false);
    }
  };

  // Load metrics on mount
  useEffect(() => {
    void loadMetrics();
  }, []);

  /**
   * Parse the current payload JSON
   */
  const parsePayload = (): ShipmentFeaturesV0Like | null => {
    try {
      const parsed = JSON.parse(payloadText);
      setParseError(null);
      return parsed as ShipmentFeaturesV0Like;
    } catch (error) {
      const errorMsg =
        error instanceof Error ? error.message : "Invalid JSON syntax";
      setParseError(
        `Unable to parse JSON: ${errorMsg}. Please fix the syntax or load a sample payload.`
      );
      return null;
    }
  };

  /**
   * Run risk scoring
   */
  const handleRunRiskScore = async () => {
    const payload = parsePayload();
    if (!payload) return;

    setIsLoadingRisk(true);
    setScoringError(null);
    setResult(null);

    try {
      const riskResult = await fetchRiskScore(payload);
      setResult({ type: "risk", data: riskResult });
      // Refresh metrics after successful scoring
      await loadMetrics();
    } catch (error) {
      const errorMsg =
        error instanceof Error
          ? error.message
          : "Failed to fetch risk score. Please check your connection and try again.";
      setScoringError(errorMsg);
    } finally {
      setIsLoadingRisk(false);
    }
  };

  /**
   * Run anomaly scoring
   */
  const handleRunAnomalyScore = async () => {
    const payload = parsePayload();
    if (!payload) return;

    setIsLoadingAnomaly(true);
    setScoringError(null);
    setResult(null);

    try {
      const anomalyResult = await fetchAnomalyScore(payload);
      setResult({ type: "anomaly", data: anomalyResult });
      // Refresh metrics after successful scoring
      await loadMetrics();
    } catch (error) {
      const errorMsg =
        error instanceof Error
          ? error.message
          : "Failed to fetch anomaly score. Please check your connection and try again.";
      setScoringError(errorMsg);
    } finally {
      setIsLoadingAnomaly(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-white">ChainIQ Lab</h1>
        <p className="text-slate-400 text-lg">
          Test and debug ChainIQ ML risk and anomaly scoring endpoints.
        </p>
      </div>

      {/* Main Layout: Side-by-Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Input Area */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold text-white">
              Step 1: Choose or Edit Payload
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Select a sample shipment or paste your own JSON feature vector.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Sample Payload Buttons */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-300">
                Quick Load Sample:
              </label>
              <div className="flex flex-col gap-2">
                {SAMPLE_PAYLOADS.map((sample, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleLoadSample(idx)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors border border-slate-700"
                  >
                    {sample.label}
                  </button>
                ))}
              </div>
            </div>

            {/* JSON Editor */}
            <div className="space-y-2">
              <label
                htmlFor="payload-editor"
                className="block text-sm font-medium text-slate-300"
              >
                Shipment Feature Vector (JSON):
              </label>
              <textarea
                id="payload-editor"
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                className="w-full h-96 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                spellCheck={false}
              />
            </div>

            {/* Parse Error */}
            {parseError && (
              <div className="p-3 bg-red-900/20 border border-red-700 rounded-lg">
                <p className="text-sm text-red-400">{parseError}</p>
              </div>
            )}

            {/* Step 2: Run Scoring */}
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-slate-300">
                Step 2: Run Scoring
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={handleRunRiskScore}
                  disabled={isLoadingRisk || isLoadingAnomaly}
                  className="flex-1 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
                >
                  {isLoadingRisk ? "Running..." : "Run Risk Score"}
                </button>
                <button
                  onClick={handleRunAnomalyScore}
                  disabled={isLoadingRisk || isLoadingAnomaly}
                  className="flex-1 px-4 py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-colors"
                >
                  {isLoadingAnomaly ? "Running..." : "Run Anomaly Score"}
                </button>
              </div>
            </div>

            {/* IQ Metrics Ribbon */}
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-semibold tracking-wide text-slate-200 text-xs">
                  IQ Metrics
                </span>
                {metricsLoading && (
                  <span className="text-slate-400 text-xs">Refreshing…</span>
                )}
                {metricsError && (
                  <span className="text-red-400 text-xs">{metricsError}</span>
                )}
              </div>
              <div className="flex flex-wrap gap-4 text-slate-300">
                <div className="flex flex-col">
                  <span className="text-[0.65rem] uppercase tracking-wide text-slate-400">
                    Risk calls
                  </span>
                  <span className="text-sm font-semibold">
                    {metrics?.risk_calls_total ?? "—"}
                  </span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[0.65rem] uppercase tracking-wide text-slate-400">
                    Anomaly calls
                  </span>
                  <span className="text-sm font-semibold">
                    {metrics?.anomaly_calls_total ?? "—"}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right: Results Area */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold text-white">
              Step 3: Review Results
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              ChainIQ ML scoring results and explanations.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Scoring Error */}
            {scoringError && (
              <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg">
                <h3 className="text-sm font-semibold text-red-400 mb-1">
                  Scoring Failed
                </h3>
                <p className="text-sm text-red-300">{scoringError}</p>
              </div>
            )}

            {/* No Results Yet */}
            {!result && !scoringError && (
              <div className="p-8 text-center text-slate-500">
                <p className="text-lg">No results yet.</p>
                <p className="text-sm mt-2">
                  Run risk or anomaly scoring to see results here.
                </p>
              </div>
            )}

            {/* Results Display */}
            {result && (
              <div className="space-y-4">
                {/* Score Display */}
                <div className="p-6 bg-slate-900/50 rounded-lg border border-slate-700">
                  <div className="flex items-baseline justify-between mb-2">
                    <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide">
                      {result.type === "risk" ? "Risk Score" : "Anomaly Score"}
                    </h3>
                    <span className="text-xs text-slate-500">
                      {result.data.model_version}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-5xl font-bold text-white">
                      {result.data.score.toFixed(2)}
                    </span>
                    <span className="text-slate-400 text-lg">/ 1.00</span>
                  </div>
                  {/* Visual Progress Bar */}
                  <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        result.data.score < 0.33
                          ? "bg-green-500"
                          : result.data.score < 0.67
                          ? "bg-yellow-500"
                          : "bg-red-500"
                      }`}
                      // Dynamic width based on score - inline style required for dynamic value
                      style={{ width: `${result.data.score * 100}%` }}
                    />
                  </div>
                </div>

                {/* Explanation */}
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-slate-300">
                    Explanation
                  </h3>
                  {result.data.explanation.length === 0 && (
                    <p className="text-sm text-slate-500">
                      No specific features contributed to this score.
                    </p>
                  )}
                  {result.data.explanation.map((contrib, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-900/50 rounded-lg border border-slate-700"
                    >
                      <div className="flex items-start gap-2">
                        <span className="inline-block px-2 py-1 bg-indigo-900/50 text-indigo-300 rounded text-xs font-mono">
                          {contrib.feature}
                        </span>
                      </div>
                      <p className="text-sm text-slate-300 mt-2">
                        {contrib.reason}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
