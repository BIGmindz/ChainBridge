import type { RiskLevel } from "@/types/chainbridge";

export type IntelShipmentPoint = {
  id: string;
  lat: number;
  lon: number;
  corridorId?: string;
  corridorLabel?: string;
  laneLabel?: string;
  valueUsd: number;
  riskScore: number;
  riskCategory?: RiskLevel;
  status?: "ON_TIME" | "DELAYED" | "AT_RISK";
  stakeApr?: number;
  stakeCapacityUsd?: number;
};
