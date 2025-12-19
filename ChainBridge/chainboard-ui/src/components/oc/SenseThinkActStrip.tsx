import React from "react";

import { Card } from "../ui/Card";

export const SenseThinkActStrip: React.FC = () => {
  const items = [
    {
      key: "sense",
      label: "sense",
      description: "event ingestion",
    },
    {
      key: "think",
      label: "think",
      description: "risk scoring",
    },
    {
      key: "act",
      label: "act",
      description: "payout triggers",
    },
  ];

  return (
    <Card className="w-full mb-4">
      <div className="flex flex-col md:flex-row md:items-stretch divide-y md:divide-y-0 md:divide-x divide-slate-800/50 font-mono">
        {items.map((item) => (
          <div key={item.key} className="flex-1 px-4 py-3 flex flex-col gap-1">
            <p className="text-xs text-slate-600 uppercase tracking-wider">
              {item.label}
            </p>
            <p className="text-sm text-slate-400">
              {item.description}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
};
