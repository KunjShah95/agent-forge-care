import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Mail, Plus, Search, Send, Sparkles } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";

import { useContacts, useCreateContact } from "@/api/hooks";
import { ListSkeleton } from "@/components/ui/skeleton";

const templates = [
  { name: "Cold outreach — recruiter", preview: "Hi {Name}, I came across {Company}'s {Role} posting and your work on {Topic}…" },
  { name: "Coffee chat request", preview: "Hi {Name}, I'm exploring opportunities in {Industry} and would love 15 minutes…" },
  { name: "Post-interview thank you", preview: "Thanks for taking the time today. Our discussion on {Topic} reinforced why {Company}…" },
  { name: "Networking follow-up", preview: "Great connecting at {Event}! As promised, here's the article on {Topic}…" },
];

const statusColors: Record<string, string> = {
  New: "bg-muted text-muted-foreground",
  "Reached out": "bg-blue-500/10 text-blue-500",
  Replied: "bg-success/10 text-success",
  Meeting: "bg-primary/10 text-primary",
  Closed: "bg-muted-foreground/20 text-muted-foreground",
};

function initials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function NetworkingHub() {
  const navigate = useNavigate();
  const { data, isLoading } = useContacts();
  const createContact = useCreateContact();
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [newCompany, setNewCompany] = useState("");
  const [newEmail, setNewEmail] = useState("");

  const contacts = useMemo(() => {
    const items = data?.items || [];
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.company || "").toLowerCase().includes(q) ||
        (c.role || "").toLowerCase().includes(q),
    );
  }, [data, searchQuery]);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Networking Hub</h1>
          <p className="text-muted-foreground mt-1">Track recruiters, draft outreach, manage relationships.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => setDialogOpen(true)}><Plus className="h-4 w-4" /> Add contact</Button>
          <Button className="bg-gradient-primary shadow-glow gap-2" onClick={() => navigate("/app/agents")}><Sparkles className="h-4 w-4" /> Draft outreach</Button>
        </div>
      </div>

      <Tabs defaultValue="contacts">
        <TabsList className="glass">
          <TabsTrigger value="contacts">Contacts ({!isLoading ? contacts.length : "…"})</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="contacts" className="mt-4">
          <Card className="glass overflow-hidden">
            <div className="p-4 border-b border-border/50 flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search contacts…"
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
            {isLoading ? (
              <div className="p-4">
                <ListSkeleton count={4} />
              </div>
            ) : contacts.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                No contacts yet. Start building your network!
              </div>
            ) : (
              <div className="divide-y divide-border/50">
                {contacts.map((c) => (
                  <div key={c.id} className="p-4 flex items-center gap-4 hover:bg-muted/30 transition">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-gradient-primary text-primary-foreground text-xs">
                        {initials(c.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium">{c.name}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        {[c.role, c.company].filter(Boolean).join(" · ") || "—"}
                      </div>
                    </div>
                    <div className="hidden md:block text-xs text-muted-foreground">{c.email}</div>
                    <Badge className={`${statusColors[c.status] || ""} text-[10px]`} variant="outline">{c.status}</Badge>
                    <div className="text-xs text-muted-foreground w-16 text-right">{c.last_contact || "—"}</div>
                    <Button variant="ghost" size="icon" onClick={() => navigate("/app/agents")}><Mail className="h-4 w-4" /></Button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="templates" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4">
            {templates.map((t) => (
              <Card key={t.name} className="glass p-5 hover:shadow-glow transition">
                <div className="font-display font-semibold mb-2">{t.name}</div>
                <p className="text-xs text-muted-foreground font-mono mb-4 line-clamp-3">{t.preview}</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">Edit</Button>
                  <Button size="sm" className="bg-gradient-primary gap-1"><Send className="h-3 w-3" /> Use</Button>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="glass">
          <DialogHeader>
            <DialogTitle className="font-display">Add Contact</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input className="mt-1.5" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Jane Doe" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Role</Label>
                <Input className="mt-1.5" value={newRole} onChange={(e) => setNewRole(e.target.value)} placeholder="Recruiter" />
              </div>
              <div>
                <Label>Company</Label>
                <Input className="mt-1.5" value={newCompany} onChange={(e) => setNewCompany(e.target.value)} placeholder="Acme Inc" />
              </div>
            </div>
            <div>
              <Label>Email</Label>
              <Input className="mt-1.5" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="jane@acme.com" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              className="bg-gradient-primary"
              disabled={!newName.trim() || createContact.isPending}
              onClick={() => {
                createContact.mutate(
                  { name: newName, role: newRole || undefined, company: newCompany || undefined, email: newEmail || undefined },
                  {
                    onSuccess: () => {
                      toast.success("Contact added");
                      setDialogOpen(false);
                      setNewName("");
                      setNewRole("");
                      setNewCompany("");
                      setNewEmail("");
                    },
                    onError: () => toast.error("Failed to add contact"),
                  },
                );
              }}
            >
              {createContact.isPending ? "Adding…" : "Add"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
