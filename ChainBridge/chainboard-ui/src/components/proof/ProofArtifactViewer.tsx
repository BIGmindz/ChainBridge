/**
 * ProofArtifactViewer Component
 *
 * Read-only display of proof artifacts.
 * Renders raw backend data without interpretation.
 * Labels match backend field names exactly.
 *
 * @module components/proof/ProofArtifactViewer
 */

import { Link } from "react-router-dom";

import type { OCCArtifact } from "../../api/proof";

interface ProofArtifactViewerProps {
  artifact: OCCArtifact;
}

/**
 * Renders a single proof artifact as raw JSON fields.
 * No computed interpretations. No colors implying judgment.
 */
export function ProofArtifactViewer({ artifact }: ProofArtifactViewerProps): JSX.Element {
  return (
    <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
      {/* View ProofPack Link */}
      <div className="mb-4">
        <Link
          to={`/proof-artifacts/${artifact.id}`}
          className="border border-slate-400 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
        >
          View ProofPack →
        </Link>
      </div>
      <table className="w-full border-collapse">
        <tbody>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">id</td>
            <td className="py-2 text-slate-900">{artifact.id}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">name</td>
            <td className="py-2 text-slate-900">{artifact.name}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">artifact_type</td>
            <td className="py-2 text-slate-900">{artifact.artifact_type}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">status</td>
            <td className="py-2 text-slate-900">{artifact.status}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">description</td>
            <td className="py-2 text-slate-900">{artifact.description ?? "null"}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">owner</td>
            <td className="py-2 text-slate-900">{artifact.owner ?? "null"}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">tags</td>
            <td className="py-2 text-slate-900">
              {artifact.tags.length > 0 ? JSON.stringify(artifact.tags) : "[]"}
            </td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">created_at</td>
            <td className="py-2 text-slate-900">{artifact.created_at}</td>
          </tr>
          <tr className="border-b border-slate-200">
            <td className="py-2 pr-4 font-semibold text-slate-600">updated_at</td>
            <td className="py-2 text-slate-900">{artifact.updated_at}</td>
          </tr>
          <tr>
            <td className="py-2 pr-4 align-top font-semibold text-slate-600">payload</td>
            <td className="py-2 text-slate-900">
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all">
                {JSON.stringify(artifact.payload, null, 2)}
              </pre>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
