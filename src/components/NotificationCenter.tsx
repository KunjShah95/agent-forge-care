import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { useNotifications, useMarkNotificationRead, useMarkAllNotificationsRead } from "@/api/hooks";
import { formatDistanceToNow } from "date-fns";

const dotColor = {
  success: "bg-emerald-500",
  error: "bg-destructive",
  info: "bg-primary",
};

export function NotificationCenter() {
  const { data } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const notifications = data?.items ?? [];
  const unread = notifications.filter(n => !n.read);

  const handleMarkAllRead = () => {
    markAllRead.mutate();
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
              <div
                key={n.id}
                className="p-4 border-b border-border/30 last:border-0 hover:bg-muted/50 cursor-pointer transition"
                onClick={() => { if (!n.read) markRead.mutate(n.id); }}
              >
                <div className="flex items-start gap-3">
                  {!n.read && <span className={`h-2 w-2 rounded-full mt-1.5 ${dotColor[n.type]}`} />}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{n.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{n.body}</div>
                    <div className="text-[10px] text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="p-2 border-t border-border/50">
          <Button variant="ghost" size="sm" className="w-full text-xs gap-1.5" onClick={handleMarkAllRead} disabled={unread.length === 0}>
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all as read
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
