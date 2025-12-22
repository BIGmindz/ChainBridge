/**
 * ProofArtifactsPage
 *
 * Minimal read-only page for displaying proof artifacts.
 * Fetches and renders artifacts from OCC backend.
 * No mutations. No interpretations. Evidence only.
 *
 * @module pages/ProofArtifactsPage
 */

import { useCallback, useEffect, useState } from "react";

import { fetchArtifacts, type ArtifactListResponse, type OCCArtifact } from "../api/proof";
import { ProofArtifactViewer } from "../components/proof/ProofArtifactViewer";

type LoadState = "idle" | "loading" | "success" | "error";

export default function ProofArtifactsPage(): JSX.Element {
  const [artifacts, setArtifacts] = useState<OCCArtifact[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadArtifacts = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);

    try {
      const response: ArtifactListResponse = await fetchArtifacts();
      setArtifacts(response.items);
      setLoadState("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error occurred";
      setErrorMessage(message);
      setLoadState("error");
    }
  }, []);

  useEffect(() => {
    loadArtifacts();
  }, [loadArtifacts]);

  return (
    <div className="space-y-6 px-6 py-8">
      {/* Header */}
      <header className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-500">
          OCC Proof Artifacts
        </p>
        <h1 className="text-4xl font-semibold text-slate-900">Proof Artifact Viewer</h1>
        <p className="max-w-3xl text-base text-slate-600">
          Read-only display of proof artifacts as returned by backend.
        </p>
      </header>

      {/* Refresh Button */}
      <div>
        <button
          type="button"
          onClick={loadArtifacts}
          disabled={loadState === "loading"}
          className="border border-slate-400 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loadState === "loading" ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Loading State */}
      {loadState === "loading" && (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-600">
          Loading artifacts...
        </div>
      )}

      {/* Error State */}
      {loadState === "error" && errorMessage && (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
          <span className="font-semibold text-slate-700">Error:</span>{" "}
          <span className="text-slate-900">{errorMessage}</span>
        </div>
      )}

      {/* Empty State */}
      {loadState === "success" && artifacts.length === 0 && (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-600">
          No artifacts found.
        </div>
      )}

      {/* Artifacts List */}
      {loadState === "success" && artifacts.length > 0 && (
        <div className="space-y-4">
          <div className="text-sm text-slate-600">
            <span className="font-mono">count:</span> {artifacts.length}
          </div>
          {artifacts.map((artifact) => (
            <ProofArtifactViewer key={artifact.id} artifact={artifact} />
          ))}
        </div>
      )}
    </div>
  );
}
