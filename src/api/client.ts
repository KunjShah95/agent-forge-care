const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
};

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, headers = {} } = options;

  let url = `${API_BASE}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const fetchHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  if (authToken) {
    fetchHeaders["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(url, {
    method,
    headers: fetchHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(response.status, errorData?.detail || response.statusText, errorData);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// Auth
export const auth = {
  register: (data: { email: string; password: string; full_name: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/register", { method: "POST", body: data }),

  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", { method: "POST", body: data }),

  me: () => request<{ id: string; email: string; full_name: string }>("/auth/me"),
};

// Profile
export const profile = {
  get: () => request<Profile>("/profile"),
  update: (data: Partial<Profile>) =>
    request<Profile>("/profile", { method: "PUT", body: data }),
};

// Opportunities
export const opportunities = {
  list: (params?: { type?: string; search?: string; remote?: boolean; page?: number; limit?: number }) =>
    request<{ items: Opportunity[]; total: number; page: number }>("/opportunities", { params }),

  get: (id: string) => request<Opportunity>(`/opportunities/${id}`),

  matches: () =>
    request<{ items: ScoredOpportunity[] }>("/opportunities/matches"),

  refresh: () =>
    request<{ task_id: string }>("/opportunities/refresh", { method: "POST" }),
};

// Applications
export const applications = {
  list: () => request<{ items: Application[] }>("/applications"),

  create: (data: { opportunity_id: string; notes?: string }) =>
    request<Application>("/applications", { method: "POST", body: data }),

  update: (id: string, data: { stage?: string; notes?: string; next_step?: string; next_date?: string }) =>
    request<Application>(`/applications/${id}`, { method: "PATCH", body: data }),

  delete: (id: string) =>
    request<void>(`/applications/${id}`, { method: "DELETE" }),
};

// Contacts
export const contacts = {
  list: () => request<{ items: Contact[] }>("/contacts"),

  create: (data: { name: string; role?: string; company?: string; email?: string }) =>
    request<Contact>("/contacts", { method: "POST", body: data }),

  update: (id: string, data: Partial<Contact>) =>
    request<Contact>(`/contacts/${id}`, { method: "PATCH", body: data }),

  delete: (id: string) => request<void>(`/contacts/${id}`, { method: "DELETE" }),
};

// Agents
export const agents = {
  runPlanner: (goal: string) =>
    request<{ task_id: string }>("/agents/planner/run", { method: "POST", body: { goal } }),

  getTasks: (params?: { status?: string; agent_type?: string; page?: number; limit?: number }) =>
    request<{ items: AgentTask[] }>("/agents/tasks", { params }),

  getTask: (id: string) => request<AgentTask>(`/agents/tasks/${id}`),

  runMonitor: () =>
    request<{ task_id: string }>("/agents/monitor/run", { method: "POST" }),
};

// Memory
export const memory = {
  list: () => request<{ items: MemoryEntry[] }>("/memory"),

  create: (data: { key: string; value: unknown; weight?: number }) =>
    request<MemoryEntry>("/memory", { method: "POST", body: data }),

  update: (id: string, data: { value?: unknown; weight?: number }) =>
    request<MemoryEntry>(`/memory/${id}`, { method: "PATCH", body: data }),

  delete: (id: string) => request<void>(`/memory/${id}`, { method: "DELETE" }),

  getContext: () => request<Record<string, unknown>>("/memory/context"),
};

// Analytics
export const analytics = {
  summary: () =>
    request<{
      active_matches: number;
      applications: number;
      interview_rate: number;
      deadlines: number;
    }>("/analytics/summary"),

  funnel: () =>
    request<{ name: string; value: number; rate: string }[]>("/analytics/funnel"),

  skillsDemand: () =>
    request<{ skill: string; demand: number }[]>("/analytics/skills-demand"),

  activity: () =>
    request<{ day: string; applications: number; interviews: number }[]>("/analytics/activity"),
};

// Types
export type Profile = {
  id: string;
  user_id: string;
  school?: string;
  graduation_date?: string;
  bio?: string;
  portfolio_url?: string;
  linkedin_url?: string;
  github_url?: string;
  target_locations: string[];
  salary_min?: number;
  salary_max?: number;
  role_types: string[];
  company_sizes: string[];
  career_goal?: string;
  skills: { id: string; name: string; proficiency: string }[];
};

export type Opportunity = {
  id: string;
  title: string;
  company: string;
  logo?: string;
  location?: string;
  remote: boolean;
  type: string;
  salary_min?: number;
  salary_max?: number;
  posted_date?: string;
  deadline?: string;
  description?: string;
  apply_url?: string;
  company_size?: string;
  skills_required: string[];
  source?: string;
};

export type ScoredOpportunity = Opportunity & {
  match_score: number;
  match_reasons: string[];
};

export type Application = {
  id: string;
  opportunity_id: string;
  stage: string;
  applied_date?: string;
  next_step?: string;
  next_date?: string;
  notes?: string;
  resume_version?: string;
  cover_letter?: string;
  created_at: string;
  updated_at: string;
  opportunity?: Opportunity;
};

export type Contact = {
  id: string;
  name: string;
  role?: string;
  company?: string;
  email?: string;
  linkedin_url?: string;
  status: string;
  last_contact?: string;
  notes?: string;
};

export type AgentTask = {
  id: string;
  agent_type: string;
  status: "queued" | "running" | "completed" | "failed";
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
};

export type MemoryEntry = {
  id: string;
  key: string;
  value: unknown;
  weight: number;
  created_at: string;
  updated_at: string;
};
