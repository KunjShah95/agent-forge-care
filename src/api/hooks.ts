import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "./client";

// ─── Auth ───────────────────────────────────────────────

export function useAuth() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.auth.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
    enabled: !!api.getAuthToken(),
  });
}

// ─── Profile ────────────────────────────────────────────

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: api.profile.get,
    enabled: !!api.getAuthToken(),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.profile.update,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

// ─── Opportunities ──────────────────────────────────────

export function useOpportunities(params?: { type?: string; search?: string; remote?: boolean; work_type?: string }) {
  return useQuery({
    queryKey: ["opportunities", params],
    queryFn: () => api.opportunities.list(params),
    enabled: !!api.getAuthToken(),
  });
}

export function useOpportunity(id: string) {
  return useQuery({
    queryKey: ["opportunities", id],
    queryFn: () => api.opportunities.get(id),
    enabled: !!id,
  });
}

export function useMatches() {
  return useQuery({
    queryKey: ["opportunities", "matches"],
    queryFn: api.opportunities.matches,
    enabled: !!api.getAuthToken(),
  });
}

export function useRefreshOpportunities() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (query?: string) => api.opportunities.refresh(query),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });
}

// ─── Applications ───────────────────────────────────────

export function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: api.applications.list,
    enabled: !!api.getAuthToken(),
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.applications.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof api.applications.update>[1] }) =>
      api.applications.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.applications.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });
}

// ─── Contacts ───────────────────────────────────────────

export function useContacts() {
  return useQuery({
    queryKey: ["contacts"],
    queryFn: api.contacts.list,
    enabled: !!api.getAuthToken(),
  });
}

export function useCreateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.contacts.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contacts"] }),
  });
}

export function useUpdateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof api.contacts.update>[1] }) =>
      api.contacts.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contacts"] }),
  });
}

export function useDeleteContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.contacts.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contacts"] }),
  });
}

// ─── Agents ─────────────────────────────────────────────

export function useAgentTasks(params?: { status?: string }) {
  return useQuery({
    queryKey: ["agent-tasks", params],
    queryFn: () => api.agents.getTasks(params),
    enabled: !!api.getAuthToken(),
    refetchInterval: 10_000, // Poll every 10s
  });
}

export function useAgentTask(id: string) {
  return useQuery({
    queryKey: ["agent-tasks", id],
    queryFn: () => api.agents.getTask(id),
    enabled: !!api.getAuthToken() && !!id,
    refetchInterval: 5_000,
  });
}

export function useRunPlanner() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.agents.runPlanner,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-tasks"] }),
  });
}

export function useRunMonitor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.agents.runMonitor,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-tasks"] }),
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.agents.deleteTask,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-tasks"] }),
  });
}

export function useRetryTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.agents.retryTask,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-tasks"] }),
  });
}

export function useCancelTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.agents.cancelTask,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-tasks"] }),
  });
}

export function useClearTasks() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.agents.clearTasks,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-tasks"] }),
  });
}


// ─── Memory ─────────────────────────────────────────────

export function useMemory() {
  return useQuery({
    queryKey: ["memory"],
    queryFn: api.memory.list,
    enabled: !!api.getAuthToken(),
  });
}

export function useCreateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.memory.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memory"] }),
  });
}

export function useUpdateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof api.memory.update>[1] }) =>
      api.memory.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memory"] }),
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.memory.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memory"] }),
  });
}

// ─── Analytics ──────────────────────────────────────────

export function useAnalyticsSummary() {
  return useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: api.analytics.summary,
    enabled: !!api.getAuthToken(),
  });
}

export function useAnalyticsActivity() {
  return useQuery({
    queryKey: ["analytics", "activity"],
    queryFn: api.analytics.activity,
    enabled: !!api.getAuthToken(),
  });
}

export function useAnalyticsFunnel() {
  return useQuery({
    queryKey: ["analytics", "funnel"],
    queryFn: api.analytics.funnel,
    enabled: !!api.getAuthToken(),
  });
}

export function useAnalyticsSkillsDemand() {
  return useQuery({
    queryKey: ["analytics", "skills-demand"],
    queryFn: api.analytics.skillsDemand,
    enabled: !!api.getAuthToken(),
  });
}

// ─── Interview Prep ─────────────────────────────────────

export function useInterviewPrep() {
  return useMutation({
    mutationFn: api.agents.interviewPrep,
  });
}

// ─── Research ───────────────────────────────────────────

export function useResearch() {
  return useMutation({
    mutationFn: api.agents.research,
  });
}

// ─── Cover Letter ───────────────────────────────────────

export function useCoverLetter() {
  return useMutation({
    mutationFn: api.agents.coverLetter,
  });
}

// ─── Career Guidance ────────────────────────────────────

export function useCareerGuidance() {
  return useMutation({
    mutationFn: api.agents.careerGuidance,
  });
}

// ─── Networking Outreach ─────────────────────────────────

export function useNetworkingOutreach() {
  return useMutation({
    mutationFn: api.agents.networkingOutreach,
  });
}

// ─── Internship Discovery ───────────────────────────────

export function useInternshipDiscovery() {
  return useMutation({
    mutationFn: api.agents.internshipDiscover,
  });
}

// ─── Job Discovery ──────────────────────────────────────

