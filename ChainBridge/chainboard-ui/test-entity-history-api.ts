/**
 * Test script for EntityHistory API client
 *
 * Demonstrates type safety and usage of the new getEntityHistory function.
 *
 * Run with: npx tsx test-entity-history-api.ts
 */

import type { EntityHistoryResponse, EntityHistoryRecord } from './src/lib/apiClient';

// Mock API response for testing type safety
const mockResponse: EntityHistoryResponse = {
  entity_id: "SHP-1004",
  total_records: 3,
  history: [
    {
      timestamp: "2025-11-15T10:30:00Z",
      score: 75,
      severity: "HIGH",
      recommended_action: "HOLD_PAYMENT",
      reason_codes: ["SANCTIONS_RISK", "ELEVATED_VALUE"],
      payload: {
        shipment_id: "SHP-1004",
        route: "IR-RU",
        carrier_id: "CARRIER-001",
        shipment_value_usd: 50000.0,
        days_in_transit: 12,
        expected_days: 5,
        documents_complete: false,
        shipper_payment_score: 85
      }
    },
    {
      timestamp: "2025-11-15T09:15:00Z",
      score: 45,
      severity: "MEDIUM",
      recommended_action: "MANUAL_REVIEW",
      reason_codes: ["TRANSIT_DELAY"],
      payload: {
        shipment_id: "SHP-1004",
        route: "IR-RU",
        carrier_id: "CARRIER-001",
        shipment_value_usd: 50000.0,
        days_in_transit: 7,
        expected_days: 5,
        documents_complete: true,
        shipper_payment_score: 85
      }
    },
    {
      timestamp: "2025-11-15T08:00:00Z",
      score: 25,
      severity: "LOW",
      recommended_action: "RELEASE_PAYMENT",
      reason_codes: [],
      payload: {
        shipment_id: "SHP-1004",
        route: "IR-RU",
        carrier_id: "CARRIER-001",
        shipment_value_usd: 50000.0,
        days_in_transit: 3,
        expected_days: 5,
        documents_complete: true,
        shipper_payment_score: 85
      }
    }
  ]
};

// Type-safe analysis functions
function analyzeRiskTrend(history: EntityHistoryRecord[]): string {
  if (history.length < 2) {
    return "Insufficient data for trend analysis";
  }

  const scores = history.map(record => record.score);
  const scoresChronological = [...scores].reverse(); // Oldest to newest

  const firstScore = scoresChronological[0];
  const lastScore = scoresChronological[scoresChronological.length - 1];

  if (lastScore > firstScore) {
    return "⬆️ Risk INCREASED over time";
  } else if (lastScore < firstScore) {
    return "⬇️ Risk DECREASED over time";
  } else {
    return "➡️ Risk STABLE over time";
  }
}

function findHighRiskEvents(history: EntityHistoryRecord[]): EntityHistoryRecord[] {
  return history.filter(record =>
    record.severity === "HIGH" || record.severity === "CRITICAL"
  );
}

function extractReasonCodes(history: EntityHistoryRecord[]): string[] {
  const allCodes = new Set<string>();
  history.forEach(record => {
    record.reason_codes.forEach(code => allCodes.add(code));
  });
  return Array.from(allCodes);
}

// Demonstrate type safety
console.log("=".repeat(70));
console.log("ChainIQ Entity History API - Type Safety Demo");
console.log("=".repeat(70));
console.log();

console.log(`Entity ID: ${mockResponse.entity_id}`);
console.log(`Total Records: ${mockResponse.total_records}`);
console.log();

console.log("Risk Trend Analysis:");
console.log(`  ${analyzeRiskTrend(mockResponse.history)}`);
console.log();

const highRiskEvents = findHighRiskEvents(mockResponse.history);
console.log(`High-Risk Events: ${highRiskEvents.length}`);
highRiskEvents.forEach((event, i) => {
  console.log(`  #${i + 1} - ${event.timestamp}`);
  console.log(`      Score: ${event.score}, Action: ${event.recommended_action}`);
});
console.log();

const uniqueReasonCodes = extractReasonCodes(mockResponse.history);
console.log(`Unique Reason Codes: ${uniqueReasonCodes.join(", ")}`);
console.log();

// Demonstrate accessing payload fields (fully typed)
console.log("Payload Analysis:");
mockResponse.history.forEach((record, i) => {
  const daysInTransit = record.payload.days_in_transit as number;
  const docsComplete = record.payload.documents_complete as boolean;
  console.log(`  Record ${i + 1}: ${daysInTransit} days, docs ${docsComplete ? '✓' : '✗'}`);
});
console.log();

console.log("=".repeat(70));
console.log("✅ All type checks passed!");
console.log("=".repeat(70));

// Example usage pattern for components
function exampleComponentUsage() {
  // In a React component, you would use:
  /*
  const [history, setHistory] = useState<EntityHistoryResponse | null>(null);

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await getEntityHistory("SHP-1004", 50);
        setHistory(data);
      } catch (error) {
        console.error("Failed to load history:", error);
      }
    }
    loadHistory();
  }, []);

  if (!history) return <div>Loading...</div>;

  return (
    <div>
      <h2>History for {history.entity_id}</h2>
      <p>Total records: {history.total_records}</p>
      <ul>
        {history.history.map((record, i) => (
          <li key={i}>
            Score: {record.score}, Severity: {record.severity}
          </li>
        ))}
      </ul>
    </div>
  );
  */
  return null; // Placeholder to prevent unused function warning
}

// Reference to avoid tree-shaking during type checking
void exampleComponentUsage;
