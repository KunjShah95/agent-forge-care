import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Clock, CheckCircle2, AlertCircle, Loader2, Brain,
  Target, FileSearch, MessageSquare, Network, Bell,
  Sparkles, Zap, Trash2, Play, XCircle,
} from "lucide-react";

type QueueItem = {
  id: string;
  task: string;
  agent: string;
  status: "queued" | "running" | "completed" | "failed";
  priority: "high" | "medium" | "low";
  created: string;
  eta?: string;
  progress?: number;
};

const queueItems: QueueItem[] = [
  { id: "q1", task: "Score internships for ML focus", agent: "Internship Agent", status: "running", priority: "high", created: "Just now", eta: "12s", progress: 65 },
  { id: "q2", task: "Tailor resume for Stripe SWE role", agent: "Resume Agent", status: "running", priority: "high", created: "2 min ago", eta: "30s", progress: 40 },
  { id: "q3", task: "Generate 8 mock questions for Stripe OA", agent: "Interview Agent", status: "queued", priority: "high", created: "2 min ago", eta: "15s" },
  { id: "q4", task: "Research Anthropic interview patterns", agent: "Research Agent", status: "queued", priority: "medium", created: "5 min ago", eta: "45s" },
  { id: "q5", task: "Draft outreach to Linear hiring manager", agent: "Networking Agent", status: "queued", priority: "medium", created: "10 min ago", eta: "20s" },
  { id: "q6", task: "Search for new AI safety fellowships", agent: "Opportunity Monitor", status: "completed", priority: "low", created: "1h ago" },
  { id: "q7", task: "Compile weekly opportunity digest", agent: "Planner Agent", status: "completed", priority: "medium", created: "2h ago" },
  { id: "q8", task: "Update skill vectors in memory", agent: "Memory Layer", status: "failed", priority: "low", created: "3h ago", progress: 88 },
];

const completedItems = queueItems.filter((q) => q.status === "completed");
const failedItems = queueItems.filter((q) => q.status === "failed");

const agentIconMap: Record<string, React.ElementType> = {
  "Planner Agent": Brain,
  "Internship Agent": Target,
  "Job Agent": Zap,
  "Research Agent": FileSearch,
  "Resume Agent": Sparkles,
  "Interview Agent": MessageSquare,
  "Networking Agent": Network,
  "Opportunity Monitor": Bell,
  "Memory Layer": Brain,
};

const priorityConfig = {
  high: { label: "High", className: "bg-destructive/10 text-destructive border-destructive/20" },
  medium: { label: "Med", className: "bg-warning/10 text-warning border-warning/20" },
  low: { label: "Low", className: "bg-muted-foreground/10 text-muted-foreground" },
};

function AgentQueueItem({ item }: { item: QueueItem }) {
  const Icon = agentIconMap[item.agent] || Brain;

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
          <span className="font-medium text-sm">{item.task}</span>
          <Badge variant="outline" className={`text-[10px] ${priorityConfig[item.priority].className}`}>
            {priorityConfig[item.priority].label}
          </Badge>
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
          <span>{item.agent}</span>
          <span>·</span>
          <span>{item.created}</span>
          {item.eta && (
            <>
              <span>·</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" /> ETA {item.eta}
              </span>
            </>
          )}
        </div>
        {item.progress !== undefined && item.status === "running" && (
          <Progress value={item.progress} className="h-1 mt-2" />
        )}
      </div>
      <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition">
        {item.status === "queued" && (
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <Play className="h-3 w-3" />
          </Button>
        )}
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive">
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

export default function TaskQueue() {
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
          <Button variant="outline" className="gap-2">
            <Play className="h-4 w-4" /> Retry Failed
          </Button>
          <Button variant="outline" className="gap-2">
            <Trash2 className="h-4 w-4" /> Clear Completed
          </Button>
        </div>
      </div>

      {/* Queue Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: "Total", value: queueItems.length, icon: Clock, color: "text-foreground" },
          { label: "Queued", value: queueItems.filter((q) => q.status === "queued").length, icon: Clock, color: "text-muted-foreground" },
          { label: "Running", value: queueItems.filter((q) => q.status === "running").length, icon: Loader2, color: "text-primary" },
          { label: "Completed", value: queueItems.filter((q) => q.status === "completed").length, icon: CheckCircle2, color: "text-success" },
          { label: "Failed", value: queueItems.filter((q) => q.status === "failed").length, icon: AlertCircle, color: "text-destructive" },
        ].map((s) => (
          <Card key={s.label} className="glass p-4 text-center">
            <s.icon className={`h-5 w-5 mx-auto mb-1 ${s.color}`} />
            <div className={`text-2xl font-display font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="active">
        <TabsList className="glass">
          <TabsTrigger value="active">Active ({queueItems.filter((q) => q.status !== "completed" && q.status !== "failed").length})</TabsTrigger>
          <TabsTrigger value="completed">Completed ({completedItems.length})</TabsTrigger>
          <TabsTrigger value="failed">Failed ({failedItems.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4 space-y-2">
          {queueItems.filter((q) => q.status === "queued" || q.status === "running").length === 0 ? (
            <div className="text-center py-16">
              <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-success opacity-50" />
              <h3 className="font-display font-semibold text-lg">All caught up</h3>
              <p className="text-sm text-muted-foreground">No active tasks in the queue.</p>
            </div>
          ) : (
            queueItems
              .filter((q) => q.status === "queued" || q.status === "running")
              .sort((a, b) => {
                const order = { high: 0, medium: 1, low: 2 };
                return order[a.priority] - order[b.priority];
              })
              .map((item) => <AgentQueueItem key={item.id} item={item} />)
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-4 space-y-2">
          {completedItems.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <Clock className="h-8 w-8 mx-auto mb-2 opacity-40" />
              No completed tasks yet.
            </div>
          ) : (
            completedItems.map((item) => <AgentQueueItem key={item.id} item={item} />)
          )}
        </TabsContent>

        <TabsContent value="failed" className="mt-4 space-y-2">
          {failedItems.length === 0 ? (
            <div className="text-center py-16">
              <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-success opacity-50" />
              <h3 className="font-display font-semibold text-lg">Zero failures</h3>
              <p className="text-sm text-muted-foreground">All tasks completed successfully.</p>
            </div>
          ) : (
            failedItems.map((item) => (
              <div key={item.id}>
                <AgentQueueItem item={item} />
                <div className="ml-12 mt-1 p-3 rounded-lg bg-destructive/5 border border-destructive/10 text-xs text-destructive/80 font-mono">
                  Error: Agent timeout after 60s. Task exceeded expected duration. Retry recommended.
                </div>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