export function useJobDiscovery() {
  return useMutation({
    mutationFn: api.agents.jobDiscover,
  });
}

// ─── Resume Tailor ──────────────────────────────────────

export function useResumeTailor() {
  return useMutation({
    mutationFn: api.agents.resumeTailor,
  });
}

// ─── Hackathons ────────────────────────────────────────

export function useHackathons() {
  return useQuery({
    queryKey: ["opportunities", "hackathons"],
    queryFn: api.opportunities.hackathons,
    enabled: !!api.getAuthToken(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useScanHackathons() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (opts?: { skills?: string[]; alert_enabled?: boolean; email_enabled?: boolean }) =>
      api.opportunities.scanHackathons(opts),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["opportunities", "hackathons"] });
      qc.invalidateQueries({ queryKey: ["opportunities", "matches"] });
    },
  });
}

export function useLocations() {
  return useQuery({
    queryKey: ["opportunities", "locations"],
    queryFn: api.opportunities.locations,
    enabled: !!api.getAuthToken(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useFilterOptions() {
  return useQuery({
    queryKey: ["opportunities", "filters"],
    queryFn: api.opportunities.filters,
    enabled: !!api.getAuthToken(),
    staleTime: 10 * 60 * 1000,
  });
}

// ─── Monitor Alerts ─────────────────────────────────────

export function useAlertConfigs() {
  return useQuery({
    queryKey: ["monitor", "alerts"],
    queryFn: api.monitor.listAlerts,
    enabled: !!api.getAuthToken(),
  });
}

export function useCreateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.monitor.createAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitor"] }),
  });
}

export function useUpdateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<import("./client").AlertConfig> }) =>
      api.monitor.updateAlert(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitor"] }),
  });
}

export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.monitor.deleteAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitor"] }),
  });
}

export function useMonitorSettings() {
  return useQuery({
    queryKey: ["monitor", "settings"],
    queryFn: api.monitor.getSettings,
    enabled: !!api.getAuthToken(),
  });
}

export function useUpdateMonitorSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<import("./client").MonitorSettings>) =>
      api.monitor.updateSettings(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["monitor", "settings"] }),
  });
}

// ─── Notifications ──────────────────────────────────────

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: api.notifications.list,
    enabled: !!api.getAuthToken(),
    refetchInterval: 15_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.notifications.markRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.notifications.markAllRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}

// ─── Resume ──────────────────────────────────────────────

export function useResumeAnalysis(enabled: boolean) {
  return useQuery({
    queryKey: ["resume", "ats-analysis"],
    queryFn: api.resume.atsAnalysis,
    enabled,
    staleTime: 0,
  });
}

export function useResumes() {
  return useQuery({
    queryKey: ["resumes"],
    queryFn: api.resume.list,
    enabled: !!api.getAuthToken(),
  });
}

export function useDeleteResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.resume.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.resume.upload(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["resumes"] }),
  });
}

export function useResumeSearch(q?: string) {
  return useQuery({
    queryKey: ["resume-search", q],
    queryFn: () => api.resume.search(q || ""),
    enabled: !!q,
  });
}

// ─── Interview Sessions ──────────────────────────────────

export function useInterviewSessions() {
  return useQuery({
    queryKey: ["interview-sessions"],
    queryFn: api.interview.sessions.list,
    enabled: !!api.getAuthToken(),
  });
}

export function useCreateInterviewSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.interview.sessions.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interview-sessions"] }),
  });
}

export function useInterviewFeedback() {
  return useMutation({
    mutationFn: api.interview.feedback,
  });
}

// ─── Hiring Agent ─────────────────────────────────────────

export function useHiringPipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.hiringAgent.pipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["hiring-agent"] }),
  });
}

export function useHiringExtract(enabled: boolean) {
  return useQuery({
    queryKey: ["hiring-agent", "extract"],
    queryFn: api.hiringAgent.extract,
    enabled,
    staleTime: 60_000,
  });
}

export function useHiringEvaluate() {
  return useMutation({
    mutationFn: api.hiringAgent.evaluateText,
  });
}

export function useHiringAts(enabled: boolean) {
  return useQuery({
    queryKey: ["hiring-agent", "ats"],
    queryFn: api.hiringAgent.ats,
    enabled,
    staleTime: 60_000,
  });
}

export function useHiringMatchJd() {
  return useMutation({
    mutationFn: api.hiringAgent.matchJd,
  });
}

export function useHiringCoverLetter() {
  return useMutation({
    mutationFn: api.hiringAgent.coverLetter,
  });
}

export function useHiringGithubEnrich() {
  return useMutation({
    mutationFn: api.hiringAgent.githubEnrich,
  });
}

export function useHiringPortfolioEnrich() {
  return useMutation({
    mutationFn: api.hiringAgent.portfolioEnrich,
  });
}

export function useHiringLiveDemos() {
  return useMutation({
    mutationFn: api.hiringAgent.liveDemos,
  });
}

export function useHiringReport() {
  return useQuery({
    queryKey: ["hiring-agent", "report"],
    queryFn: api.hiringAgent.report,
    enabled: false,
  });
}

export function useHiringHistory() {
  return useQuery({
    queryKey: ["hiring-agent", "history"],
    queryFn: api.hiringAgent.history,
    enabled: !!api.getAuthToken(),
    staleTime: 120_000,
  });
}
