import { useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Calendar, FileText } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

import { useApplications, useUpdateApplication, useCreateApplication, useOpportunities } from "@/api/hooks";
import { CardSkeleton } from "@/components/ui/skeleton";

type Stage = "Saved" | "Applied" | "OA" | "Interview" | "Offer" | "Rejected";

const stages: Stage[] = ["Saved", "Applied", "OA", "Interview", "Offer", "Rejected"];
const stageColor: Record<Stage, string> = {
  Saved: "bg-muted-foreground/10 text-muted-foreground",
  Applied: "bg-blue-500/10 text-blue-500",
  OA: "bg-warning/10 text-warning",
  Interview: "bg-primary/10 text-primary",
  Offer: "bg-success/10 text-success",
  Rejected: "bg-destructive/10 text-destructive",
};

export default function Applications() {
  const { data, isLoading } = useApplications();
  const updateApp = useUpdateApplication();
  const createApp = useCreateApplication();
  const { data: oppsData } = useOpportunities();
  const [dragId, setDragId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newOppId, setNewOppId] = useState("");
  const [newNotes, setNewNotes] = useState("");

  const apps = useMemo(
    () =>
      (data?.items || []).map((a) => ({
        id: a.id,
        stage: (a.stage || "Saved") as Stage,
        title: a.opportunity?.title || "Untitled",
        company: a.opportunity?.company || "Unknown",
        logo: a.opportunity?.company?.charAt(0) || "?",
        appliedDate: a.applied_date || "—",
        nextStep: a.next_step,
        nextDate: a.next_date,
        notes: a.notes,
      })),
    [data],
  );

  const move = (id: string, stage: Stage) => {
    updateApp.mutate({ id, data: { stage } });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Application Tracker</h1>
          <p className="text-muted-foreground mt-1">
            {isLoading ? "Loading…" : `Drag cards between stages. ${apps.length} total applications.`}
          </p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2" onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" /> New application
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          {stages.map((stage) => {
            const stageApps = apps.filter((a) => a.stage === stage);
            return (
              <div
                key={stage}
                className="flex flex-col min-h-[400px]"
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => {
                  if (dragId) {
                    move(dragId, stage);
                    setDragId(null);
                  }
                }}
              >
                <div className="flex items-center justify-between mb-3 px-1">
                  <div className="flex items-center gap-2">
                    <span className="font-display font-semibold text-sm">{stage}</span>
                    <Badge variant="secondary" className="text-[10px]">{stageApps.length}</Badge>
                  </div>
                </div>
                <div className="flex-1 space-y-2 p-2 rounded-xl bg-muted/30 border border-dashed border-border/50">
                  {stageApps.map((a) => (
                    <Card
                      key={a.id}
                      draggable
                      onDragStart={() => setDragId(a.id)}
                      className="glass p-3 cursor-grab active:cursor-grabbing hover:shadow-glow transition"
                    >
                      <div className="flex items-start gap-2 mb-2">
                        <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary text-sm shrink-0">
                          {a.logo}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium leading-tight truncate">{a.title}</div>
                          <div className="text-xs text-muted-foreground truncate">{a.company}</div>
                        </div>
                      </div>
                      <Badge className={`${stageColor[a.stage]} text-[10px] mb-2`} variant="outline">{a.stage}</Badge>
                      {a.nextStep && (
                        <div className="text-[11px] text-muted-foreground flex items-center gap-1 mt-2">
                          <Calendar className="h-3 w-3" /> {a.nextStep} · {a.nextDate}
                        </div>
                      )}
                      {a.notes && (
                        <div className="text-[11px] text-muted-foreground flex items-start gap-1 mt-1.5 italic">
                          <FileText className="h-3 w-3 mt-0.5 flex-shrink-0" /> {a.notes}
                        </div>
                      )}
                    </Card>
                  ))}
                  {stageApps.length === 0 && (
                    <div className="text-center text-[11px] text-muted-foreground py-8">Drop here</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="glass">
          <DialogHeader>
            <DialogTitle className="font-display">New Application</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Opportunity</label>
              <Select value={newOppId} onValueChange={setNewOppId}>
                <SelectTrigger className="mt-1.5">
                  <SelectValue placeholder="Select an opportunity" />
                </SelectTrigger>
                <SelectContent>
                  {(oppsData?.items || []).map((o) => (
                    <SelectItem key={o.id} value={o.id}>
                      {o.title} — {o.company}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Notes</label>
              <Textarea
                className="mt-1.5"
                placeholder="Any notes about this application…"
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              className="bg-gradient-primary"
              disabled={!newOppId || createApp.isPending}
              onClick={() => {
                createApp.mutate(
                  { opportunity_id: newOppId, notes: newNotes || undefined },
                  {
                    onSuccess: () => {
                      toast.success("Application created");
                      setDialogOpen(false);
                      setNewOppId("");
                      setNewNotes("");
                    },
                    onError: () => toast.error("Failed to create application"),
                  },
                );
              }}
            >
              {createApp.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
