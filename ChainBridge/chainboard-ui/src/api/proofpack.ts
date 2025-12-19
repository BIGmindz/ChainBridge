/**
 * ProofPack API Client
 *
 * Dedicated client for fetching ProofPack data by artifact ID.
 * Read-only operations only. Field names match backend exactly.
 *
 * @module api/proofpack
 */

import { httpGet } from "../services/apiClient";

/**
 * Audit event summary as returned by OCC API.
 * Field names match backend exactly.
 */
export interface AuditEventSummary {
  id: string;
  event_type: string;
  actor: string | null;
  timestamp: string;
  details: Record<string, unknown>;
}

/**
 * Artifact summary as returned by OCC API.
 * Field names match backend exactly.
 */
export interface ArtifactSummary {
  id: string;
  name: string;
  artifact_type: string;
  status: string;
  description: string | null;
  owner: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

/**
 * Integrity manifest with cryptographic hashes.
 * Field names match backend exactly.
 */
export interface IntegrityManifest {
  algorithm: string;
  artifact_hash: string;
  events_hash: string;
  manifest_hash: string;
  generated_at: string;
  signature: string | null;
  public_key: string | null;
  key_id: string | null;
  signature_algorithm: string | null;
  signed_at: string | null;
}

/**
 * Full ProofPack as returned by OCC API.
 * Field names match backend exactly.
 */
export interface ProofPack {
  id: string;
  artifact_id: string;
  artifact: ArtifactSummary;
  events: AuditEventSummary[];
  event_count: number;
  integrity: IntegrityManifest;
  status: string;
  generated_at: string;
  generated_by: string;
  notes: string | null;
  schema_version: string;
}

/**
 * API response wrapper for ProofPack.
 * Field names match backend exactly.
 */
export interface ProofPackResponse {
  proofpack: ProofPack;
  export_formats: string[];
  verification_url: string | null;
  is_signed: boolean;
}

/**
 * Fetch ProofPack for a specific artifact.
 * GET /occ/artifacts/{artifact_id}/proofpack
 *
 * @param artifactId - The artifact ID to fetch ProofPack for
 * @returns ProofPackResponse containing the full ProofPack data
 */
export async function fetchProofPackByArtifactId(artifactId: string): Promise<ProofPackResponse> {
  return httpGet<ProofPackResponse>(`/occ/artifacts/${artifactId}/proofpack`);
}
