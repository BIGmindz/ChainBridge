/**
 * Governance Decisions Mock Data Provider
 *
 * NOTE: PROPOSED API shape. Currently backed by local mock data.
 * TODO: Wire to real backend endpoint when CODI exposes it.
 *
 * Expected backend endpoint: GET /api/governance/decisions/recent?limit=50&status=FREEZE
 */

import type { GovernanceDecision, GovernanceDecisionApiResponse, GovernanceDecisionFilter } from '../types/governance';

// Mock data generator
const generateMockDecision = (index: number): GovernanceDecision => {
  const statuses: GovernanceDecision['status'][] = ['APPROVE', 'APPROVE', 'APPROVE', 'FREEZE', 'REJECT'];
  const decisionTypes = ['settlement_precheck', 'payment_authorization', 'risk_override'];
  const corridors = ['US-MX', 'CN-US', 'EU-UK', 'US-CA', 'MX-GT'];
  const currencies = ['USD', 'EUR', 'GBP', 'CAD', 'MXN'];
  const reasonCodes = [
    ['L3_SECURITY_THRESHOLD_EXCEEDED', 'HIGH_RISK_CORRIDOR'],
    ['GEOPOLITICAL_RISK_DETECTED', 'SANCTIONS_CHECK_REQUIRED'],
    ['COMPLIANCE_REVIEW_NEEDED', 'AML_FLAG_TRIGGERED'],
    ['CREDIT_LIMIT_EXCEEDED', 'COUNTERPARTY_RISK_HIGH'],
    ['OPERATIONAL_RISK_FLAG', 'ROUTE_ANOMALY_DETECTED']
  ];
  const policies = [
    ['GID-HGP-L1: Code = Cash', 'GID-HGP-L3: Security > Speed'],
    ['GID-HGP-L2: Trust = Truth', 'Risk Score >= 7.5 Threshold'],
    ['GID-HGP-L4: One Truth Many Views', 'Settlement Precheck Required'],
    ['AML Compliance Policy v2.1', 'Sanctions Screening Required'],
    ['Operational Risk Framework v1.3', 'Route Verification Protocol']
  ];

  const status = statuses[index % statuses.length];
  const decisionType = decisionTypes[index % decisionTypes.length];
  const corridor = corridors[index % corridors.length];
  const currency = currencies[index % currencies.length];
  const reasonCodeSet = reasonCodes[index % reasonCodes.length];
  const policySet = policies[index % policies.length];

  const baseDate = new Date('2025-12-01T08:00:00Z');
  const createdAt = new Date(baseDate.getTime() - (index * 1000 * 60 * 30)); // 30min intervals

  return {
    id: `gd-${String(index + 1).padStart(4, '0')}`,
    createdAt: createdAt.toISOString(),
    decisionType,
    status,
    shipmentId: Math.random() > 0.3 ? `SHP-2025-${String(Math.floor(Math.random() * 9999) + 1).padStart(4, '0')}` : undefined,
    payerId: `PAYER-${String(Math.floor(Math.random() * 999) + 1).padStart(3, '0')}`,
    payeeId: `PAYEE-${String(Math.floor(Math.random() * 999) + 1).padStart(3, '0')}`,
    amount: Math.floor(Math.random() * 100000) + 5000,
    currency,
    corridor,
    riskScore: status === 'FREEZE'
      ? Math.random() * 2 + 8  // 8.0-10.0 for FREEZE
      : status === 'REJECT'
        ? Math.random() * 1.5 + 8.5 // 8.5-10.0 for REJECT
        : Math.random() * 7 + 1, // 1.0-8.0 for APPROVE
    reasonCodes: reasonCodeSet,
    policiesApplied: policySet,
    economicJustification: status === 'FREEZE'
      ? `Risk score ${(Math.random() * 2 + 8).toFixed(1)} exceeds L3 threshold. Manual Guardian review required before settlement.`
      : status === 'REJECT'
        ? `Critical compliance violation detected. Settlement blocked pending investigation.`
        : `Settlement approved within risk parameters. Automated processing authorized.`,
    agentId: 'GID-Kernel',
    gid: 'GID-01',
    gidVersion: '1.0',
    raw: {
      processingTimeMs: Math.floor(Math.random() * 500) + 50,
      contextHash: `0x${Math.random().toString(16).substring(2, 18)}`,
      policyEngineVersion: '1.0.3',
      riskEngineVersion: '2.1.4'
    }
  };
};

// Generate mock dataset
const MOCK_DECISIONS: GovernanceDecision[] = Array.from({ length: 47 }, (_, i) => generateMockDecision(i));

/**
 * Mock API client for governance decisions
 * Simulates pagination, filtering, and search
 */
export const governanceDecisionsMock = {
  /**
   * Fetch governance decisions with filtering and pagination
   * NOTE: PROPOSED API - replace with real fetch when backend is ready
   */
  async fetchGovernanceDecisions(
    filters: GovernanceDecisionFilter = {},
    page = 1,
    limit = 20
  ): Promise<GovernanceDecisionApiResponse> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 200));

    let filtered = [...MOCK_DECISIONS];

    // Status filter
    if (filters.status && filters.status !== 'ALL') {
      filtered = filtered.filter(d => d.status === filters.status);
    }

    // Search filter (shipmentId, payer, payee)
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      filtered = filtered.filter(d =>
        d.shipmentId?.toLowerCase().includes(query) ||
        d.payerId.toLowerCase().includes(query) ||
        d.payeeId.toLowerCase().includes(query) ||
        d.id.toLowerCase().includes(query)
      );
    }

    // Decision type filter
    if (filters.decisionType && filters.decisionType !== 'ALL') {
      filtered = filtered.filter(d => d.decisionType === filters.decisionType);
    }

    // Sort by created date descending
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    // Pagination
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const paginatedResults = filtered.slice(startIndex, endIndex);

    return {
      decisions: paginatedResults,
      total: filtered.length,
      page,
      limit
    };
  }
};
