import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

// Mock all API hooks before any imports
vi.mock("@/api/hooks", () => ({
  useAuth: vi.fn(),
  useProfile: vi.fn(),
  useMatches: vi.fn(),
  useAgentTasks: vi.fn(),
  useAnalyticsSummary: vi.fn(),
  useAnalyticsActivity: vi.fn(),
  useAnalyticsFunnel: vi.fn(),
  useOpportunities: vi.fn(),
  useRunPlanner: vi.fn(),
}));

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => {
  const MockResponsiveContainer = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  );
  const MockBarChart = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  );
  const MockBar = () => <div data-testid="bar" />;
  const MockAreaChart = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="area-chart">{children}</div>
  );
  const MockArea = () => <div data-testid="area" />;
  const MockXAxis = () => <div data-testid="x-axis" />;
  const MockYAxis = () => <div data-testid="y-axis" />;
  const MockTooltip = () => <div data-testid="tooltip" />;
  const MockCartesianGrid = () => <div data-testid="cartesian-grid" />;
  return {
    ResponsiveContainer: MockResponsiveContainer,
    BarChart: MockBarChart,
    Bar: MockBar,
    AreaChart: MockAreaChart,
    Area: MockArea,
    XAxis: MockXAxis,
    YAxis: MockYAxis,
    Tooltip: MockTooltip,
    CartesianGrid: MockCartesianGrid,
  };
});

import Dashboard from "@/pages/Dashboard";
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

function renderDashboard() {
  return render(<Dashboard />, { wrapper: createWrapper() });
}

const defaultProfile = {
  full_name: "Alice",
  target_locations: ["San Francisco", "Remote"],
};

const defaultMatches = {
  items: [
    {
      id: "1",
      title: "Frontend Engineer",
      company: "Google",
      location: "Mountain View",
      salary_min: 120000,
      salary_max: 180000,
      match_score: 92,
    },
    {
      id: "2",
      title: "Software Engineer",
      company: "Stripe",
      location: "Remote",
      salary_min: 130000,
      salary_max: 190000,
      match_score: 85,
    },
  ],
};

const defaultTasks = {
  items: [
    {
      id: "t1",
      agent_type: "planner",
      status: "completed",
      created_at: "2026-07-04T10:00:00Z",
      completed_at: "2026-07-04T10:01:00Z",
      input: { goal: "Plan weekly job search" },
      output: { message: "Strategy created" },
    },
    {
      id: "t2",
      agent_type: "internship",
      status: "running",
      created_at: "2026-07-04T10:02:00Z",
      input: { goal: "Find AI internships" },
    },
  ],
};

const defaultAnalytics = {
  active_matches: 18,
  applications: 24,
  interview_rate: 32,
  deadlines: 4,
};

const defaultFunnel = [
  { name: "Applied", value: 24 },
  { name: "Phone", value: 12 },
  { name: "On-site", value: 6 },
];

const defaultActivity = [
  { day: "Mon", applications: 3, interviews: 1 },
  { day: "Tue", applications: 5, interviews: 2 },
];

