const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "");

export const apiConfigError = import.meta.env.DEV || import.meta.env.VITE_API_URL
  ? null
  : "Missing VITE_API_URL. Set it in Vercel to your deployed backend, e.g. https://your-backend.example.com/api/v1";

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

if (typeof window !== "undefined") {
  authToken = localStorage.getItem("auth_token");
}

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  if (!API_BASE) {
    throw new Error(apiConfigError || "API base URL is not configured");
  }

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
  // Deprecated: sign-in now handled via Firebase SDK in auth-context.tsx
  register: (data: { email: string; password: string; full_name: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/register", { method: "POST", body: data }),

  // Deprecated: sign-in now handled via Firebase SDK in auth-context.tsx
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", { method: "POST", body: data }),

  me: () => request<{ id: string; email: string; full_name: string }>("/auth/me"),
};

// Profile
export const profile = {
  get: () => request<Profile>("/profile"),
  update: (data: Partial<Profile>) =>
    request<Profile>("/profile", { method: "PUT", body: data }),
  uploadAvatar: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    const token = getAuthToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}/profile/avatar`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new ApiError(response.status, errorData?.detail || response.statusText, errorData);
    }

    return response.json() as Promise<Profile>;
  },
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
  list: () => request<{ items: Contact[]; total: number; page: number }>("/contacts"),

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

  interviewPrep: (data: { company: string; role: string; type?: string }) =>
    request<{ questions: { skill: string; question: string; type: string; tips: string }[]; prep_tips: string[]; total_questions: number; focus_areas: string[]; message: string }>("/agents/interview-prep", { method: "POST", body: data }),

  research: (data: { company: string; focus?: string; topics?: string[] }) =>
    request<Record<string, unknown>>("/agents/research", { method: "POST", body: data }),

  coverLetter: (data: { company: string; role: string; application_id?: string }) =>
    request<{ cover_letter: string }>("/agents/cover-letter", { method: "POST", body: data }),

  resumeTailor: (data: { role_type: string; target_company?: string; skills?: string[] }) =>
    request<{ suggestions: string[]; action_items: string[]; ats_keywords: string[]; summary: string; message: string }>("/agents/resume-tailor", { method: "POST", body: data }),

  deleteTask: (id: string) => request<void>(`/agents/tasks/${id}`, { method: "DELETE" }),

  careerGuidance: (data: { query: string; context?: Record<string, unknown> }) =>
    request<{ guidance: Record<string, unknown>; message: string }>("/agents/career-guidance", { method: "POST", body: data }),

  networkingOutreach: (data: { target_companies?: string[]; role?: string; skills?: string[] }) =>
    request<{ templates: { type: string; subject: string; message: string }[]; best_practices: string[]; message: string }>(
      "/agents/networking-outreach", { method: "POST", body: data }
    ),

  internshipDiscover: (data: { query?: string; location?: string; skills?: string[] }) =>
    request<Record<string, unknown>>("/agents/internship-discover", { method: "POST", body: data }),

  jobDiscover: (data: { query?: string; location?: string; skills?: string[] }) =>
    request<Record<string, unknown>>("/agents/job-discover", { method: "POST", body: data }),

  retryTask: (id: string) =>
    request<{ status: string; message: string }>(`/agents/tasks/${id}/retry`, { method: "POST" }),

  cancelTask: (id: string) =>
    request<{ status: string; message: string }>(`/agents/tasks/${id}/cancel`, { method: "POST" }),

  clearTasks: () =>
    request<void>("/agents/tasks/clear", { method: "DELETE" }),
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
  full_name?: string;
  school?: string;
  graduation_date?: string;
  bio?: string;
  portfolio_url?: string;
  linkedin_url?: string;
  github_url?: string;
  avatar_url?: string;
  target_locations: string[];
  salary_min?: number;
  salary_max?: number;
  role_types: string[];
  company_sizes: string[];
  career_goal?: string;
  skills: { id?: string; name: string; proficiency: string }[];
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

export type AlertConfig = {
  id: string;
  name: string;
  keywords: string[];
  locations: string[];
  opportunity_types: string[];
  min_match_score: number;
  frequency: string;
  is_active: boolean;
  created_at: string;
};

export type MonitorSettings = {
  frequency: string;
  digest: boolean;
  push: boolean;
  realtime: boolean;
  min_match_score: number;
};

export const monitor = {
  listAlerts: () => request<AlertConfig[]>("/monitor/alerts"),
  createAlert: (data: { name: string; keywords?: string[]; locations?: string[]; opportunity_types?: string[]; min_match_score?: number; frequency?: string }) =>
    request<AlertConfig>("/monitor/alerts", { method: "POST", body: data }),
  updateAlert: (id: string, data: Partial<AlertConfig>) =>
    request<AlertConfig>(`/monitor/alerts/${id}`, { method: "PATCH", body: data }),
  deleteAlert: (id: string) => request<void>(`/monitor/alerts/${id}`, { method: "DELETE" }),

  getSettings: () => request<MonitorSettings>("/monitor/settings"),
  updateSettings: (data: Partial<MonitorSettings>) =>
    request<MonitorSettings>("/monitor/settings", { method: "PATCH", body: data }),
};

export type AtsAnalysis = {
  format_score: number;
  keyword_score: number;
  action_verb_score: number;
  missing_keywords: string[];
  present_keywords: string[];
  suggestions: string[];
  summary: string;
};

export const resume = {
  atsAnalysis: () => request<AtsAnalysis>("/resume/ats-analysis"),

  upload: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    const token = getAuthToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}/resume/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new ApiError(response.status, errorData?.detail || response.statusText, errorData);
    }

    return response.json() as Promise<{ filename: string; pages: number; characters: number; text: string }>;
  },

  search: (q: string) => request<{ items: { text: string; filename?: string; chunk_index?: number; pages?: number; characters?: number; score?: number }[] }>(`/resume/search`, { method: "GET", params: { q } }),

  list: () => request<{ items: ResumeItem[]; total: number }>("/resume"),

  delete: (filename: string) => request<void>(`/resume/${encodeURIComponent(filename)}`, { method: "DELETE" }),
};

export const interview = {
  sessions: {
    list: () => request<{ items: InterviewSession[] }>("/agents/interview-sessions"),
    create: (data: { company: string; type: string; score?: number; duration?: string }) =>
      request<InterviewSession>("/agents/interview-sessions", { method: "POST", body: data }),
  },
  feedback: (data: { question: string; answer: string; company?: string; role?: string }) =>
    request<{ feedback: string; score?: number; strengths?: string[]; improvements?: string[] }>(
      "/agents/interview-feedback",
      { method: "POST", body: data }
    ),
};

export type Notification = {
  id: string;
  title: string;
  body: string;
  type: "success" | "error" | "info";
  read: boolean;
  created_at: string;
};

export const notifications = {
  list: () => request<{ items: Notification[] }>("/notifications"),
  markRead: (id: string) => request<Notification>(`/notifications/${id}`, { method: "PATCH" }),
  markAllRead: () => request<{ status: string }>("/notifications/read-all", { method: "POST" }),
};

export type ResumeItem = {
  filename: string;
  pages: number;
  characters: number;
  uploaded_at?: string;
};

export type InterviewSession = {
  id: string;
  company: string;
  type: string;
  date: string;
  score?: number;
  duration?: string;
};

export type MemoryEntry = {
  id: string;
  key: string;
  value: unknown;
  weight: number;
  created_at: string;
  updated_at: string;
};
