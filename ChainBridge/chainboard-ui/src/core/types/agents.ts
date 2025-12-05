/**
 * Agent Health Types
 *
 * Shared types for UI components consuming /api/agents/status.
 */

export interface AgentHealthResponse {
  total: number;
  valid: number;
  invalid: number;
  invalid_roles: string[];
}

export interface AgentHealthSummary {
  total: number;
  valid: number;
  invalid: number;
  invalidRoles: string[];
}
