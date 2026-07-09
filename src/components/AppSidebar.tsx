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
} from "@/components/ui/sidebar";

const MUTED = "hsl(240, 4%, 55%)";
const BORDER = "rgba(255,255,255,0.07)";

const mainNav = [
  { title: "Dashboard",    url: "/app",              icon: LayoutDashboard },
  { title: "Opportunities",url: "/app/opportunities", icon: Briefcase },
  { title: "Applications", url: "/app/applications",  icon: Kanban },
  { title: "Resume Studio",url: "/app/resume",        icon: FileText },
  { title: "Interview",    url: "/app/interview",     icon: MessageSquare },
  { title: "Career Coach", url: "/app/coach",         icon: Sparkles },
];

const intelNav = [
  { title: "Research",     url: "/app/research",    icon: Building2 },
  { title: "Networking",   url: "/app/networking",  icon: Users },
  { title: "Monitor",      url: "/app/monitor",     icon: Bell },
  { title: "Agent Console",url: "/app/agents",      icon: Cpu },
  { title: "Task Queue",   url: "/app/tasks",       icon: ListOrdered },
  { title: "Memory",       url: "/app/memory",      icon: Database },
  { title: "Analytics",    url: "/app/analytics",   icon: BarChart3 },
];

export function AppSidebar() {
  const { pathname } = useLocation();

  const NavItem = ({ item }: { item: (typeof mainNav)[number] }) => {
    const active = pathname === item.url;
    return (
      <SidebarMenuItem>
        <NavLink
          to={item.url}
          end
          className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors duration-150"
          style={({ isActive }) => ({
            color: isActive ? "white" : MUTED,
            background: isActive ? "rgba(255,255,255,0.07)" : "transparent",
            fontWeight: isActive ? 500 : 400,
          })}
        >
          <item.icon
            className="h-3.5 w-3.5 flex-shrink-0"
            style={{ opacity: active ? 1 : 0.6 }}
          />
          <span>{item.title}</span>
        </NavLink>
      </SidebarMenuItem>
    );
  };

  return (
    <Sidebar
      collapsible="icon"
      className="dark border-r"
      style={{ borderColor: BORDER, background: "hsl(210, 25%, 5%)" }}
    >
      {/* Logo */}
      <SidebarHeader style={{ borderBottom: `1px solid ${BORDER}`, padding: "16px 12px" }}>
        <NavLink to="/app" className="flex items-center gap-2.5 px-1">
          <div
            className="h-7 w-7 rounded flex items-center justify-center flex-shrink-0"
            style={{ background: "rgba(255,255,255,0.08)", border: `1px solid ${BORDER}` }}
          >
            <Sparkles className="h-3.5 w-3.5" style={{ color: "white" }} />
          </div>
          <div className="flex flex-col leading-none">
            <span
              className="text-sm text-white"
              style={{ fontFamily: "'Instrument Serif', serif", letterSpacing: "-0.02em" }}
            >
              Velorah
            </span>
            <span className="text-[10px] mt-0.5" style={{ color: MUTED }}>
              Career OS
            </span>
          </div>
        </NavLink>
      </SidebarHeader>

      <SidebarContent className="px-2 py-3">
        {/* Workspace */}
        <SidebarGroup>
          <SidebarGroupLabel
            className="px-3 mb-1 text-[10px] tracking-widest uppercase"
            style={{ color: "rgba(255,255,255,0.25)" }}
          >
            Workspace
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-0.5">
              {mainNav.map((item) => (
                <NavItem key={item.url} item={item} />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Intelligence */}
        <SidebarGroup className="mt-4">
          <SidebarGroupLabel
            className="px-3 mb-1 text-[10px] tracking-widest uppercase"
            style={{ color: "rgba(255,255,255,0.25)" }}
          >
            Intelligence
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-0.5">
              {intelNav.map((item) => (
                <NavItem key={item.url} item={item} />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter style={{ borderTop: `1px solid ${BORDER}`, padding: "8px" }}>
        <NavLink
          to="/app/settings"
          className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors duration-150"
          style={({ isActive }) => ({
            color: isActive ? "white" : MUTED,
            background: isActive ? "rgba(255,255,255,0.07)" : "transparent",
          })}
        >
          <Settings className="h-3.5 w-3.5 flex-shrink-0" style={{ opacity: 0.6 }} />
          <span>Settings</span>
        </NavLink>
      </SidebarFooter>
    </Sidebar>
  );
}
