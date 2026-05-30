import { useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Calendar, FileText, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  DndContext, DragOverlay, useDroppable,
  PointerSensor, TouchSensor, useSensor, useSensors,
  type DragEndEvent, type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { useApplications, useUpdateApplication, useCreateApplication, useDeleteApplication, useOpportunities } from "@/api/hooks";
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

function SortableCard({
  app,
  stageColor,
  onDelete,
}: {
  app: { id: string; stage: Stage; title: string; company: string; logo: string; nextStep?: string; nextDate?: string; notes?: string };
  stageColor: Record<Stage, string>;
  onDelete: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: app.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card className="glass p-3 cursor-grab active:cursor-grabbing hover:shadow-glow transition group">
        <div className="flex items-start gap-2 mb-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary text-sm shrink-0">
            {app.logo}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium leading-tight truncate">{app.title}</div>
            <div className="text-xs text-muted-foreground truncate">{app.company}</div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(app.id);
            }}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
        <Badge className={`${stageColor[app.stage]} text-[10px] mb-2`} variant="outline">{app.stage}</Badge>
        {app.nextStep && (
          <div className="text-[11px] text-muted-foreground flex items-center gap-1 mt-2">
            <Calendar className="h-3 w-3" /> {app.nextStep} · {app.nextDate}
          </div>
        )}
        {app.notes && (
          <div className="text-[11px] text-muted-foreground flex items-start gap-1 mt-1.5 italic">
            <FileText className="h-3 w-3 mt-0.5 flex-shrink-0" /> {app.notes}
          </div>
        )}
      </Card>
    </div>
  );
}

function CardContent({
  app,
  stageColor,
}: {
  app: { id: string; stage: Stage; title: string; company: string; logo: string; nextStep?: string; nextDate?: string; notes?: string };
  stageColor: Record<Stage, string>;
}) {
  return (
    <Card className="glass p-3 shadow-lg ring-2 ring-primary/20">
      <div className="flex items-start gap-2 mb-2">
        <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary text-sm shrink-0">
          {app.logo}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium leading-tight truncate">{app.title}</div>
          <div className="text-xs text-muted-foreground truncate">{app.company}</div>
        </div>
      </div>
      <Badge className={`${stageColor[app.stage]} text-[10px] mb-2`} variant="outline">{app.stage}</Badge>
      {app.nextStep && (
        <div className="text-[11px] text-muted-foreground flex items-center gap-1 mt-2">
          <Calendar className="h-3 w-3" /> {app.nextStep} · {app.nextDate}
        </div>
      )}
    </Card>
  );
}

function StageColumn({
  stage,
  apps,
  stageColor,
  onDelete,
}: {
  stage: Stage;
  apps: { id: string; stage: Stage; title: string; company: string; logo: string; nextStep?: string; nextDate?: string; notes?: string }[];
  stageColor: Record<Stage, string>;
  onDelete: (id: string) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: stage });
  const stageApps = apps.filter((a) => a.stage === stage);

  return (
    <div className="flex flex-col min-h-[400px]">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <span className="font-display font-semibold text-sm">{stage}</span>
          <Badge variant="secondary" className="text-[10px]">{stageApps.length}</Badge>
        </div>
      </div>
      <SortableContext items={stageApps.map((a) => a.id)} strategy={verticalListSortingStrategy}>
        <div
          ref={setNodeRef}
          className={`flex-1 space-y-2 p-2 rounded-xl bg-muted/30 border border-dashed transition-colors ${isOver ? "bg-primary/5 border-primary/30" : "border-border/50"}`}
        >
          {stageApps.map((a) => (
            <SortableCard key={a.id} app={a} stageColor={stageColor} onDelete={onDelete} />
          ))}
          {stageApps.length === 0 && (
            <div className="text-center text-[11px] text-muted-foreground py-8">Drop here</div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

export default function Applications() {
  const { data, isLoading } = useApplications();
  const updateApp = useUpdateApplication();
  const createApp = useCreateApplication();
  const deleteApp = useDeleteApplication();
  const { data: oppsData } = useOpportunities();

  const [activeId, setActiveId] = useState<string | null>(null);
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

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;

    const draggedId = String(active.id);
    const overId = String(over.id);

    const fromStage = stages.find((s) =>
      apps.filter((a) => a.stage === s).some((a) => a.id === draggedId),
    );
    if (!fromStage) return;

    let toStage: Stage | undefined;
    if (stages.includes(overId as Stage)) {
      toStage = overId as Stage;
    } else {
      toStage = stages.find((s) =>
        apps.filter((a) => a.stage === s).some((a) => a.id === overId),
      );
    }

    if (toStage && fromStage !== toStage) {
      move(draggedId, toStage);
    }
    setActiveId(null);
  }

  const draggedApp = activeId ? apps.find((a) => a.id === activeId) : null;

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
        <DndContext
          sensors={sensors}
          collisionDetection={(args) => {
            const rects = args.droppableRects;
            const pointer = args.pointerCoordinates;
            if (!pointer) return null;
            let closest = null;
            let minDist = Infinity;
            for (const [id, rect] of rects) {
              if (!rect) continue;
              const cx = rect.left + rect.width / 2;
              const cy = rect.top + rect.height / 2;
              const dist = Math.sqrt((pointer.x - cx) ** 2 + (pointer.y - cy) ** 2);
              if (dist < minDist) {
                minDist = dist;
                closest = id;
              }
            }
            return closest ? [{ id: closest, value: 0 }] : [];
          }}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
            {stages.map((stage) => (
              <StageColumn
                key={stage}
                stage={stage}
                apps={apps}
                stageColor={stageColor}
                onDelete={(id) =>
                  deleteApp.mutate(id, {
                    onSuccess: () => toast.success("Application deleted"),
                    onError: () => toast.error("Failed to delete application"),
                  })
                }
              />
            ))}
          </div>
          <DragOverlay>
            {draggedApp && <CardContent app={draggedApp} stageColor={stageColor} />}
          </DragOverlay>
        </DndContext>
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
