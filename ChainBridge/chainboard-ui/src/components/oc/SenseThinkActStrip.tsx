import React from "react";

import { Card } from "../ui/Card";

export const SenseThinkActStrip: React.FC = () => {
  const items = [
    {
      key: "sense",
      label: "Sense",
      description: "Ingest live shipment, EDI, and IoT events.",
      color: "text-blue-400",
    },
    {
      key: "think",
      label: "Think",
      description: "Score risk and readiness with ChainIQ.",
      color: "text-purple-400",
    },
    {
      key: "act",
      label: "Act",
      description: "Trigger milestone-based payouts via ChainPay.",
      color: "text-emerald-400",
    },
  ];

  return (
    <Card className="w-full mb-4">
      <div className="flex flex-col md:flex-row md:items-stretch divide-y md:divide-y-0 md:divide-x divide-slate-800/50">
        {items.map((item) => (
          <div key={item.key} className="flex-1 px-4 py-3 flex flex-col gap-1">
            <div className={`text-xs font-bold uppercase tracking-wider ${item.color}`}>
              {item.label}
            </div>
            <p className="text-sm text-slate-400 leading-snug">
              {item.description}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
};
