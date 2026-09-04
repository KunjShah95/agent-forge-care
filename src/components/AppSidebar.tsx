import {
  LayoutDashboard,
  Briefcase,
  Kanban,
  FileText,
  MessageSquare,
  Building2,
  Users,
  BarChart3,
  Settings,
  Sparkles,
  Bell,
  Cpu,
  ListOrdered,
  Database,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import { useNotifications } from "@/api/hooks";

const MUTED = "hsl(240, 4%, 55%)";
const BORDER = "rgba(255,255,255,0.07)";

interface NavEntry {
  title: string;
  url: string;
  icon: typeof LayoutDashboard;
  badge?: number;
}

/* Ordered by daily use: hunt → prepare → intel → system internals last. */
const jobHuntNav = [
  { title: "Dashboard", url: "/app", icon: LayoutDashboard },
  { title: "Opportunities", url: "/app/opportunities", icon: Briefcase },
  { title: "Applications", url: "/app/applications", icon: Kanban },
];

const prepareNav = [
  { title: "Resume Studio", url: "/app/resume", icon: FileText },
  { title: "Interview", url: "/app/interview", icon: MessageSquare },
  { title: "Career Coach", url: "/app/coach", icon: Sparkles },
];

const intelNav = [
  { title: "Research", url: "/app/research", icon: Building2 },
  { title: "Networking", url: "/app/networking", icon: Users },
  { title: "Monitor", url: "/app/monitor", icon: Bell },
  { title: "Analytics", url: "/app/analytics", icon: BarChart3 },
];

const systemNav = [
  { title: "Agent Console", url: "/app/agents", icon: Cpu },
  { title: "Task Queue", url: "/app/tasks", icon: ListOrdered },
  { title: "Memory", url: "/app/memory", icon: Database },
];

function NavItem({ item }: { item: NavEntry }) {
  const { pathname } = useLocation();
  const { isMobile, setOpenMobile } = useSidebar();
  // Stay highlighted on nested routes (e.g. /app/opportunities/123).
  const active = pathname === item.url || (item.url !== "/app" && pathname.startsWith(item.url + "/"));

  return (
    <SidebarMenuItem>
      <NavLink
        to={item.url}
        end={item.url === "/app"}
        title={item.title}
        aria-current={active ? "page" : undefined}
        onClick={() => {
          if (isMobile) setOpenMobile(false);
        }}
        className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors duration-150 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
        style={{
          color: active ? "white" : MUTED,
          background: active ? "rgba(255,255,255,0.07)" : "transparent",
          fontWeight: active ? 500 : 400,
        }}
      >
        <item.icon className="h-3.5 w-3.5 flex-shrink-0" style={{ opacity: active ? 1 : 0.6 }} />
        <span className="truncate group-data-[collapsible=icon]:hidden">{item.title}</span>
        {typeof item.badge === "number" && item.badge > 0 && (
          <span
            className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-md px-1 text-[11px] font-medium tabular-nums group-data-[collapsible=icon]:hidden"
            style={{ background: "rgba(255,255,255,0.1)", color: "white" }}
          >
            {item.badge > 99 ? "99+" : item.badge}
          </span>
        )}
      </NavLink>
    </SidebarMenuItem>
  );
}

function NavGroup({ label, items }: { label: string; items: NavEntry[] }) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel
        className="px-3 mb-1 text-[10px] tracking-widest uppercase"
        style={{ color: "rgba(255,255,255,0.25)" }}
      >
        {label}
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu className="gap-0.5">
          {items.map((item) => (
            <NavItem key={item.url} item={item} />
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar() {
  const { data: notifications } = useNotifications();
  const unread = (notifications?.items ?? []).filter((n) => !n.read).length;

  const intel: NavEntry[] = intelNav.map((i) =>
    i.url === "/app/monitor" ? { ...i, badge: unread } : i,
  );

  return (
    <Sidebar
      collapsible="icon"
      className="dark border-r"
      style={{ borderColor: BORDER, background: "hsl(210, 25%, 5%)" }}
    >
      {/* Logo */}
      <SidebarHeader style={{ borderBottom: `1px solid ${BORDER}`, padding: "16px 12px" }}>
        <NavLink to="/app" title="CareerOS home" className="flex items-center gap-2.5 px-1 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <div
            className="h-7 w-7 rounded flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(255,255,255,0.08)", border: `1px solid ${BORDER}` }}
          >
            <Sparkles className="h-3.5 w-3.5" style={{ color: "white" }} />
          </div>
          <div className="flex flex-col leading-none group-data-[collapsible=icon]:hidden">
            <span
              className="text-sm text-white"
              style={{ fontFamily: "'Instrument Serif', serif", letterSpacing: "-0.02em" }}
            >
              CareerOS
            </span>
            <span className="text-[10px] mt-0.5" style={{ color: MUTED }}>
              Your career team
            </span>
          </div>
        </NavLink>
      </SidebarHeader>

      <SidebarContent className="px-2 py-3">
        <NavGroup label="Job hunt" items={jobHuntNav} />
        <div className="mt-4">
          <NavGroup label="Prepare" items={prepareNav} />
        </div>
        <div className="mt-4">
          <NavGroup label="Intelligence" items={intel} />
        </div>
        <div className="mt-4">
          <NavGroup label="System" items={systemNav} />
        </div>
      </SidebarContent>

      <SidebarFooter style={{ borderTop: `1px solid ${BORDER}`, padding: "8px" }}>
        <NavLink
          to="/app/settings"
          title="Settings"
          className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors duration-150 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
          style={({ isActive }) => ({
            color: isActive ? "white" : MUTED,
            background: isActive ? "rgba(255,255,255,0.07)" : "transparent",
          })}
        >
          <Settings className="h-3.5 w-3.5 flex-shrink-0" style={{ opacity: 0.6 }} />
          <span className="group-data-[collapsible=icon]:hidden">Settings</span>
        </NavLink>
      </SidebarFooter>
    </Sidebar>
  );
}
