import React, { useState } from 'react';

import ChainSensePanel from '../components/ChainSensePanel';
import ShipmentFeed from '../components/ShipmentFeed';
import RiskConsole from '../components/RiskConsole';
import SettlementsConsole from '../components/SettlementsConsole';
import AgentTelemetryPanel from '../components/AgentTelemetryPanel';
import SettlementsPanel from '../components/SettlementsPanel';
import TokenFlowPanel from '../components/TokenFlowPanel';
import TokenTrajectoryPanel from '../components/TokenTrajectoryPanel';
import { IoTHealthPanel } from '../components/iot/IoTHealthPanel';
import { RiskEventsPanel } from '../components/risk/RiskEventsPanel';
import { ContextRiskPanel } from '../components/risk/ContextRiskPanel';
import { ChainPaySettlementPanel } from '../features/chainpay/ChainPaySettlementPanel';
import { useChainPaySettlement, useChainPayAnalyticsUsdMxn, useUsdMxnGuardrails } from '../features/chainpay/hooks';
import { ChainPayAnalyticsPanel } from '../features/chainpay/ChainPayAnalyticsPanel';
import { ChainPayGuardrailPanel } from '../features/chainpay/ChainPayGuardrailPanel';

export type IntentId = string;

const OperatorConsole: React.FC = () => {
  const [selectedIntentId, setSelectedIntentId] = useState<IntentId | null>(null);
  const defaultShipmentId = 'SHIP-12345';
  const {
    data: settlementStatus,
    loading: settlementLoading,
    error: settlementError,
    refetch: refetchSettlement,
  } = useChainPaySettlement(defaultShipmentId);
  const {
    data: analyticsSnapshot,
    loading: analyticsLoading,
    error: analyticsError,
    refetch: refetchAnalytics,
  } = useChainPayAnalyticsUsdMxn();
  const {
    data: guardrailsSnapshot,
    loading: guardrailsLoading,
    error: guardrailsError,
    refetch: refetchGuardrails,
  } = useUsdMxnGuardrails();

  return (
    <div className="grid grid-cols-3 gap-4 p-6 bg-gray-950 min-h-screen">
      {/* Left column – ChainSense & IoT */}
      <div className="space-y-4">
        <ChainSensePanel />
        <IoTHealthPanel />
        <ShipmentFeed />
        <TokenFlowPanel />
        <TokenTrajectoryPanel />
      </div>

      {/* Middle column – ChainPay Risk Rail */}
      <div className="space-y-4">
        <RiskConsole
          selectedIntentId={selectedIntentId}
          onSelectIntent={setSelectedIntentId}
        />
        <ContextRiskPanel intentId={selectedIntentId} />
        <RiskEventsPanel selectedIntentId={selectedIntentId} />
        <SettlementsPanel
          selectedIntentId={selectedIntentId}
          onSelectIntent={setSelectedIntentId}
        />
      </div>

      {/* Right column – Settlements + Agents */}
      <div className="space-y-4">
        <ChainPayGuardrailPanel
          snapshot={guardrailsSnapshot}
          loading={guardrailsLoading}
          error={guardrailsError}
          onRefresh={refetchGuardrails}
        />
        <ChainPaySettlementPanel
          status={settlementStatus}
          loading={settlementLoading}
          error={settlementError}
          onRefresh={refetchSettlement}
          corridorLabel="USD→MXN"
          policyLabel="P0"
          assetLabel="CB-USDx"
        />
        <ChainPayAnalyticsPanel
          snapshot={analyticsSnapshot}
          loading={analyticsLoading}
          error={analyticsError}
          onRefresh={refetchAnalytics}
          corridorLabel="USD→MXN"
          policyLabel="P0"
          assetLabel="CB-USDx"
        />
        <SettlementsConsole />
        <AgentTelemetryPanel />
      </div>
    </div>
  );
};

export default OperatorConsole;
