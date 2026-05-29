import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import AgentChat from "@/components/AgentChat";
import {
  Brain, Sparkles, Clock, CheckCircle2,
  AlertCircle, Loader2, Target, FileSearch, MessageSquare,
  Network, Bell, Zap, Layers3,
} from "lucide-react";
import { useAgentTasks } from "@/api/hooks";

const agentIcons: Record<string, React.ElementType> = {
  "Planner Agent": Brain,
  "Internship Agent": Target,
  "Job Agent": Zap,
  "Research Agent": FileSearch,
  "Resume Agent": Sparkles,
  "Interview Agent": MessageSquare,
  "Networking Agent": Network,
  "Opportunity Monitor": Bell,
  "Memory Layer": Layers3,
};

const statusConfig = {
  running: { icon: Loader2, className: "text-primary animate-spin", label: "Running" },
  completed: { icon: CheckCircle2, className: "text-success", label: "Complete" },
  queued: { icon: Clock, className: "text-muted-foreground", label: "Queued" },
  failed: { icon: AlertCircle, className: "text-destructive", label: "Failed" },
};

const agentMetrics = [
  { agent: "Planner", runs: 847, success: 98, avgDuration: "12s" },
  { agent: "Internship", runs: 2134, success: 96, avgDuration: "45s" },
  { agent: "Job", runs: 1892, success: 97, avgDuration: "38s" },
  { agent: "Research", runs: 643, success: 99, avgDuration: "22s" },
  { agent: "Resume", runs: 412, success: 95, avgDuration: "18s" },
  { agent: "Interview", runs: 298, success: 94, avgDuration: "15s" },
  { agent: "Networking", runs: 184, success: 97, avgDuration: "8s" },
  { agent: "Monitor", runs: 4256, success: 99, avgDuration: "55s" },
];

export default function AgentConsole() {
  const { data: tasksData, isLoading: tasksLoading } = useAgentTasks();

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Agent Console</h1>
          <p className="text-muted-foreground mt-1">
            Chat with the planner agent to decompose goals into tasks, dispatch specialist agents, and see results stream in real-time.
          </p>
        </div>
      </div>

      {/* Streaming Chat Interface */}
      <AgentChat />

      {/* Agent Performance Metrics */}
      <div>
        <h2 className="font-display text-lg font-semibold mb-3">Agent Performance</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {agentMetrics.map((m) => (
            <Card key={m.agent} className="glass p-4 hover:shadow-glow transition">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {(() => {
                    const Icon = agentIcons[`${m.agent} Agent`] || Brain;
                    return <Icon className="h-4 w-4 text-primary" />;
                  })()}
                  <span className="font-medium text-sm">{m.agent}</span>
                </div>
                <Badge variant="outline" className="text-[10px] bg-success/10 text-success border-success/20">
                  {m.success}%
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{m.runs.toLocaleString()} runs</span>
                <span>avg {m.avgDuration}</span>
              </div>
              <Progress value={m.success} className="h-1 mt-2" />
            </Card>
          ))}
        </div>
      </div>

      {/* Live Activity Feed + Task Queue */}
      <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-6">
        {/* Activity Feed */}
        <Card className="glass p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold">Live Agent Activity</h2>
            <Badge className="bg-primary/10 text-primary border-primary/20 gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-glow" />
              Live
            </Badge>
          </div>
          {tasksLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-16 rounded-lg bg-muted/30 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto scrollbar-thin">
              {(tasksData?.items || []).map((t: any) => {
                const agentName = t.agent_type
                  ? t.agent_type.charAt(0).toUpperCase() + t.agent_type.slice(1) + " Agent"
                  : t.agent;
                const Icon = agentIcons[agentName] || Brain;
                const taskStatus = t.status || t.status;
                const status = statusConfig[taskStatus as keyof typeof statusConfig] || statusConfig.queued;
                const StatusIcon = status.icon;
                return (
                  <div key={t.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/30 transition group">
                    <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center group-hover:scale-110 transition shrink-0">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{agentName}</span>
                        <Badge variant="outline" className={`text-[10px] ${status.className}`}>
                          <StatusIcon className={`h-3 w-3 mr-0.5 ${t.status === "running" ? "animate-spin" : ""}`} />
                          {status.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {t.input?.goal || t.action || t.agent_type || "Processing..."}
                      </p>
                      <p className="text-[11px] text-muted-foreground/60 mt-0.5">
                        {t.created_at ? new Date(t.created_at).toLocaleString() : t.timestamp}
                      </p>
                    </div>
                    <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition">
                      Details
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Task Queue Summary */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Task Queue</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Queued", value: tasksData?.items?.filter((t: any) => t.status === "queued").length || 3, color: "text-muted-foreground" },
                { label: "Running", value: tasksData?.items?.filter((t: any) => t.status === "running").length || 1, color: "text-primary" },
                { label: "Completed", value: tasksData?.items?.filter((t: any) => t.status === "completed").length || 847, color: "text-success" },
                { label: "Failed", value: tasksData?.items?.filter((t: any) => t.status === "failed").length || 2, color: "text-destructive" },
              ].map((item) => (
                <div key={item.label} className="p-3 rounded-xl bg-muted/30 text-center">
                  <div className={`text-2xl font-display font-bold ${item.color}`}>{item.value}</div>
                  <div className="text-xs text-muted-foreground">{item.label}</div>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">Recent Tasks</div>
              {(tasksData?.items || []).slice(0, 3).map((task: any) => (
                <div key={task.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/30 text-sm">
                  <Loader2 className={`h-3 w-3 ${task.status === "running" ? "animate-spin text-primary" : "text-muted-foreground"} shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{task.input?.goal || task.agent_type || "Task"}</div>
                    <div className="text-xs text-muted-foreground">
                      {task.agent_type} · {task.status}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <Button variant="outline" size="sm" className="w-full gap-2" asChild>
              <a href="/app/tasks">
                <Layers3 className="h-3 w-3" />
                View full queue
              </a>
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
