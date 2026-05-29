import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";

const notifications = [
  { id: 1, title: "Stripe OA due in 2 days", body: "Complete coding assessment by Dec 8", time: "5m ago", unread: true },
  { id: 2, title: "New 96% match found", body: "Anthropic ML Research Intern", time: "1h ago", unread: true },
  { id: 3, title: "Daniel @ Linear replied", body: "Wants to schedule a chat next week", time: "3h ago", unread: true },
  { id: 4, title: "Resume tailored", body: "Resume Agent finished v3 for Vercel", time: "Yesterday", unread: false },
  { id: 5, title: "Daily digest ready", body: "12 new matches across your filters", time: "Yesterday", unread: false },
];

export function NotificationCenter() {
  const unread = notifications.filter(n => n.unread).length;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative rounded-full">
          <Bell className="h-[1.1rem] w-[1.1rem]" />
          {unread > 0 && (
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0 glass" align="end">
        <div className="flex items-center justify-between p-4 border-b border-border/50">
          <div className="font-display font-semibold">Notifications</div>
          <Badge variant="secondary" className="text-xs">{unread} new</Badge>
        </div>
        <div className="max-h-96 overflow-y-auto scrollbar-thin">
          {notifications.map((n) => (
            <div key={n.id} className="p-4 border-b border-border/30 last:border-0 hover:bg-muted/50 cursor-pointer transition">
              <div className="flex items-start gap-3">
                {n.unread && <span className="h-2 w-2 rounded-full bg-primary mt-1.5" />}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{n.title}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{n.body}</div>
                  <div className="text-[10px] text-muted-foreground mt-1">{n.time}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="p-2 border-t border-border/50">
          <Button variant="ghost" size="sm" className="w-full text-xs">Mark all as read</Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
