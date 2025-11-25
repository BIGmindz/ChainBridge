/**
 * ProofPack Types
 *
 * Structured evidence bundles for settlement milestones.
 * Provides on-chain traceability for tokenized freight payments.
 */

/**
 * ProofPack - Comprehensive evidence bundle for a payment milestone
 *
 * Mirrors backend schema from ChainIQ/ChainPay integration.
 * Contains documents, IoT signals, risk assessments, and audit trail.
 */
export interface ProofPack {
  milestone_id: string;
  shipment_reference: string;
  corridor: string;
  customer_name: string;
  amount: number;
  currency: string;
  state: string;
  freight_token_id?: number | null;
  last_updated: string; // ISO timestamp
  documents: Array<Record<string, unknown>>;
  iot_signals: Array<Record<string, unknown>>;
  risk_assessment: Record<string, unknown>;
  audit_trail: Array<Record<string, unknown>>;
}

/**
 * ProofPack API response envelope
 */
export interface ProofPackEnvelope {
  proofpack: ProofPack;
  generatedAt: string;
}
