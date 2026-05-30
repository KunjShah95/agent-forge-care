import {
  CommandDialog, CommandEmpty, CommandGroup, CommandInput,
  CommandItem, CommandList, CommandSeparator,
} from "@/components/ui/command";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Briefcase, Kanban, FileText, MessageSquare,
  Building2, Users, Bell, BarChart3, Settings, Sparkles, Plus,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", url: "/app", icon: LayoutDashboard },
  { label: "Opportunities", url: "/app/opportunities", icon: Briefcase },
  { label: "Applications", url: "/app/applications", icon: Kanban },
  { label: "Resume Studio", url: "/app/resume", icon: FileText },
  { label: "Interview Prep", url: "/app/interview", icon: MessageSquare },
  { label: "Research Center", url: "/app/research", icon: Building2 },
  { label: "Networking Hub", url: "/app/networking", icon: Users },
  { label: "Opportunity Monitor", url: "/app/monitor", icon: Bell },
  { label: "Analytics", url: "/app/analytics", icon: BarChart3 },
  { label: "Settings", url: "/app/settings", icon: Settings },
];

export function CommandPalette({ open, setOpen }: { open: boolean; setOpen: (o: boolean) => void }) {
  const navigate = useNavigate();
  const go = (url: string) => { setOpen(false); navigate(url); };
  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Quick Actions">
          <CommandItem onSelect={() => go("/app/agents")}>
            <Sparkles className="mr-2 h-4 w-4" /> Run scan
          </CommandItem>
          <CommandItem onSelect={() => go("/app/applications")}>
            <Plus className="mr-2 h-4 w-4" /> Add application
          </CommandItem>
          <CommandItem onSelect={() => go("/app/resume")}>
            <FileText className="mr-2 h-4 w-4" /> Tailor resume with AI
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Navigation">
          {navItems.map((item) => (
            <CommandItem key={item.url} onSelect={() => go(item.url)}>
              <item.icon className="mr-2 h-4 w-4" /> {item.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
