export type CorridorId = "asia-us-west" | "eu-us-east" | "intra-us" | "other";

export interface CorridorClassification {
  id: CorridorId;
  label: string;
}

interface CorridorSubject {
  origin: string;
  destination: string;
}

const CORRIDOR_LABELS: Record<CorridorId, string> = {
  "asia-us-west": "Asia → US West",
  "eu-us-east": "EU → US East",
  "intra-us": "Intra-US",
  other: "Global / Other",
};

const ASIA_KEYWORDS = ["shanghai", "singapore", "cn", "sg"];
const EU_KEYWORDS = ["rotterdam", "hamburg", "nl", "de"];
const US_WEST_KEYWORDS = ["los angeles", "long beach"];
const US_EAST_KEYWORDS = ["new york", "houston", "us"];

export function classifyCorridor(subject: CorridorSubject): CorridorClassification {
  const origin = subject.origin.toLowerCase();
  const destination = subject.destination.toLowerCase();

  const isAsia = ASIA_KEYWORDS.some((token) => origin.includes(token));
  const isEU = EU_KEYWORDS.some((token) => origin.includes(token));
  const isUSWest = US_WEST_KEYWORDS.some((token) => destination.includes(token));
  const isUSEast = US_EAST_KEYWORDS.some((token) => destination.includes(token));

  if (isAsia && isUSWest) {
    return { id: "asia-us-west", label: CORRIDOR_LABELS["asia-us-west"] };
  }

  if (isEU && isUSEast) {
    return { id: "eu-us-east", label: CORRIDOR_LABELS["eu-us-east"] };
  }

  const originUS = origin.includes("us") || origin.includes("houston") || origin.includes("los angeles");
  if (originUS && isUSEast) {
    return { id: "intra-us", label: CORRIDOR_LABELS["intra-us"] };
  }

  return { id: "other", label: CORRIDOR_LABELS.other };
}

export function getCorridorLabel(id: CorridorId): string {
  return CORRIDOR_LABELS[id];
}

export function isCorridorId(value: string | null): value is CorridorId {
  if (!value) return false;
  return value === "asia-us-west" || value === "eu-us-east" || value === "intra-us" || value === "other";
}

export const CORRIDOR_FILTER_OPTIONS: Array<{ value: CorridorId | "all"; label: string }> = [
  { value: "all", label: "All Corridors" },
  { value: "asia-us-west", label: CORRIDOR_LABELS["asia-us-west"] },
  { value: "eu-us-east", label: CORRIDOR_LABELS["eu-us-east"] },
  { value: "intra-us", label: CORRIDOR_LABELS["intra-us"] },
  { value: "other", label: CORRIDOR_LABELS.other },
];
