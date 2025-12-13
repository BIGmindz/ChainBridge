import React from "react";

import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";

type ServiceStatus = "online" | "partial" | "offline";

interface ServiceDescriptor {
  id: "chainiq" | "chainpay-consumer";
  name: string;
  status: ServiceStatus;
  description: string;
}

const SERVICES: ServiceDescriptor[] = [
  {
    id: "chainiq",
    name: "ChainIQ",
    status: "online",
    description: "Risk scoring & IQ routes are mounted under /iq.",
  },
  {
    id: "chainpay-consumer",
    name: "ChainPay Consumer",
    status: "partial",
    description: "Milestone payout logic in progress on this branch.",
  },
];

// TODO: wire SERVICE status to backend health endpoint once available

export const ServiceStatusSummary: React.FC = () => {
  return (
    <Card className="w-full mb-4">
      <div className="px-4 py-3 border-b border-slate-800/50">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Service Status
        </div>
      </div>
      <div className="flex flex-col md:flex-row md:flex-wrap divide-y md:divide-y-0 md:divide-x divide-slate-800/50">
        {SERVICES.map((service) => (
          <div
            key={service.id}
            className="flex-1 min-w-[200px] px-4 py-3 flex items-start justify-between gap-3"
          >
            <div className="flex flex-col gap-1">
              <div className="text-sm font-medium text-slate-200">{service.name}</div>
              <p className="text-xs text-slate-400">{service.description}</p>
            </div>
            <Badge variant={
              service.status === "online" ? "success" :
              service.status === "partial" ? "warning" : "danger"
            }>
              {service.status === "online" && "Online"}
              {service.status === "partial" && "In Progress"}
              {service.status === "offline" && "Offline"}
            </Badge>
          </div>
        ))}
      </div>
    </Card>
  );
};
