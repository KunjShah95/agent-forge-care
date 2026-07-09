import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

// Mock API hooks
vi.mock("@/api/hooks", () => ({
  useAgentTasks: vi.fn(),
}));

// Mock AgentChat component (it has complex chat logic with useChat)
vi.mock("@/components/AgentChat", () => ({
  default: () => <div data-testid="agent-chat-mock">Agent Chat</div>,
}));

// Mock lucide-react icons for simpler testing
vi.mock("lucide-react", async () => {
  const actual = await vi.importActual("lucide-react");
  return {
    ...actual,
    // Keep actual icon names but map them to simple spans for easier testing
  };
});

import AgentConsole from "@/pages/AgentConsole";
import * as hooks from "@/api/hooks";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function renderAgentConsole() {
  return render(<AgentConsole />, { wrapper: createWrapper() });
}

const sampleTasks = {
  items: [
    {
      id: "t1",
      agent_type: "planner",
      status: "completed",
      created_at: "2026-07-04T10:00:00Z",
      completed_at: "2026-07-04T10:02:00Z",
      input: { goal: "Plan weekly strategy" },
    },
    {
      id: "t2",
      agent_type: "internship",
      status: "running",
      created_at: "2026-07-04T10:05:00Z",
      input: { goal: "Find AI summer internships" },
    },
    {
      id: "t3",
      agent_type: "resume",
      status: "queued",
      created_at: "2026-07-04T10:06:00Z",
      input: { goal: "Tailor resume for Google" },
    },
    {
      id: "t4",
      agent_type: "research",
      status: "failed",
      created_at: "2026-07-04T09:00:00Z",
      input: { goal: "Research company culture" },
      error: "API rate limit exceeded",
    },
  ],
};

describe("AgentConsole", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(hooks.useAgentTasks).mockReturnValue({
      data: sampleTasks,
      isLoading: false,
      isError: false,
    } as never);
  });

  it("renders the page title", () => {
    renderAgentConsole();
    expect(screen.getByText("Agent Console")).toBeDefined();
  });

  it("renders the page description", () => {
    renderAgentConsole();
    expect(
      screen.getByText(/Chat with the planner agent to decompose goals/)
    ).toBeDefined();
  });

  it("renders the AgentChat component", () => {
    renderAgentConsole();
    expect(screen.getByTestId("agent-chat-mock")).toBeDefined();
  });

  it("renders the 'Agent Performance' section", () => {
    renderAgentConsole();
    expect(screen.getByText("Agent Performance")).toBeDefined();
  });

  it("displays agent metric cards for each agent type", () => {
    renderAgentConsole();
    // AGENT_KEYS includes planner, internship, job, research, resume, interview, networking, monitor, memory
    expect(screen.getByText("Planner")).toBeDefined();
    expect(screen.getByText("Internship")).toBeDefined();
    expect(screen.getByText("Research")).toBeDefined();
    expect(screen.getByText("Resume")).toBeDefined();
  });

  it("shows success percentage badges on agent cards", () => {
    renderAgentConsole();
    // Planner: 1 completed out of 1 = 100%
    const plannerBadges = screen.getAllByText("100%");
    expect(plannerBadges.length).toBeGreaterThanOrEqual(1);
  });

  it("shows run counts on agent cards", () => {
    renderAgentConsole();
    // Multiple agents may have 1 run each
    const runElements = screen.getAllByText(/1 runs/);
    expect(runElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders 'Live Agent Activity' heading", () => {
    renderAgentConsole();
    expect(screen.getByText("Live Agent Activity")).toBeDefined();
  });

  it("renders the 'Live' badge on activity feed", () => {
    renderAgentConsole();
    expect(screen.getByText("Live")).toBeDefined();
  });

  it("displays tasks in the activity feed", () => {
    renderAgentConsole();
    // Tasks appear in both the activity feed and recent tasks section
    const planTasks = screen.getAllByText(/Plan weekly strategy/);
    expect(planTasks.length).toBeGreaterThanOrEqual(1);
    const internshipTasks = screen.getAllByText(/Find AI summer internships/);
    expect(internshipTasks.length).toBeGreaterThanOrEqual(1);
  });

  it("renders status badges for tasks", () => {
    renderAgentConsole();
    const completeElements = screen.getAllByText("Complete");
    expect(completeElements.length).toBeGreaterThanOrEqual(1);
    const runningElements = screen.getAllByText("Running");
    expect(runningElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders 'Task Queue' section", () => {
    renderAgentConsole();
    expect(screen.getByText("Task Queue")).toBeDefined();
  });

  it("shows task queue statistics (queued, running, completed, failed)", () => {
    renderAgentConsole();
    // Task statuses: planner=completed, internship=running, resume=queued, research=failed
    // All four stats are "1" - use getAllByText and verify count
    const ones = screen.getAllByText("1");
    expect(ones.length).toBeGreaterThanOrEqual(4);
  });

  it("shows queue stat labels", () => {
    renderAgentConsole();
    // These labels appear in both the task queue and activity feed sections
    expect(screen.getAllByText("Queued").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Running").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Completed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Failed").length).toBeGreaterThanOrEqual(1);
  });

  it("renders recent tasks in the task queue section", () => {
    renderAgentConsole();
    expect(screen.getByText("Recent Tasks")).toBeDefined();
  });

  it("renders 'View full queue' button", () => {
    renderAgentConsole();
    expect(screen.getByText("View full queue")).toBeDefined();
  });

  it("renders skeleton loaders when tasks are loading", () => {
    vi.mocked(hooks.useAgentTasks).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);
    const { container } = renderAgentConsole();
    // Skeleton elements should be present
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders empty activity feed when no tasks exist", () => {
    vi.mocked(hooks.useAgentTasks).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as never);
    renderAgentConsole();
    // Task queue stats should all be 0
    const zeroElements = screen.getAllByText("0");
    expect(zeroElements.length).toBeGreaterThanOrEqual(3); // Queued, Running, Failed = 0, Completed = 0
  });

  it("shows task timestamp in activity feed", () => {
    renderAgentConsole();
    // Tasks have created_at, should render as locale string
    const yearElements = screen.getAllByText(/2026/);
    expect(yearElements.length).toBeGreaterThanOrEqual(1);
  });

  it("shows agent type labels in activity items", () => {
    renderAgentConsole();
    expect(screen.getByText("Planner Agent")).toBeDefined();
    expect(screen.getByText("Resume Agent")).toBeDefined();
  });

  it("renders 'Details' buttons on activity items", () => {
    renderAgentConsole();
    const detailsButtons = screen.getAllByText("Details");
    expect(detailsButtons.length).toBeGreaterThan(0);
  });

  it("renders progress bar on agent metric cards", () => {
    renderAgentConsole();
    // Progress bars have role="progressbar" in the shadcn component
    const progressBars = screen.getAllByRole("progressbar");
    expect(progressBars.length).toBeGreaterThan(0);
  });

  it("displays running status in UI", () => {
    renderAgentConsole();
    const runningElements = screen.getAllByText("Running");
    expect(runningElements.length).toBeGreaterThanOrEqual(1);
  });
});
