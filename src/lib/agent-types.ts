import {
  Brain, Target, Zap, FileSearch, Sparkles, MessageSquare,
  Network, Bell, Layers3, type LucideIcon,
  Loader2, CheckCircle2, Clock, AlertCircle,
} from "lucide-react";

export type AgentTypeKey =
  | "planner" | "internship" | "job" | "research"
  | "resume" | "interview" | "networking" | "monitor" | "memory" | "discovery";

export type AgentTypeInfo = {
  key: AgentTypeKey;
  name: string;
  icon: LucideIcon;
  label: string;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const T = (k: AgentTypeKey, n: string, i: LucideIcon, l: string): AgentTypeInfo => ({ key: k, name: n, icon: i, label: l });

export const AGENT_TYPES: AgentTypeInfo[] = [
  T("planner", "Planner Agent", Brain, "Planner"),
  T("internship", "Internship Agent", Target, "Internship"),
  T("job", "Job Agent", Zap, "Job"),
  T("research", "Research Agent", FileSearch, "Research"),
  T("resume", "Resume Agent", Sparkles, "Resume"),
  T("interview", "Interview Agent", MessageSquare, "Interview"),
  T("networking", "Networking Agent", Network, "Networking"),
  T("monitor", "Opportunity Monitor", Bell, "Opportunity Monitor"),
  T("memory", "Memory Layer", Layers3, "Memory"),
  T("discovery", "Discovery Agent", FileSearch, "Discovery"),
];

export const AGENT_TYPE_MAP: Record<string, AgentTypeInfo> = {};
AGENT_TYPES.forEach((a) => { AGENT_TYPE_MAP[a.key] = a; });

export const AGENT_KEYS: AgentTypeKey[] = AGENT_TYPES.map((a) => a.key);

export const AGENT_LABELS: string[] = AGENT_TYPES.map((a) => a.label);

export function getAgentInfo(agentType: string): AgentTypeInfo {
  return AGENT_TYPE_MAP[agentType] || { key: agentType as AgentTypeKey, name: `${agentType} Agent`, icon: Brain, label: agentType };
}

export type TaskStatusKey = "running" | "completed" | "queued" | "failed";

export const STATUS_CONFIG: Record<TaskStatusKey, {
  icon: LucideIcon;
  className: string;
  label: string;
}> = {
  running: { icon: Loader2, className: "text-primary animate-spin", label: "Running" },
  completed: { icon: CheckCircle2, className: "text-success", label: "Complete" },
  queued: { icon: Clock, className: "text-muted-foreground", label: "Queued" },
  failed: { icon: AlertCircle, className: "text-destructive", label: "Failed" },
};