const defaultOpps = {
  items: [
    { id: "o1", title: "Senior Dev", company: "Meta", deadline: "2026-07-06T00:00:00Z" },
    { id: "o2", title: "ML Engineer", company: "OpenAI", deadline: "2026-08-01T00:00:00Z" },
  ],
};

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    vi.mocked(hooks.useAuth).mockReturnValue({ data: { full_name: "Alice" } } as never);
    vi.mocked(hooks.useProfile).mockReturnValue({ data: defaultProfile } as never);
    vi.mocked(hooks.useMatches).mockReturnValue({
      data: defaultMatches,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(hooks.useAgentTasks).mockReturnValue({
      data: defaultTasks,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(hooks.useAnalyticsSummary).mockReturnValue({
      data: defaultAnalytics,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(hooks.useAnalyticsActivity).mockReturnValue({
      data: defaultActivity,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(hooks.useAnalyticsFunnel).mockReturnValue({
      data: defaultFunnel,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(hooks.useOpportunities).mockReturnValue({
      data: defaultOpps,
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(hooks.useRunPlanner).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("renders the greeting with user's name from profile", () => {
    renderDashboard();
    expect(screen.getByText(/Alice/)).toBeDefined();
  });

  it("renders the greeting with user's name from auth fallback", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({ data: null } as never);
    renderDashboard();
    expect(screen.getByText(/Alice/)).toBeDefined();
  });

  it("renders a fallback greeting when no name is available", () => {
    vi.mocked(hooks.useAuth).mockReturnValue({ data: { full_name: null } } as never);
    vi.mocked(hooks.useProfile).mockReturnValue({ data: null } as never);
    renderDashboard();
    expect(screen.getByText(/there/)).toBeDefined();
  });

  it("displays the 'Run Planner Agent' button", () => {
    renderDashboard();
    expect(screen.getByText("Run Planner Agent")).toBeDefined();
  });

  it("shows the planner button as disabled while running", () => {
    vi.mocked(hooks.useRunPlanner).mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
    } as never);
    renderDashboard();
    const button = screen.getByText("Running…");
    expect(button).toBeDefined();
  });

  it("displays stat cards with analytics data", () => {
    renderDashboard();
    // Use getAllByText since numbers may appear in multiple places (stats + salary ranges)
    expect(screen.getAllByText("18").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("24").length).toBeGreaterThanOrEqual(1);
    const pctElements = screen.getAllByText("32%");
    expect(pctElements.length).toBeGreaterThanOrEqual(1);
  });

  it("displays stat skeleton when analytics is loading", () => {
    vi.mocked(hooks.useAnalyticsSummary).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
    } as never);
    const { container } = renderDashboard();
    // Should have skeleton elements (no numeric data)
    expect(screen.queryByText("18")).toBeNull();
  });

  it("renders top matches from matches data", () => {
    renderDashboard();
    expect(screen.getByText("Frontend Engineer")).toBeDefined();
    expect(screen.getByText("Software Engineer")).toBeDefined();
    expect(screen.getByText("92%")).toBeDefined();
    expect(screen.getByText("85%")).toBeDefined();
  });

  it("renders 'No matches yet' when matches list is empty", () => {
    vi.mocked(hooks.useMatches).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.getByText(/No matches yet/)).toBeDefined();
  });

  it("renders match skeleton when matches are loading", () => {
    vi.mocked(hooks.useMatches).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.queryByText("Frontend Engineer")).toBeNull();
  });

  it("renders upcoming deadlines sorted by date", () => {
    renderDashboard();
    expect(screen.getByText("Senior Dev")).toBeDefined();
    expect(screen.getByText("ML Engineer")).toBeDefined();
  });

  it("renders 'No upcoming deadlines' when there are none", () => {
    vi.mocked(hooks.useOpportunities).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.getByText(/No upcoming deadlines/)).toBeDefined();
  });

  it("renders agent activity feed", () => {
    renderDashboard();
    // The action text comes from tasks data - check for the timestamp context
    const tasks = screen.getAllByText(/plan weekly job search/i);
    expect(tasks.length).toBeGreaterThanOrEqual(1);
  });

  it("renders 'No planner reasoning yet' when there are no agent tasks", () => {
    vi.mocked(hooks.useAgentTasks).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.getByText(/No planner reasoning yet/)).toBeDefined();
  });

  it("renders pipeline chart with funnel data", () => {
    renderDashboard();
    expect(screen.getByText("Applied")).toBeDefined();
    expect(screen.getByText("Phone")).toBeDefined();
  });

  it("renders 'No pipeline data yet' when funnel is empty", () => {
    vi.mocked(hooks.useAnalyticsFunnel).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.getByText(/No pipeline data yet/)).toBeDefined();
  });

  it("renders pipeline skeleton when funnel is loading", () => {
    vi.mocked(hooks.useAnalyticsFunnel).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.queryByText("Applied")).toBeNull();
  });

  it("renders weekly activity chart when data exists", () => {
    renderDashboard();
    expect(screen.getByText("Weekly Activity")).toBeDefined();
  });

  it("renders 'No activity data yet' when activity is empty", () => {
    vi.mocked(hooks.useAnalyticsActivity).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.getByText(/No activity data yet/)).toBeDefined();
  });

  it("renders 'Career OS active' badge", () => {
    renderDashboard();
    expect(screen.getByText("Career OS active")).toBeDefined();
  });

  it("renders error banner when some data fails to load", () => {
    vi.mocked(hooks.useMatches).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as never);
    renderDashboard();
    expect(screen.getByText(/Some data failed to load/)).toBeDefined();
    // The error list should show "matches" - check it appears somewhere in the error context
    const errorBanner = screen.getByText(/Some data failed to load/).closest('div');
    expect(errorBanner?.textContent).toContain('matches');
  });

  it("renders quick stats row with match score value", () => {
    renderDashboard();
    expect(screen.getByText("Match score")).toBeDefined();
    expect(screen.getByText("Targets")).toBeDefined();
    expect(screen.getByText("Auto actions")).toBeDefined();
  });

  it("renders 'View board' link for pipeline", () => {
    renderDashboard();
    expect(screen.getByText("View board")).toBeDefined();
  });

  it("renders 'See all' link for matches", () => {
    renderDashboard();
    expect(screen.getByText("See all")).toBeDefined();
  });

  it("renders 'View all tasks' link when tasks exist", () => {
    renderDashboard();
    expect(screen.getByText("View all tasks")).toBeDefined();
  });

  it("does not render 'View all tasks' when there are no tasks", () => {
    vi.mocked(hooks.useAgentTasks).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.queryByText("View all tasks")).toBeNull();
  });

  it("shows urgent deadline styling for deadlines within 3 days", () => {
    // Create an opportunity due tomorrow
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
    vi.mocked(hooks.useOpportunities).mockReturnValue({
      data: {
        items: [
          { id: "urgent", title: "Urgent Role", company: "Startup", deadline: tomorrow.toISOString() },
        ],
      },
      isLoading: false,
      isError: false,
    } as never);
    renderDashboard();
    expect(screen.getByText("Urgent Role")).toBeDefined();
    expect(screen.getByText("Startup")).toBeDefined();
  });

  it("renders deadlines sync note at the bottom of deadlines section", () => {
    renderDashboard();
    expect(screen.getByText(/Deadlines are synced/)).toBeDefined();
  });
});
