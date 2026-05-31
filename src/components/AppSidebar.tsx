import {
  LayoutDashboard, Briefcase, Kanban, FileText, MessageSquare,
  Building2, Users, BarChart3, Settings, Sparkles, Bell,
  Cpu, ListOrdered, Database,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarGroupLabel,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarHeader, SidebarFooter,
} from "@/components/ui/sidebar";

const mainNav = [
  { title: "Dashboard", url: "/app", icon: LayoutDashboard },
  { title: "Opportunities", url: "/app/opportunities", icon: Briefcase },
  { title: "Applications", url: "/app/applications", icon: Kanban },
  { title: "Resume Studio", url: "/app/resume", icon: FileText },
  { title: "Interview Prep", url: "/app/interview", icon: MessageSquare },
  { title: "Career Coach", url: "/app/coach", icon: Sparkles },
];

const intelligenceNav = [
  { title: "Research Center", url: "/app/research", icon: Building2 },
  { title: "Networking Hub", url: "/app/networking", icon: Users },
  { title: "Opportunity Monitor", url: "/app/monitor", icon: Bell },
  { title: "Agent Console", url: "/app/agents", icon: Cpu },
  { title: "Task Queue", url: "/app/tasks", icon: ListOrdered },
  { title: "Memory Viewer", url: "/app/memory", icon: Database },
  { title: "Analytics", url: "/app/analytics", icon: BarChart3 },
];

export function AppSidebar() {
  const { pathname } = useLocation();
  const isActive = (url: string) => pathname === url;

  const renderItem = (item: typeof mainNav[number]) => (
    <SidebarMenuItem key={item.title}>
      <SidebarMenuButton asChild isActive={isActive(item.url)}>
        <NavLink to={item.url} end className="flex items-center gap-3">
          <item.icon className="h-4 w-4" />
          <span>{item.title}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <NavLink to="/app" className="flex items-center gap-2 px-2 py-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-primary shadow-glow">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="font-display font-bold text-sm leading-none">AgentForge</span>
            <span className="text-[10px] text-muted-foreground">Career OS</span>
          </div>
        </NavLink>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>{mainNav.map(renderItem)}</SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Intelligence</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>{intelligenceNav.map(renderItem)}</SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={isActive("/app/settings")}>
              <NavLink to="/app/settings" className="flex items-center gap-3">
                <Settings className="h-4 w-4" />
                <span>Settings</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
