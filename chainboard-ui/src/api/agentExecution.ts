/**
 * ChainBridge Agent Execution API Client
 * PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
 * 
 * GET-ONLY API client for agent execution visibility.
 * 
 * INV-AGENT-004: OC is read-only; no agent control actions.
 * This client ONLY exposes GET methods.
 */

import type {
  AgentExecutionView,
  AgentListResponse,
  AgentTimelineEvent,
  PACExecutionView,
  PACListResponse,
} from '../types/agentExecution';

const API_BASE = '/api/oc/agents';

/**
 * Fetch with error handling
 */
async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

/**
 * Get all currently active agents across all PACs
 */
export async function fetchActiveAgents(
  limit: number = 100,
  offset: number = 0
): Promise<AgentListResponse> {
  return fetchJson<AgentListResponse>(
    `${API_BASE}/active?limit=${limit}&offset=${offset}`
  );
}

/**
 * Get comprehensive execution view for a PAC
 */
export async function fetchPACExecution(pacId: string): Promise<PACExecutionView> {
  return fetchJson<PACExecutionView>(`${API_BASE}/pac/${encodeURIComponent(pacId)}`);
}

/**
 * Get all agents for a PAC
 */
export async function fetchPACAgents(
  pacId: string,
  limit: number = 100,
  offset: number = 0
): Promise<AgentListResponse> {
  return fetchJson<AgentListResponse>(
    `${API_BASE}/pac/${encodeURIComponent(pacId)}/agents?limit=${limit}&offset=${offset}`
  );
}

/**
 * Get specific agent execution view
 */
export async function fetchAgentView(
  pacId: string,
  agentGid: string
): Promise<AgentExecutionView> {
  return fetchJson<AgentExecutionView>(
    `${API_BASE}/pac/${encodeURIComponent(pacId)}/agent/${encodeURIComponent(agentGid)}`
  );
}

/**
 * Get execution timeline for a PAC
 */
export async function fetchPACTimeline(
  pacId: string,
  agentGid?: string
): Promise<AgentTimelineEvent[]> {
  let url = `${API_BASE}/pac/${encodeURIComponent(pacId)}/timeline`;
  if (agentGid) {
    url += `?agent_gid=${encodeURIComponent(agentGid)}`;
  }
  return fetchJson<AgentTimelineEvent[]>(url);
}

/**
 * Get list of all PACs with execution status
 */
export async function fetchPACList(): Promise<PACListResponse> {
  return fetchJson<PACListResponse>(`${API_BASE}/pacs`);
}

/**
 * Health check for agent OC API
 */
export async function checkAgentOCHealth(): Promise<{
  status: string;
  read_only: boolean;
  api_version: string;
  timestamp: string;
}> {
  return fetchJson(`${API_BASE}/health`);
}
