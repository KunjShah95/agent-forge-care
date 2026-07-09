import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { CommandPalette } from "./CommandPalette";
import { NotificationCenter } from "./NotificationCenter";
import { useState, useEffect } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/api/hooks";
import { useAuthContext } from "@/lib/auth-context";
import { Link } from "react-router-dom";
import { Settings, LogOut, Search } from "lucide-react";

const BORDER = "rgba(255,255,255,0.08)";
const MUTED = "hsl(240, 4%, 60%)";

export default function AppLayout() {
  const [cmdOpen, setCmdOpen] = useState(false);
  const { data: user } = useAuth();
  const { logout } = useAuthContext();

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((w: string) => w[0])
        .filter(Boolean)
        .slice(0, 2)
        .join("")
        .toUpperCase()
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
      <div
        className="dark min-h-screen flex w-full"
        style={{ background: "hsl(210, 25%, 6%)", color: "white" }}
      >
        <AppSidebar />

        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <header
            className="h-12 flex items-center gap-3 px-5 sticky top-0 z-30"
            style={{
              background: "hsl(210, 25%, 6%)",
              borderBottom: `1px solid ${BORDER}`,
            }}
          >
            <SidebarTrigger
              className="text-white/40 hover:text-white transition-colors"
              style={{ color: MUTED }}
            />

            {/* Search trigger */}
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs transition-colors"
              style={{
                color: MUTED,
                background: "rgba(255,255,255,0.04)",
                border: `1px solid ${BORDER}`,
              }}
            >
              <Search className="h-3.5 w-3.5" />
              <span>Search…</span>
              <kbd
                className="ml-6 font-mono text-[10px] px-1.5 py-0.5 rounded"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  color: MUTED,
                  border: `1px solid ${BORDER}`,
                }}
              >
                ⌘K
              </kbd>
            </button>

            <div className="ml-auto flex items-center gap-2">
              <NotificationCenter />

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Avatar
                    className="h-7 w-7 cursor-pointer"
                    style={{ border: `1px solid ${BORDER}` }}
                  >
                    <AvatarFallback
                      className="text-[11px] font-medium"
                      style={{
                        background: "rgba(255,255,255,0.08)",
                        color: "white",
                      }}
                    >
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="w-48 dark"
                  style={{
                    background: "hsl(210, 22%, 8%)",
                    border: `1px solid ${BORDER}`,
                  }}
                >
                  <div className="px-3 py-2 text-sm font-medium text-white">
                    {user?.full_name || user?.email || "User"}
                  </div>
                  <div className="px-3 pb-2 text-xs" style={{ color: MUTED }}>
                    {user?.email}
                  </div>
                  <DropdownMenuSeparator style={{ background: BORDER }} />
                  <DropdownMenuItem asChild>
                    <Link
                      to="/app/settings"
                      className="flex items-center gap-2 text-sm cursor-pointer"
                      style={{ color: MUTED }}
                    >
                      <Settings className="h-3.5 w-3.5" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator style={{ background: BORDER }} />
                  <DropdownMenuItem
                    onClick={() => logout()}
                    className="flex items-center gap-2 text-sm cursor-pointer text-red-400"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          {/* Page content */}
          <main className="flex-1 overflow-x-hidden">
            <Outlet />
          </main>
        </div>

        <CommandPalette open={cmdOpen} setOpen={setCmdOpen} />
      </div>
    </SidebarProvider>
  );
}
