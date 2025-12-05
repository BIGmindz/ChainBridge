import type { IntelShipmentPoint } from "@/types/intel";

export type CorridorIntelSummary = {
  corridorId: string;
  corridorLabel: string;
  total_valueUsd: number;
  at_risk_valueUsd: number;
  avg_riskScore: number;
  max_riskScore: number;
  avg_stakeApr: number | null;
  stakeCapacityUsd: number;
  opportunity_score: number;
};

type AggregatedRow = CorridorIntelSummary & {
  _count: number;
  _aprs: number[];
};

export function buildCorridorStats(
  shipments: IntelShipmentPoint[],
): CorridorIntelSummary[] {
  const rows = new Map<string, AggregatedRow>();

  for (const s of shipments) {
    const corridorId = s.corridorId || s.corridorLabel || "UNKNOWN";
    const key = corridorId;
    const label = s.corridorLabel || s.corridorId || "Unknown Corridor";
    const riskScore = s.riskScore ?? 0;

    if (!rows.has(key)) {
      rows.set(key, {
        corridorId: corridorId,
        corridorLabel: label,
        total_valueUsd: 0,
        at_risk_valueUsd: 0,
        avg_riskScore: 0,
        max_riskScore: 0,
        avg_stakeApr: null,
        stakeCapacityUsd: 0,
        opportunity_score: 0,
        _count: 0,
        _aprs: [],
      });
    }

    const row = rows.get(key)!;
    const value = s.valueUsd ?? 0;
    row.total_valueUsd += value;
    row.avg_riskScore += riskScore;
    row.max_riskScore = Math.max(row.max_riskScore, riskScore);

    const isAtRisk =
      riskScore >= 70 ||
      s.status === "AT_RISK" ||
      s.riskCategory === "HIGH" ||
      s.riskCategory === "CRITICAL";

    if (isAtRisk) {
      row.at_risk_valueUsd += value;
    }

    if (typeof s.stakeCapacityUsd === "number") {
      row.stakeCapacityUsd += s.stakeCapacityUsd;
    }

    if (typeof s.stakeApr === "number") {
      row._aprs.push(s.stakeApr);
    }

    row._count += 1;
  }

  const result: CorridorIntelSummary[] = [];
  for (const [, aggregated] of rows) {
    const { _count, _aprs, ...rest } = aggregated;
    const avgRisk = _count > 0 ? rest.avg_riskScore / _count : 0;
    rest.avg_riskScore = avgRisk;

    if (_aprs.length > 0) {
      rest.avg_stakeApr = _aprs.reduce((a, b) => a + b, 0) / _aprs.length;
    }

    const aprFactor = (rest.avg_stakeApr ?? 0) / 10;
    const riskFactor = avgRisk / 100;
    const capacityFactor = Math.log10(rest.stakeCapacityUsd + 10);

    rest.opportunity_score = aprFactor * (1 + riskFactor) * capacityFactor;

    result.push({ ...rest });
  }

  result.sort((a, b) => b.opportunity_score - a.opportunity_score);
  return result;
}

/**
 * Format USD value with K/M/B suffix for compact display.
 */
export function formatUsd(value: number): string {
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

/**
 * Format percentage with one decimal place.
 */
export function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}
