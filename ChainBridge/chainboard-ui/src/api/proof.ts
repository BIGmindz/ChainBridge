/**
 * Proof Artifacts API Client
 *
 * Handles fetching proof artifacts from the OCC backend.
 * Read-only operations only.
 *
 * @module api/proof
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
 */
export interface ProofPackResponse {
  proofpack: ProofPack;
  export_formats: string[];
  verification_url: string | null;
  is_signed: boolean;
}

/**
 * OCC Artifact as returned by list endpoint.
 * Field names match backend exactly.
 */
export interface OCCArtifact {
  id: string;
  name: string;
  artifact_type: string;
  status: string;
  description: string | null;
  payload: Record<string, unknown>;
  tags: string[];
  owner: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Artifact list response from OCC API.
 */
export interface ArtifactListResponse {
  items: OCCArtifact[];
  count: number;
  limit: number | null;
  offset: number;
}

/**
 * Fetch list of OCC artifacts.
 * GET /occ/artifacts
 */
export async function fetchArtifacts(params?: {
  artifact_type?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ArtifactListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.artifact_type) queryParams.set("artifact_type", params.artifact_type);
  if (params?.status) queryParams.set("status", params.status);
  if (params?.limit) queryParams.set("limit", String(params.limit));
  if (params?.offset) queryParams.set("offset", String(params.offset));

  const query = queryParams.toString();
  const path = `/occ/artifacts${query ? `?${query}` : ""}`;

  return httpGet<ArtifactListResponse>(path);
}

/**
 * Fetch a single artifact by ID.
 * GET /occ/artifacts/{artifact_id}
 */
export async function fetchArtifact(artifactId: string): Promise<OCCArtifact> {
  return httpGet<OCCArtifact>(`/occ/artifacts/${artifactId}`);
}

/**
 * Fetch ProofPack for a specific artifact.
 * GET /occ/artifacts/{artifact_id}/proofpack
 */
export async function fetchArtifactProofPack(artifactId: string): Promise<ProofPackResponse> {
  return httpGet<ProofPackResponse>(`/occ/artifacts/${artifactId}/proofpack`);
}
