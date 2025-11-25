import type {
    ChainDocsDossier,
    ChainPayPlan,
} from "../types/chainbridge";

const deepClone = <T>(payload: T): T => JSON.parse(JSON.stringify(payload));

const chainDocsLibrary: Record<string, ChainDocsDossier> = {
  "SHP-2048-VC-77": {
    shipmentId: "SHP-2048-VC-77",
    lastPolicyReview: "2025-05-03T10:15:00Z",
    aiConfidenceScore: 0.93,
    missingDocuments: ["Sensor Exception Report"],
    documents: [
      {
        documentId: "DOC-INV-2048",
        type: "Commercial Invoice",
        status: "VERIFIED",
        version: 4,
        hash: "0x1b9a40f7cd8739aa",
        updatedAt: "2025-05-02T14:21:00Z",
        issuedBy: "TransGlobal Freight",
        storageLocation: "s3://chainbridge/chaindocs/SHP-2048-VC-77/invoice.pdf",
        mletrReady: true,
        complianceTags: ["INCOTERMS:DAP", "HS:840991"],
      },
      {
        documentId: "DOC-BOL-2048",
        type: "Bill of Lading",
        status: "VERIFIED",
        version: 2,
        hash: "0x83a11c92beff1029",
        updatedAt: "2025-05-02T10:11:00Z",
        issuedBy: "PortChain Alliance",
        storageLocation: "s3://chainbridge/chaindocs/SHP-2048-VC-77/bol.pdf",
        mletrReady: true,
        complianceTags: ["SIGNATURE:BLOCKCHAIN", "PORT:CN-SHA"],
      },
      {
        documentId: "DOC-POD-2048",
        type: "Proof of Delivery",
        status: "PRESENT",
        version: 1,
        hash: "0xdbe711c02f19b4e1",
        updatedAt: "2025-05-03T08:54:00Z",
        issuedBy: "Vector Logistics",
        storageLocation: "s3://chainbridge/chaindocs/SHP-2048-VC-77/pod.pdf",
        mletrReady: false,
        complianceTags: ["SIGNATURE:PENDING"],
      },
      {
        documentId: "DOC-SENSOR-2048",
        type: "Sensor Telemetry",
        status: "FLAGGED",
        version: 7,
        hash: "0xfab9c0443b713211",
        updatedAt: "2025-05-03T12:00:00Z",
        issuedBy: "ChainSense",
        storageLocation: "s3://chainbridge/chaindocs/SHP-2048-VC-77/sensor.json",
        mletrReady: false,
        complianceTags: ["TEMP:EXCURSION"],
      },
    ],
  },
  "SHP-2048-VC-79": {
    shipmentId: "SHP-2048-VC-79",
    lastPolicyReview: "2025-05-01T09:00:00Z",
    aiConfidenceScore: 0.82,
    missingDocuments: ["Insurance Certificate", "Proof of Delivery"],
    documents: [
      {
        documentId: "DOC-INV-2049",
        type: "Commercial Invoice",
        status: "VERIFIED",
        version: 1,
        hash: "0x99f010f736de30b3",
        updatedAt: "2025-05-01T07:21:00Z",
        issuedBy: "Mariner Imports",
        storageLocation: "s3://chainbridge/chaindocs/SHP-2048-VC-79/invoice.pdf",
        mletrReady: true,
        complianceTags: ["INCOTERMS:FOB"],
      },
      {
        documentId: "DOC-PACK-2049",
        type: "Packing List",
        status: "PRESENT",
        version: 2,
        hash: "0x7aa14072ff09d832",
        updatedAt: "2025-04-30T19:12:00Z",
        issuedBy: "Mariner Imports",
        storageLocation: "s3://chainbridge/chaindocs/SHP-2048-VC-79/packing.pdf",
        mletrReady: true,
        complianceTags: ["COMPLETENESS:PASS"],
      },
    ],
  },
};

const chainPayPlans: Record<string, ChainPayPlan> = {
  "SHP-2048-VC-77": {
    shipmentId: "SHP-2048-VC-77",
    templateId: "TPL-20-70-10",
    customer: "Vector Logistics",
    totalValueUsd: 1250000,
    floatReductionEstimate: 4.2,
    coveragePercent: 92,
    creditTermsDays: 30,
    milestones: [
      {
        id: "M1",
        label: "Pickup / Token Mint",
        payoutPercent: 20,
        amountUsd: 250000,
        expectedRelease: "2025-05-01T12:00:00Z",
        status: "PAID",
        paidAt: "2025-05-01T14:32:00Z",
      },
      {
        id: "M2",
        label: "Midline IoT Health",
        payoutPercent: 70,
        amountUsd: 875000,
        expectedRelease: "2025-05-05T08:00:00Z",
        status: "HELD",
        holdReason: "Sensor excursion awaiting manual override",
      },
      {
        id: "M3",
        label: "Proof of Delivery",
        payoutPercent: 10,
        amountUsd: 125000,
        expectedRelease: "2025-05-07T18:00:00Z",
        status: "PENDING",
      },
    ],
    alerts: [
      {
        id: "ALERT-77-1",
        severity: "warning",
        message: "ChainSense flagged temp excursion at hour 42.",
        createdAt: "2025-05-03T12:14:00Z",
      },
      {
        id: "ALERT-77-2",
        severity: "info",
        message: "Awaiting updated Proof of Delivery signature.",
        createdAt: "2025-05-03T15:02:00Z",
      },
    ],
  },
  "SHP-2048-VC-79": {
    shipmentId: "SHP-2048-VC-79",
    templateId: "TPL-30-60-10",
    customer: "Mariner Imports",
    totalValueUsd: 860000,
    floatReductionEstimate: 6.1,
    coveragePercent: 88,
    creditTermsDays: 45,
    milestones: [
      {
        id: "M1",
        label: "Pre-carriage docs",
        payoutPercent: 30,
        amountUsd: 258000,
        expectedRelease: "2025-05-02T09:00:00Z",
        status: "PAID",
        paidAt: "2025-05-02T09:15:00Z",
      },
      {
        id: "M2",
        label: "In-transit telemetry",
        payoutPercent: 60,
        amountUsd: 516000,
        expectedRelease: "2025-05-06T10:00:00Z",
        status: "PENDING",
      },
      {
        id: "M3",
        label: "Final proofpack",
        payoutPercent: 10,
        amountUsd: 86000,
        expectedRelease: "2025-05-09T17:00:00Z",
        status: "PENDING",
      },
    ],
    alerts: [
      {
        id: "ALERT-79-1",
        severity: "info",
        message: "Awaiting customs clearance confirmation.",
        createdAt: "2025-05-03T04:00:00Z",
      },
    ],
  },
};

const latencyRangeMs = [300, 900];

const withLatency = <T>(payload: T, delayOverride?: number): Promise<T> => {
  const delay = delayOverride ??
    Math.floor(
      Math.random() * (latencyRangeMs[1] - latencyRangeMs[0]) + latencyRangeMs[0]
    );

  return new Promise((resolve) => setTimeout(() => resolve(deepClone(payload)), delay));
};

export async function fetchChainDocsDossier(shipmentId: string): Promise<ChainDocsDossier> {
  const dossier = chainDocsLibrary[shipmentId] ?? chainDocsLibrary["SHP-2048-VC-77"];
  return withLatency(dossier);
}

export async function fetchChainPayPlan(shipmentId: string): Promise<ChainPayPlan> {
  const plan = chainPayPlans[shipmentId] ?? chainPayPlans["SHP-2048-VC-77"];
  return withLatency(plan);
}
