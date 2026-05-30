import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "./client";

// ─── Auth ───────────────────────────────────────────────

export function useAuth() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: api.auth.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Profile ────────────────────────────────────────────

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: api.profile.get,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.profile.update,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });
}

// ─── Opportunities ──────────────────────────────────────

export function useOpportunities(params?: { type?: string; search?: string; remote?: boolean }) {
  return useQuery({
    queryKey: ["opportunities", params],
    queryFn: () => api.opportunities.list(params),
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
  });
}

export function useRefreshOpportunities() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.opportunities.refresh,
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
    refetchInterval: 10_000, // Poll every 10s
  });
}

export function useAgentTask(id: string) {
  return useQuery({
    queryKey: ["agent-tasks", id],
    queryFn: () => api.agents.getTask(id),
    enabled: !!id,
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

// ─── Memory ─────────────────────────────────────────────

export function useMemory() {
  return useQuery({
    queryKey: ["memory"],
    queryFn: api.memory.list,
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
  });
}

export function useAnalyticsActivity() {
  return useQuery({
    queryKey: ["analytics", "activity"],
    queryFn: api.analytics.activity,
  });
}

export function useAnalyticsFunnel() {
  return useQuery({
    queryKey: ["analytics", "funnel"],
    queryFn: api.analytics.funnel,
  });
}

export function useAnalyticsSkillsDemand() {
  return useQuery({
    queryKey: ["analytics", "skills-demand"],
    queryFn: api.analytics.skillsDemand,
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

// ─── Resume Tailor ──────────────────────────────────────

export function useResumeTailor() {
  return useMutation({
    mutationFn: api.agents.resumeTailor,
  });
}

// ─── Monitor Alerts ─────────────────────────────────────

export function useAlertConfigs() {
  return useQuery({
    queryKey: ["monitor", "alerts"],
    queryFn: api.monitor.listAlerts,
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

// ─── Notifications ──────────────────────────────────────

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: api.notifications.list,
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
