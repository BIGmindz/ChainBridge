/**
 * ProofPackViewer Component
 *
 * Read-only display of ProofPack data.
 * Renders all canonical sections: Event, Decision, Action, Proof metadata.
 * Field names and values match backend exactly. No interpretation.
 *
 * @module components/proof/ProofPackViewer
 */

import type {
  ArtifactSummary,
  AuditEventSummary,
  IntegrityManifest,
  ProofPack,
  ProofPackResponse,
} from "../../api/proofpack";

interface ProofPackViewerProps {
  response: ProofPackResponse;
}

/**
 * Renders a single field row in the table format.
 */
function FieldRow({
  label,
  value,
  isLast = false,
}: {
  label: string;
  value: React.ReactNode;
  isLast?: boolean;
}): JSX.Element {
  return (
    <tr className={isLast ? "" : "border-b border-slate-200"}>
      <td className="py-2 pr-4 align-top font-semibold text-slate-600">{label}</td>
      <td className="py-2 text-slate-900">{value}</td>
    </tr>
  );
}

/**
 * Renders the Artifact section of the ProofPack.
 * Displays artifact metadata exactly as returned by backend.
 */
function ArtifactSection({ artifact }: { artifact: ArtifactSummary }): JSX.Element {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
        Artifact
      </h3>
      <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
        <table className="w-full border-collapse">
          <tbody>
            <FieldRow label="id" value={artifact.id} />
            <FieldRow label="name" value={artifact.name} />
            <FieldRow label="artifact_type" value={artifact.artifact_type} />
            <FieldRow label="status" value={artifact.status} />
            <FieldRow label="description" value={artifact.description ?? "null"} />
            <FieldRow label="owner" value={artifact.owner ?? "null"} />
            <FieldRow
              label="tags"
              value={artifact.tags.length > 0 ? JSON.stringify(artifact.tags) : "[]"}
            />
            <FieldRow label="created_at" value={artifact.created_at} />
            <FieldRow label="updated_at" value={artifact.updated_at} isLast />
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * Renders a single Event from the ProofPack.
 * Displays event details exactly as returned by backend.
 */
function EventItem({ event, index }: { event: AuditEventSummary; index: number }): JSX.Element {
  return (
    <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
      <div className="mb-2 text-xs font-semibold text-slate-500">Event [{index}]</div>
      <table className="w-full border-collapse">
        <tbody>
          <FieldRow label="id" value={event.id} />
          <FieldRow label="event_type" value={event.event_type} />
          <FieldRow label="actor" value={event.actor ?? "null"} />
          <FieldRow label="timestamp" value={event.timestamp} />
          <FieldRow
            label="details"
            value={
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all">
                {JSON.stringify(event.details, null, 2)}
              </pre>
            }
            isLast
          />
        </tbody>
      </table>
    </div>
  );
}

/**
 * Renders the Events section of the ProofPack.
 * Lists all audit events in deterministic order.
 */
function EventsSection({ events }: { events: AuditEventSummary[] }): JSX.Element {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
        Events
      </h3>
      <div className="text-xs text-slate-600">
        <span className="font-mono">event_count:</span> {events.length}
      </div>
      {events.length === 0 ? (
        <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm text-slate-600">
          No events recorded.
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((event, index) => (
            <EventItem key={event.id} event={event} index={index} />
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Renders the Integrity section of the ProofPack.
 * Displays cryptographic hashes and signature metadata.
 */
function IntegritySection({ integrity }: { integrity: IntegrityManifest }): JSX.Element {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
        Integrity (Proof Metadata)
      </h3>
      <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
        <table className="w-full border-collapse">
          <tbody>
            <FieldRow label="algorithm" value={integrity.algorithm} />
            <FieldRow
              label="artifact_hash"
              value={
                <span className="break-all">{integrity.artifact_hash}</span>
              }
            />
            <FieldRow
              label="events_hash"
              value={
                <span className="break-all">{integrity.events_hash}</span>
              }
            />
            <FieldRow
              label="manifest_hash"
              value={
                <span className="break-all">{integrity.manifest_hash}</span>
              }
            />
            <FieldRow label="generated_at" value={integrity.generated_at} />
            <FieldRow label="signature" value={integrity.signature ?? "null"} />
            <FieldRow label="public_key" value={integrity.public_key ?? "null"} />
            <FieldRow label="key_id" value={integrity.key_id ?? "null"} />
            <FieldRow label="signature_algorithm" value={integrity.signature_algorithm ?? "null"} />
            <FieldRow label="signed_at" value={integrity.signed_at ?? "null"} isLast />
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * Renders the ProofPack metadata section.
 * Displays generation and status information.
 */
function ProofPackMetadataSection({ proofpack }: { proofpack: ProofPack }): JSX.Element {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
        ProofPack
      </h3>
      <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
        <table className="w-full border-collapse">
          <tbody>
            <FieldRow label="id" value={proofpack.id} />
            <FieldRow label="artifact_id" value={proofpack.artifact_id} />
            <FieldRow label="status" value={proofpack.status} />
            <FieldRow label="event_count" value={String(proofpack.event_count)} />
            <FieldRow label="generated_at" value={proofpack.generated_at} />
            <FieldRow label="generated_by" value={proofpack.generated_by} />
            <FieldRow label="notes" value={proofpack.notes ?? "null"} />
            <FieldRow label="schema_version" value={proofpack.schema_version} isLast />
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * Renders the Response metadata section.
 * Displays export formats and verification info.
 */
function ResponseMetadataSection({ response }: { response: ProofPackResponse }): JSX.Element {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
        Response Metadata
      </h3>
      <div className="border border-slate-300 bg-slate-50 p-4 font-mono text-sm">
        <table className="w-full border-collapse">
          <tbody>
            <FieldRow
              label="export_formats"
              value={JSON.stringify(response.export_formats)}
            />
            <FieldRow
              label="verification_url"
              value={response.verification_url ?? "null"}
            />
            <FieldRow label="is_signed" value={String(response.is_signed)} isLast />
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * ProofPackViewer - Full read-only viewer for ProofPack data.
 *
 * Renders all canonical sections:
 * - ProofPack metadata
 * - Artifact (context/subject)
 * - Events (what happened, decisions, actions)
 * - Integrity (proof/cryptographic verification)
 * - Response metadata
 *
 * All field names and values match backend exactly.
 * No interpretation, summarization, or derived data.
 */
export function ProofPackViewer({ response }: ProofPackViewerProps): JSX.Element {
  const { proofpack } = response;

  return (
    <div className="space-y-6">
      {/* ProofPack Metadata */}
      <ProofPackMetadataSection proofpack={proofpack} />

      {/* Artifact Section */}
      <ArtifactSection artifact={proofpack.artifact} />

      {/* Events Section */}
      <EventsSection events={proofpack.events} />

      {/* Integrity Section */}
      <IntegritySection integrity={proofpack.integrity} />

      {/* Response Metadata */}
      <ResponseMetadataSection response={response} />
    </div>
  );
}
