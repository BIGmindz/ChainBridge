/**
 * ProofPackDetailPage
 *
 * Read-only page for displaying ProofPack detail by artifact ID.
 * Navigation is explicit, user-initiated, and neutral.
 * Renders page shell regardless of data presence.
 * No validation. No interpretation. Evidence only.
 *
 * @module pages/ProofPackDetailPage
 */

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchProofPackByArtifactId, type ProofPackResponse } from "../api/proofpack";
import { ProofPackViewer } from "../components/proof/ProofPackViewer";

type LoadState = "idle" | "loading" | "success" | "error";

export default function ProofPackDetailPage(): JSX.Element {
  const { artifactId } = useParams<{ artifactId: string }>();
  const [proofpackResponse, setProofpackResponse] = useState<ProofPackResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadProofPack = useCallback(async () => {
    if (!artifactId) {
      setErrorMessage("No artifact ID provided");
      setLoadState("error");
      return;
    }

    setLoadState("loading");
    setErrorMessage(null);

    try {
      const response = await fetchProofPackByArtifactId(artifactId);
      setProofpackResponse(response);
      setLoadState("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error occurred";
      setErrorMessage(message);
      setLoadState("error");
    }
  }, [artifactId]);

  useEffect(() => {
    loadProofPack();
  }, [loadProofPack]);

  return (
    <div className="space-y-6 px-6 py-8">
      {/* Header */}
      <header className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-500">
          OCC ProofPack Detail
        </p>
        <h1 className="text-4xl font-semibold text-slate-900">ProofPack Viewer</h1>
        <p className="max-w-3xl text-base text-slate-600">
          Read-only display of ProofPack data as returned by backend.
        </p>
      </header>

      {/* Artifact ID Display */}
      <div className="font-mono text-sm text-slate-700">
        <span className="font-semibold">artifact_id:</span>{" "}
        <span className="text-slate-900">{artifactId ?? "null"}</span>
      </div>

      {/* Navigation & Actions */}
      <div className="flex items-center gap-4">
        <Link
          to="/proof-artifacts"
          className="border border-slate-400 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
        >
          ← Back to Artifacts
        </Link>
        <button
          type="button"
          onClick={loadProofPack}
          disabled={loadState === "loading"}
          className="border border-slate-400 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loadState === "loading" ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Loading State */}
      {loadState === "loading" && (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-600">
          Loading ProofPack...
        </div>
      )}

      {/* Data Not Found State */}
      {loadState === "error" && errorMessage && (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-600">
          Proof artifact not found
        </div>
      )}

      {/* No Artifact ID State */}
      {!artifactId && loadState !== "loading" && (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-600">
          No artifact ID provided in URL
        </div>
      )}

      {/* ProofPack Content */}
      {loadState === "success" && proofpackResponse && (
        <ProofPackViewer response={proofpackResponse} />
      )}
    </div>
  );
}
