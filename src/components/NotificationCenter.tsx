import { useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { useAgentTasks } from "@/api/hooks";
import { formatDistanceToNow } from "date-fns";
import type { AgentTask } from "@/api/client";

function taskToNotification(task: AgentTask) {
  const time = formatDistanceToNow(new Date(task.created_at), { addSuffix: true });
  switch (task.status) {
    case "completed":
      return { id: task.id, title: `${task.agent_type} completed`, body: "Task finished successfully", time, type: "success" as const };
    case "failed":
      return { id: task.id, title: `${task.agent_type} failed`, body: task.error || "Task encountered an error", time, type: "error" as const };
    default:
      return { id: task.id, title: `${task.agent_type} running`, body: "Task is in progress", time, type: "info" as const };
  }
}

const dotColor = {
  success: "bg-emerald-500",
  error: "bg-destructive",
  info: "bg-primary",
};

export function NotificationCenter() {
  const { data } = useAgentTasks();
  const [readIds, setReadIds] = useState<Set<string>>(new Set());

  const tasks = data?.items ?? [];
  const notifications = tasks.map(taskToNotification);
  const unread = notifications.filter(n => !readIds.has(n.id));

  const markAllRead = () => {
    setReadIds(new Set(notifications.map(n => n.id)));
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative rounded-full">
          <Bell className="h-[1.1rem] w-[1.1rem]" />
          {unread.length > 0 && (
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0 glass" align="end">
        <div className="flex items-center justify-between p-4 border-b border-border/50">
          <div className="font-display font-semibold">Notifications</div>
          <Badge variant="secondary" className="text-xs">{unread.length} new</Badge>
        </div>
        <div className="max-h-96 overflow-y-auto scrollbar-thin">
          {notifications.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">No new notifications</div>
          ) : (
            notifications.map((n) => (
              <div key={n.id} className="p-4 border-b border-border/30 last:border-0 hover:bg-muted/50 cursor-pointer transition">
                <div className="flex items-start gap-3">
                  {!readIds.has(n.id) && <span className={`h-2 w-2 rounded-full mt-1.5 ${dotColor[n.type]}`} />}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{n.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{n.body}</div>
                    <div className="text-[10px] text-muted-foreground mt-1">{n.time}</div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="p-2 border-t border-border/50">
          <Button variant="ghost" size="sm" className="w-full text-xs gap-1.5" onClick={markAllRead} disabled={unread.length === 0}>
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all as read
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
