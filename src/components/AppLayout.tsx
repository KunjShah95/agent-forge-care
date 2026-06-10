import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { ThemeToggle } from "./ThemeToggle";
import { CommandPalette } from "./CommandPalette";
import { NotificationCenter } from "./NotificationCenter";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";
import { useState, useEffect } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/api/hooks";

export default function AppLayout() {
  const [cmdOpen, setCmdOpen] = useState(false);
  const { data: user } = useAuth();
  const initials = user?.full_name
    ? user.full_name.split(" ").map((w) => w[0]).filter(Boolean).slice(0, 2).join("").toUpperCase()
    : "?";

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCmdOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full mesh-bg">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-14 flex items-center gap-3 border-b border-border/40 px-4 backdrop-blur-xl bg-background/70 sticky top-0 z-30">
            <SidebarTrigger />
            <Button
              variant="outline"
              size="sm"
              className="gap-2 text-muted-foreground w-72 justify-start glass"
              onClick={() => setCmdOpen(true)}
            >
              <Search className="h-4 w-4" />
              <span className="text-xs">Search opportunities, contacts, actions…</span>
              <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium">
                ⌘K
              </kbd>
            </Button>
            <div className="ml-auto flex items-center gap-1">
              <NotificationCenter />
              <ThemeToggle />
              <Avatar className="h-8 w-8 ml-2 border-2 border-primary/30">
                <AvatarFallback className="bg-gradient-1 text-primary-foreground text-xs font-semibold">{initials}</AvatarFallback>
              </Avatar>
            </div>
          </header>
          <main className="flex-1 p-6 animate-fade-in overflow-x-hidden">
            <Outlet />
          </main>
        </div>
        <CommandPalette open={cmdOpen} setOpen={setCmdOpen} />
      </div>
    </SidebarProvider>
  );
}
