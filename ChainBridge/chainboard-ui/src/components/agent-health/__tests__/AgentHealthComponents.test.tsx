import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentHealthCard } from "../AgentHealthCard";
import { AgentHealthList } from "../AgentHealthList";

const baseSummary = {
  total: 5,
  valid: 5,
  invalid: 0,
  invalidRoles: [] as string[],
};

describe("AgentHealth components", () => {
  it("renders healthy summary state", () => {
    render(
      <AgentHealthCard
        summary={baseSummary}
        loading={false}
        error={null}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText(/Agent Health/i)).toBeInTheDocument();
    expect(screen.getByText(/Healthy/i)).toBeInTheDocument();
    const totalBlock = screen.getByText(/Total/i).closest("div");
    expect(totalBlock).toHaveTextContent("5");
  });

  it("renders attention state when invalid agents exist", () => {
    render(
      <AgentHealthCard
        summary={{ ...baseSummary, invalid: 2, valid: 3, invalidRoles: ["x"] }}
        loading={false}
        error={null}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText(/Attention Needed/i)).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows error state with retry button", () => {
    const retry = vi.fn();
    render(
      <AgentHealthCard
        summary={null}
        loading={false}
        error={new Error("fetch failed")}
        onRetry={retry}
      />,
    );

    expect(screen.getByText(/Unable to load agent status/i)).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /Retry/i });
    expect(button).toBeInTheDocument();
  });

  it("lists invalid agent roles", () => {
    render(
      <AgentHealthList
        invalidRoles={["AI_AGENT_TIM", "SECURITY_COMPLIANCE_ENGINEER"]}
        loading={false}
        error={null}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText(/Invalid Roles/i)).toBeInTheDocument();
    expect(screen.getByText("AI_AGENT_TIM")).toBeInTheDocument();
    expect(screen.getByText("SECURITY_COMPLIANCE_ENGINEER")).toBeInTheDocument();
  });

  it("renders positive state when no invalid roles", () => {
    render(
      <AgentHealthList invalidRoles={[]} loading={false} error={null} onRetry={vi.fn()} />,
    );

    expect(screen.getByText(/All agents valid/i)).toBeInTheDocument();
  });

  it("shows list error state", () => {
    render(
      <AgentHealthList
        invalidRoles={[]}
        loading={false}
        error={new Error("oops")}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText(/oops/)).toBeInTheDocument();
  });
});
