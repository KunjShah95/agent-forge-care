import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import AgentChat from "@/components/AgentChat";
import { Layers3, Loader2 } from "lucide-react";
import { useAgentTasks } from "@/api/hooks";
import type { AgentTask } from "@/api/client";
import { AGENT_KEYS, STATUS_CONFIG, getAgentInfo } from "@/lib/agent-types";

export default function AgentConsole() {
  const { data: tasksData, isLoading: tasksLoading } = useAgentTasks();

  const agentMetrics = AGENT_KEYS.map((type) => {
    const tasks = (tasksData?.items || []).filter(
      (t: AgentTask) => t.agent_type === type
    );
    const total = tasks.length;
    const completed = tasks.filter((t: AgentTask) => t.status === "completed").length;
    const success = total > 0 ? Math.round((completed / total) * 100) : 100;
    const durations = tasks
      .filter((t: AgentTask) => t.status === "completed" && t.created_at && t.completed_at)
      .map((t: AgentTask) => new Date(t.completed_at!).getTime() - new Date(t.created_at).getTime());
    const avgDuration =
      durations.length > 0
        ? Math.round(durations.reduce((a: number, b: number) => a + b, 0) / durations.length / 1000) + "s"
        : "—";
    return { agent: type.charAt(0).toUpperCase() + type.slice(1), runs: total, success, avgDuration };
  });

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
                    const Icon = getAgentInfo(m.agent.toLowerCase()).icon;
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
              {(tasksData?.items || []).map((t: AgentTask) => {
                const info2 = getAgentInfo(t.agent_type);
                const Icon = info2.icon;
                const status = STATUS_CONFIG[t.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.queued;
                const StatusIcon = status.icon;
                return (
                  <div key={t.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/30 transition group">
                    <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center group-hover:scale-110 transition shrink-0">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{info2.name}</span>
                        <Badge variant="outline" className={`text-[10px] ${status.className}`}>
                          <StatusIcon className={`h-3 w-3 mr-0.5 ${t.status === "running" ? "animate-spin" : ""}`} />
                          {status.label}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5">
                        {t.input?.goal ? String(t.input.goal) : t.agent_type || "Processing..."}
                      </p>
                      <p className="text-[11px] text-muted-foreground/60 mt-0.5">
                        {t.created_at ? new Date(t.created_at).toLocaleString() : ""}
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
                { label: "Queued", value: tasksData?.items?.filter((t: AgentTask) => t.status === "queued").length ?? 0, color: "text-muted-foreground" },
                { label: "Running", value: tasksData?.items?.filter((t: AgentTask) => t.status === "running").length ?? 0, color: "text-primary" },
                { label: "Completed", value: tasksData?.items?.filter((t: AgentTask) => t.status === "completed").length ?? 0, color: "text-success" },
                { label: "Failed", value: tasksData?.items?.filter((t: AgentTask) => t.status === "failed").length ?? 0, color: "text-destructive" },
              ].map((item) => (
                <div key={item.label} className="p-3 rounded-xl bg-muted/30 text-center">
                  <div className={`text-2xl font-display font-bold ${item.color}`}>{item.value}</div>
                  <div className="text-xs text-muted-foreground">{item.label}</div>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">Recent Tasks</div>
              {(tasksData?.items || []).slice(0, 3).map((task: AgentTask) => (
                <div key={task.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/30 text-sm">
                  <Loader2 className={`h-3 w-3 ${task.status === "running" ? "animate-spin text-primary" : "text-muted-foreground"} shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{task.input?.goal ? String(task.input.goal) : task.agent_type || "Task"}</div>
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
