import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Layers3, Brain, Star, BookOpen,
  Plus, Sparkles, Clock, Database, Zap, Trash2, Pencil,
} from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useMemory, useCreateMemory, useUpdateMemory, useDeleteMemory, useProfile } from "@/api/hooks";
import { toast } from "@/hooks/use-toast";
import type { MemoryEntry } from "@/api/client";

function formatRelativeTime(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

function MemoryEntryRow({ entry, onEdit, onDelete }: { entry: MemoryEntry; onEdit: (entry: MemoryEntry) => void; onDelete: (entry: MemoryEntry) => void }) {
  return (
    <div className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition group">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{entry.key}</span>
          <Badge variant="outline" className="text-[10px]">
            weight: {entry.weight.toFixed(1)}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">{typeof entry.value === "object" ? JSON.stringify(entry.value) : String(entry.value)}</p>
      </div>
      <div className="text-xs text-muted-foreground hidden md:block">{formatRelativeTime(entry.updated_at)}</div>
      <Button
        variant="ghost"
        size="sm"
        className="opacity-0 group-hover:opacity-100 transition"
        onClick={() => onEdit(entry)}
      >
        <Pencil className="h-3 w-3" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="opacity-0 group-hover:opacity-100 transition text-destructive hover:text-destructive"
        onClick={() => onDelete(entry)}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
}

export default function MemoryViewer() {
  const [addOpen, setAddOpen] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [editingEntry, setEditingEntry] = useState<MemoryEntry | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editWeight, setEditWeight] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<MemoryEntry | null>(null);

  const { data: memoryData, isLoading: memoryLoading } = useMemory();
  const { data: profile, isLoading: profileLoading } = useProfile();
  const createMemory = useCreateMemory();
  const updateMemory = useUpdateMemory();
  const deleteMemory = useDeleteMemory();

  const entries = memoryData?.items ?? [];
  const profileEntries = entries.filter((e) =>
    ["target_role", "preferred_locations", "salary", "company", "portfolio", "linkedin", "graduation", "career_goal", "school", "bio"].some(
      (prefix) => e.key.toLowerCase().includes(prefix)
    )
  );
  const learningEntries = entries.filter((e) =>
    ["learning", "insight", "feedback", "trend", "note"].some(
      (prefix) => e.key.toLowerCase().includes(prefix)
    )
  );
  const otherEntries = entries.filter(
    (e) => !profileEntries.includes(e) && !learningEntries.includes(e)
  );

  const skills = profile?.skills ?? [];

  const handleAdd = () => {
    if (newKey.trim() && newValue.trim()) {
      createMemory.mutate(
        { key: newKey.trim(), value: newValue.trim() },
        {
          onSuccess: () => {
            setNewKey("");
            setNewValue("");
            setAddOpen(false);
          },
        }
      );
    }
  };

  const handleEdit = (entry: MemoryEntry) => {
    setEditingEntry(entry);
    setEditValue(JSON.stringify(entry.value, null, 2));
    setEditWeight(String(entry.weight));
  };

  const handleSaveEdit = () => {
    if (!editingEntry) return;
    let parsedValue: unknown;
    try {
      parsedValue = JSON.parse(editValue);
    } catch {
      toast({ title: "Invalid JSON", description: "Value must be valid JSON", variant: "destructive" });
      return;
    }
    const weight = parseFloat(editWeight);
    if (isNaN(weight)) {
      toast({ title: "Invalid weight", description: "Weight must be a number", variant: "destructive" });
      return;
    }
    updateMemory.mutate(
      { id: editingEntry.id, data: { value: parsedValue, weight } },
      {
        onSuccess: () => {
          toast({ title: "Memory updated" });
          setEditingEntry(null);
        },
        onError: () => {
          toast({ title: "Failed to update memory", variant: "destructive" });
        },
      }
    );
  };

  const handleDelete = (entry: MemoryEntry) => {
    setDeleteTarget(entry);
  };

  const confirmDelete = () => {
    if (!deleteTarget) return;
    deleteMemory.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast({ title: "Memory deleted" });
        setDeleteTarget(null);
      },
      onError: () => {
        toast({ title: "Failed to delete memory", variant: "destructive" });
      },
    });
  };

  const isLoading = memoryLoading || profileLoading;

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Memory Layer</h1>
          <p className="text-muted-foreground mt-1">
            The system's long-term memory. This data personalizes agent behavior, match scoring, and recommendations.
          </p>
        </div>
        <Button className="bg-gradient-1 shadow-glow gap-2" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" /> Add Memory
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Memory Entries", value: entries.length, icon: Database },
          { label: "Skills Tracked", value: skills.length, icon: Zap },
          { label: "Learning Points", value: learningEntries.length, icon: BookOpen },
          {
            label: "Context Score",
            value: entries.length > 0
              ? Math.round(entries.reduce((s, e) => s + e.weight, 0) / entries.length * 100) / 100 + "/10"
              : "—",
            icon: Brain,
          },
        ].map((s) => (
          <Card key={s.label} className="bento-card p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{s.label}</span>
              <s.icon className="h-4 w-4 text-primary" />
            </div>
            <div className="text-3xl font-display font-bold mt-2 gradient-text">
              {isLoading ? <Skeleton className="h-9 w-16" /> : s.value}
            </div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="bento-card">
          <TabsTrigger value="profile">Profile Memory</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="learnings">Learnings</TabsTrigger>
          <TabsTrigger value="raw">Raw Context</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4">
          <Card className="bento-card p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-display font-semibold">Stored Preferences</h2>
                <p className="text-xs text-muted-foreground">Weight indicates importance in match scoring</p>
              </div>
              <Layers3 className="h-4 w-4 text-muted-foreground" />
            </div>
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-xl" />
                ))}
              </div>
            ) : profileEntries.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Database className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No profile memory entries yet. Add one to get started.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {profileEntries.map((entry) => (
                  <MemoryEntryRow key={entry.id} entry={entry} onEdit={handleEdit} onDelete={handleDelete} />
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="skills" className="mt-4 space-y-4">
          <Card className="bento-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display font-semibold">Skills</h2>
              <Badge variant="outline" className="gap-1">
                <Star className="h-3 w-3 fill-warning text-warning" />
                Total: {skills.reduce((s, sk) => s + (sk.proficiency === "expert" ? 1 : sk.proficiency === "advanced" ? 0.85 : sk.proficiency === "intermediate" ? 0.65 : 0.3), 0).toFixed(1)}
              </Badge>
            </div>
            {isLoading ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-20 rounded-xl" />
                ))}
              </div>
            ) : skills.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Zap className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No skills tracked yet.</p>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {skills.map((skill) => {
                  const level = skill.proficiency || "intermediate";
                  const weight = level === "expert" ? 1.0 : level === "advanced" ? 0.85 : level === "intermediate" ? 0.65 : 0.3;
                  return (
                    <div key={skill.id} className="p-3 rounded-xl bg-muted/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm">{skill.name}</span>
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            level === "expert"
                              ? "bg-success/10 text-success border-success/20"
                              : level === "advanced"
                                ? "bg-primary/10 text-primary border-primary/20"
                                : "bg-muted-foreground/10 text-muted-foreground"
                          }`}
                        >
                          {level.charAt(0).toUpperCase() + level.slice(1)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-1"
                            style={{ width: `${weight * 100}%` }}
                          />
                        </div>
                        <span>w:{weight.toFixed(1)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="learnings" className="mt-4 space-y-3">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full rounded-xl" />
              ))}
            </div>
          ) : learningEntries.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No learning entries yet.</p>
            </div>
          ) : (
            learningEntries.map((entry) => (
              <Card key={entry.id} className="bento-card p-5 hover:shadow-glow transition">
                <div className="flex items-start gap-3">
                  <div className="h-8 w-8 rounded-lg bg-gradient-1/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <Brain className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm">{String(entry.value)}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                      <Badge variant="secondary" className="text-[10px]">{entry.key}</Badge>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {formatRelativeTime(entry.updated_at)}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="raw" className="mt-4">
          <Card className="bento-card p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-display font-semibold">Raw Agent Context</h2>
                <p className="text-xs text-muted-foreground">
                  This condensed view is sent to agents for personalization
                </p>
              </div>
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div className="p-4 rounded-xl bg-muted/40 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
              {isLoading ? (
                <Skeleton className="h-48 w-full" />
              ) : (
                JSON.stringify(
                  {
                    memory: entries.map((e) => ({ key: e.key, value: e.value, weight: e.weight })),
                    skills: skills.map((s) => ({ name: s.name, proficiency: s.proficiency })),
                  },
                  null,
                  2
                )
              )}
            </div>
            <div className="flex gap-2 mt-4">
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => navigator.clipboard.writeText(JSON.stringify({ memory: entries, skills }, null, 2))}
              >
                <Database className="h-3 w-3" /> Copy context
              </Button>
              <Button variant="outline" size="sm" className="gap-1">
                <Sparkles className="h-3 w-3" /> Refresh
              </Button>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-w-md glass">
          <DialogHeader>
            <DialogTitle className="font-display">Add Memory Entry</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Key</label>
              <Input
                placeholder="e.g., preferred_company, interview_note"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="mt-1.5"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Value</label>
              <Input
                placeholder="e.g., Anthropic, Stripe, Linear"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="mt-1.5"
              />
            </div>
            <Button
              className="w-full bg-gradient-1 shadow-glow"
              onClick={handleAdd}
              disabled={createMemory.isPending}
            >
              {createMemory.isPending ? "Saving..." : "Save Memory"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editingEntry} onOpenChange={(open) => { if (!open) setEditingEntry(null); }}>
        <DialogContent className="max-w-md glass">
          <DialogHeader>
            <DialogTitle className="font-display">Edit Memory Entry</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Key</label>
              <Input value={editingEntry?.key ?? ""} disabled className="mt-1.5" />
            </div>
            <div>
              <label className="text-sm font-medium">Value (JSON)</label>
              <Textarea
                placeholder='e.g., "Anthropic" or {"company":"Stripe"}'
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="mt-1.5 font-mono text-xs"
                rows={6}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Weight</label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="10"
                placeholder="e.g., 1.0"
                value={editWeight}
                onChange={(e) => setEditWeight(e.target.value)}
                className="mt-1.5"
              />
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setEditingEntry(null)}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-gradient-1 shadow-glow"
                onClick={handleSaveEdit}
                disabled={updateMemory.isPending}
              >
                {updateMemory.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <DialogContent className="max-w-sm glass">
          <DialogHeader>
            <DialogTitle className="font-display">Delete Memory Entry</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete "<strong>{deleteTarget?.key}</strong>"? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={confirmDelete}
                disabled={deleteMemory.isPending}
              >
                {deleteMemory.isPending ? "Deleting..." : "Delete"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
