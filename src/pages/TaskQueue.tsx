import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Clock, CheckCircle2, AlertCircle, Loader2, Brain,
  Target, FileSearch, MessageSquare, Network, Bell,
  Sparkles, Zap, Trash2, Play, XCircle,
} from "lucide-react";
import { useAgentTasks, useRunPlanner, useRunMonitor } from "@/api/hooks";
import type { AgentTask } from "@/api/client";

const agentTypeDisplayMap: Record<string, { name: string; icon: React.ElementType }> = {
  planner: { name: "Planner Agent", icon: Brain },
  internship: { name: "Internship Agent", icon: Target },
  job: { name: "Job Agent", icon: Zap },
  research: { name: "Research Agent", icon: FileSearch },
  resume: { name: "Resume Agent", icon: Sparkles },
  interview: { name: "Interview Agent", icon: MessageSquare },
  networking: { name: "Networking Agent", icon: Network },
  monitor: { name: "Opportunity Monitor", icon: Bell },
  memory: { name: "Memory Layer", icon: Brain },
};

function getAgentDisplay(agentType: string) {
  return agentTypeDisplayMap[agentType] || { name: `${agentType} Agent`, icon: Brain };
}

function formatTimeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function AgentQueueItem({ item, onRun }: { item: AgentTask; onRun?: (item: AgentTask) => void }) {
  const display = getAgentDisplay(item.agent_type);
  const Icon = display.icon;
  const taskDescription = item.input?.goal as string || item.input?.task as string || display.name + " task";

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition group">
      <div className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${
        item.status === "running"
          ? "bg-primary/10 border border-primary/30"
          : item.status === "completed"
            ? "bg-success/10 border border-success/20"
            : item.status === "failed"
              ? "bg-destructive/10 border border-destructive/20"
              : "bg-muted-foreground/10 border border-muted-foreground/20"
      }`}>
        <Icon className={`h-4 w-4 ${
          item.status === "running" ? "text-primary" :
          item.status === "completed" ? "text-success" :
          item.status === "failed" ? "text-destructive" : "text-muted-foreground"
        }`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">{taskDescription}</span>
          <Badge variant="outline" className={`text-[10px] ${
            item.status === "running" ? "bg-primary/10 text-primary border-primary/20" :
            item.status === "completed" ? "bg-success/10 text-success border-success/20" :
            item.status === "failed" ? "bg-destructive/10 text-destructive border-destructive/20" :
            "bg-muted-foreground/10 text-muted-foreground"
          }`}>
            {item.status === "queued" && <Clock className="h-3 w-3 mr-0.5" />}
            {item.status === "running" && <Loader2 className="h-3 w-3 mr-0.5 animate-spin" />}
            {item.status === "completed" && <CheckCircle2 className="h-3 w-3 mr-0.5" />}
            {item.status === "failed" && <XCircle className="h-3 w-3 mr-0.5" />}
            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
          </Badge>
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
          <span>{display.name}</span>
          <span>·</span>
          <span>{formatTimeAgo(item.created_at)}</span>
        </div>
      </div>
      <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition">
        {item.status === "queued" && (
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => onRun?.(item)}>
            <Play className="h-3 w-3" />
          </Button>
        )}
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive" onClick={() => toast.error("Not implemented yet")}>
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 p-4 rounded-xl bg-muted/30">
          <Skeleton className="h-9 w-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function TaskQueue() {
  const { data, isLoading } = useAgentTasks();
  const runPlanner = useRunPlanner();
  const runMonitor = useRunMonitor();
  const [hideCompleted, setHideCompleted] = useState(false);

  const handleRunTask = (task: AgentTask) => {
    if (task.agent_type === "planner") {
      const goal = (task.input?.goal as string) || "Run planner";
      runPlanner.mutate(goal, {
        onSuccess: () => toast.success("Task queued"),
        onError: () => toast.error("Failed to queue task"),
      });
    } else if (task.agent_type === "monitor") {
      runMonitor.mutate(undefined, {
        onSuccess: () => toast.success("Monitor scan queued"),
        onError: () => toast.error("Failed to queue scan"),
      });
    } else {
      toast.error("Re-run not supported for this agent type");
    }
  };

  const handleRetryFailed = () => {
    failedItems.forEach(handleRunTask);
  };

  const tasks = data?.items ?? [];
  const activeItems = tasks.filter((q) => q.status === "queued" || q.status === "running");
  const completedItems = tasks.filter((q) => q.status === "completed");
  const failedItems = tasks.filter((q) => q.status === "failed");
  const visibleCompleted = hideCompleted ? [] : completedItems;

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Task Queue</h1>
          <p className="text-muted-foreground mt-1">
            View and manage all agent tasks. Queued, running, completed, and failed tasks.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" disabled={failedItems.length === 0 || runPlanner.isPending || runMonitor.isPending} onClick={handleRetryFailed}>
            <Play className="h-4 w-4" /> Retry Failed
          </Button>
          <Button variant="outline" className="gap-2" onClick={() => { toast.error("Not implemented yet"); setHideCompleted(true); }} disabled={hideCompleted || completedItems.length === 0}>
            <Trash2 className="h-4 w-4" /> Clear Completed
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: "Total", value: tasks.length, icon: Clock, color: "text-foreground" },
          { label: "Queued", value: tasks.filter((q) => q.status === "queued").length, icon: Clock, color: "text-muted-foreground" },
          { label: "Running", value: tasks.filter((q) => q.status === "running").length, icon: Loader2, color: "text-primary" },
          { label: "Completed", value: completedItems.length, icon: CheckCircle2, color: "text-success" },
          { label: "Failed", value: failedItems.length, icon: AlertCircle, color: "text-destructive" },
        ].map((s) => (
          <Card key={s.label} className="glass p-4 text-center">
            <s.icon className={`h-5 w-5 mx-auto mb-1 ${s.color}`} />
            <div className={`text-2xl font-display font-bold ${s.color}`}>
              {isLoading ? <Skeleton className="h-8 w-8 mx-auto" /> : s.value}
            </div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="active">
        <TabsList className="glass">
          <TabsTrigger value="active">Active ({activeItems.length})</TabsTrigger>
          <TabsTrigger value="completed">Completed ({visibleCompleted.length})</TabsTrigger>
          <TabsTrigger value="failed">Failed ({failedItems.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4 space-y-2">
          {isLoading ? (
            <LoadingSkeleton />
          ) : activeItems.length === 0 ? (
            <div className="text-center py-16">
              <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-success opacity-50" />
              <h3 className="font-display font-semibold text-lg">All caught up</h3>
              <p className="text-sm text-muted-foreground">No active tasks in the queue.</p>
            </div>
          ) : (
            activeItems.map((item) => <AgentQueueItem key={item.id} item={item} onRun={handleRunTask} />)
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-4 space-y-2">
          {isLoading ? (
            <LoadingSkeleton />
          ) : visibleCompleted.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <Clock className="h-8 w-8 mx-auto mb-2 opacity-40" />
              No completed tasks yet.
            </div>
          ) : (
            visibleCompleted.map((item) => <AgentQueueItem key={item.id} item={item} />)
          )}
        </TabsContent>

        <TabsContent value="failed" className="mt-4 space-y-2">
          {isLoading ? (
            <LoadingSkeleton />
          ) : failedItems.length === 0 ? (
            <div className="text-center py-16">
              <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-success opacity-50" />
              <h3 className="font-display font-semibold text-lg">Zero failures</h3>
              <p className="text-sm text-muted-foreground">All tasks completed successfully.</p>
            </div>
          ) : (
            failedItems.map((item) => (
              <div key={item.id}>
                <AgentQueueItem item={item} />
                {item.error && (
                  <div className="ml-12 mt-1 p-3 rounded-lg bg-destructive/5 border border-destructive/10 text-xs text-destructive/80 font-mono">
                    Error: {item.error}
                  </div>
                )}
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
