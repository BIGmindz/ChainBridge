import React from "react";

import { Card } from "../ui/Card";

interface ServiceDescriptor {
  id: "chainiq" | "chainpay-consumer";
  name: string;
  status: string;
  description: string;
}

const SERVICES: ServiceDescriptor[] = [
  {
    id: "chainiq",
    name: "chainiq",
    status: "mounted",
    description: "/iq routes",
  },
  {
    id: "chainpay-consumer",
    name: "chainpay_consumer",
    status: "partial",
    description: "milestone logic",
  },
];

// TODO: wire SERVICE status to backend health endpoint once available

export const ServiceStatusSummary: React.FC = () => {
  return (
    <Card className="w-full mb-4">
      <div className="px-4 py-3 border-b border-slate-800/50">
        <p className="text-xs text-slate-600 uppercase tracking-wider font-mono">
          service_status
        </p>
      </div>

      {/* Demo data warning */}
      <div className="border-b border-slate-700/50 bg-slate-900/50 px-4 py-2">
        <p className="text-xs text-slate-500 font-mono">
          UNLINKED / DEMO DATA — Not linked to live backend
        </p>
      </div>

      <div className="divide-y divide-slate-800/50 font-mono text-sm">
        {SERVICES.map((service) => (
          <div
            key={service.id}
            className="px-4 py-3 flex items-center justify-between"
          >
            <div className="flex flex-col gap-0.5">
              <span className="text-slate-400">{service.name}</span>
              <span className="text-xs text-slate-600">{service.description}</span>
            </div>
            <span className="text-slate-500">{service.status}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};
