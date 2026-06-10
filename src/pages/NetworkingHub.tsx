import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Mail, Plus, Search, Send, Sparkles, Trash2, Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

import { useContacts, useCreateContact, useUpdateContact, useDeleteContact, useNetworkingOutreach } from "@/api/hooks";
import { ListSkeleton } from "@/components/ui/skeleton";
import {
  Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious,
} from "@/components/ui/pagination";

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

const ITEMS_PER_PAGE = 12;

export default function NetworkingHub() {
  const navigate = useNavigate();
  const { data, isLoading } = useContacts();
  const createContact = useCreateContact();
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [newCompany, setNewCompany] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newLinkedin, setNewLinkedin] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [newStatus, setNewStatus] = useState("New");

  const updateContact = useUpdateContact();
  const deleteContact = useDeleteContact();
  const outreach = useNetworkingOutreach();
  const [outreachDialogOpen, setOutreachDialogOpen] = useState(false);
  const [outreachTargets, setOutreachTargets] = useState("");
  const [outreachRole, setOutreachRole] = useState("");
  const [outreachResult, setOutreachResult] = useState<{ templates: { type: string; subject: string; message: string }[]; best_practices: string[] } | null>(null);

  const resetForm = () => {
    setNewName("");
    setNewRole("");
    setNewCompany("");
    setNewEmail("");
    setNewLinkedin("");
    setNewNotes("");
    setNewStatus("New");
    setEditingId(null);
  };

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

  const totalPages = Math.max(1, Math.ceil(contacts.length / ITEMS_PER_PAGE));
  const paginatedContacts = contacts.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [contacts.length, totalPages]);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Networking Hub</h1>
          <p className="text-muted-foreground mt-1">Track recruiters, draft outreach, manage relationships.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => { resetForm(); setDialogOpen(true); }}><Plus className="h-4 w-4" /> Add contact</Button>
          <Button className="bg-gradient-1 shadow-glow gap-2" onClick={() => { setOutreachDialogOpen(true); setOutreachResult(null); }}><Sparkles className="h-4 w-4" /> Draft outreach</Button>
        </div>
      </div>

      <Tabs defaultValue="contacts">
        <TabsList className="glass-strong">
          <TabsTrigger value="contacts">Contacts ({!isLoading ? contacts.length : "…"})</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="contacts" className="mt-4">
          <Card className="glass-strong overflow-hidden">
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
                {paginatedContacts.map((c) => (
                  <div
                    key={c.id}
                    className="p-4 flex items-center gap-4 hover:bg-muted/30 transition cursor-pointer"
                    onClick={() => {
                      setEditingId(c.id);
                      setNewName(c.name);
                      setNewRole(c.role || "");
                      setNewCompany(c.company || "");
                      setNewEmail(c.email || "");
                      setNewLinkedin(c.linkedin_url || "");
                      setNewNotes(c.notes || "");
                      setNewStatus(c.status);
                      setDialogOpen(true);
                    }}
                  >
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-gradient-1 text-primary-foreground text-xs">
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
                    <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); window.open(`mailto:${c.email}`, "_blank"); }}><Mail className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={(e) => {
                      e.stopPropagation();
                      deleteContact.mutate(c.id, {
                        onSuccess: () => toast.success("Contact deleted"),
                        onError: () => toast.error("Failed to delete contact"),
                      });
                    }}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border/50">
              <span className="text-xs text-muted-foreground">
                Showing {Math.min((page - 1) * ITEMS_PER_PAGE + 1, contacts.length)}–{Math.min(page * ITEMS_PER_PAGE, contacts.length)} of {contacts.length} contacts
              </span>
              <Pagination className="w-auto mx-0">
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    let pageNum: number;
                    if (totalPages <= 7) {
                      pageNum = i + 1;
                    } else if (page <= 4) {
                      pageNum = i + 1;
                    } else if (page >= totalPages - 3) {
                      pageNum = totalPages - 6 + i;
                    } else {
                      pageNum = page - 3 + i;
                    }
                    return (
                      <PaginationItem key={pageNum}>
                        <PaginationLink
                          isActive={pageNum === page}
                          onClick={() => setPage(pageNum)}
                          className="cursor-pointer"
                        >
                          {pageNum}
                        </PaginationLink>
                      </PaginationItem>
                    );
                  })}
                  <PaginationItem>
                    <PaginationNext
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </TabsContent>

        <TabsContent value="templates" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4">
            {templates.map((t) => (
              <Card key={t.name} className="glass-strong p-5 hover:shadow-glow transition">
                <div className="font-display font-semibold mb-2">{t.name}</div>
                <p className="text-xs text-muted-foreground font-mono mb-4 line-clamp-3">{t.preview}</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">Edit</Button>
                  <Button size="sm" className="bg-gradient-1 gap-1"><Send className="h-3 w-3" /> Use</Button>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) { setDialogOpen(false); resetForm(); } }}>
        <DialogContent className="glass-strong">
          <DialogHeader>
            <DialogTitle className="font-display">{editingId ? "Edit Contact" : "Add Contact"}</DialogTitle>
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
            <div>
              <Label>LinkedIn URL</Label>
              <Input className="mt-1.5" value={newLinkedin} onChange={(e) => setNewLinkedin(e.target.value)} placeholder="https://linkedin.com/in/..." />
            </div>
            <div>
              <Label>Notes</Label>
              <Input className="mt-1.5" value={newNotes} onChange={(e) => setNewNotes(e.target.value)} placeholder="Any notes..." />
            </div>
            <div>
              <Label>Status</Label>
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(statusColors).map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            {editingId && (
              <Button variant="destructive" onClick={() => {
                deleteContact.mutate(editingId, {
                  onSuccess: () => { toast.success("Contact deleted"); setDialogOpen(false); resetForm(); },
                  onError: () => toast.error("Failed to delete contact"),
                });
              }} disabled={deleteContact.isPending}>
                {deleteContact.isPending ? "Deleting…" : "Delete"}
              </Button>
            )}
            <Button variant="outline" onClick={() => { setDialogOpen(false); resetForm(); }}>Cancel</Button>
            <Button
              className="bg-gradient-1"
              disabled={!newName.trim() || createContact.isPending || updateContact.isPending}
              onClick={() => {
                const data = {
                  name: newName,
                  role: newRole || undefined,
                  company: newCompany || undefined,
                  email: newEmail || undefined,
                  linkedin_url: newLinkedin || undefined,
                  notes: newNotes || undefined,
                  status: newStatus,
                };
                if (editingId) {
                  updateContact.mutate(
                    { id: editingId, data },
                    {
                      onSuccess: () => { toast.success("Contact updated"); setDialogOpen(false); resetForm(); },
                      onError: () => toast.error("Failed to update contact"),
                    },
                  );
                } else {
                  createContact.mutate(
                    data,
                    {
                      onSuccess: () => { toast.success("Contact added"); setDialogOpen(false); resetForm(); },
                      onError: () => toast.error("Failed to add contact"),
                    },
                  );
                }
              }}
            >
              {editingId
                ? (updateContact.isPending ? "Saving…" : "Save")
                : (createContact.isPending ? "Adding…" : "Add")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={outreachDialogOpen} onOpenChange={(open) => { if (!open) { setOutreachDialogOpen(false); setOutreachResult(null); } }}>
        <DialogContent className="glass-strong max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-display">Draft AI Outreach</DialogTitle>
          </DialogHeader>
          {!outreachResult ? (
            <div className="space-y-4">
              <div>
                <Label>Target Companies (comma-separated)</Label>
                <Input
                  className="mt-1.5"
                  placeholder="e.g. Stripe, Anthropic, Vercel"
                  value={outreachTargets}
                  onChange={(e) => setOutreachTargets(e.target.value)}
                />
              </div>
              <div>
                <Label>Target Role</Label>
                <Input
                  className="mt-1.5"
                  placeholder="e.g. Software Engineer"
                  value={outreachRole}
                  onChange={(e) => setOutreachRole(e.target.value)}
                />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOutreachDialogOpen(false)}>Cancel</Button>
                <Button
                  className="bg-gradient-1 shadow-glow gap-2"
                  disabled={!outreachTargets.trim() || outreach.isPending}
                  onClick={async () => {
                    try {
                      const targets = outreachTargets.split(",").map((s) => s.trim()).filter(Boolean);
                      const result = await outreach.mutateAsync({
                        target_companies: targets,
                        role: outreachRole || undefined,
                      });
                      setOutreachResult(result);
                      toast.success("Outreach templates generated!");
                    } catch {
                      toast.error("Failed to generate outreach");
                    }
                  }}
                >
                  {outreach.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  Generate
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {outreachResult.templates.map((t, i) => (
                <Card key={i} className="p-4 bg-muted/20">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="outline">{t.type.replace("_", " ")}</Badge>
                    {t.subject && <span className="text-xs font-medium">{t.subject}</span>}
                  </div>
                  <p className="text-xs text-muted-foreground whitespace-pre-wrap font-mono bg-muted/30 p-3 rounded">{t.message}</p>
                </Card>
              ))}
              {outreachResult.best_practices.length > 0 && (
                <Card className="p-4 bg-primary/5 border-primary/20">
                  <div className="text-xs font-semibold text-primary mb-2">Best Practices</div>
                  <ul className="space-y-1">
                    {outreachResult.best_practices.map((bp, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                        <span className="text-primary mt-1">•</span> {bp}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
              <DialogFooter>
                <Button variant="outline" onClick={() => { setOutreachResult(null); setOutreachDialogOpen(false); }}>Close</Button>
                <Button variant="outline" onClick={() => setOutreachResult(null)}>Generate again</Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
