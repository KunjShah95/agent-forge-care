import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { applications as initial, type Application } from "@/lib/sample-data";
import { Plus, Calendar, FileText } from "lucide-react";

const stages: Application["stage"][] = ["Saved", "Applied", "OA", "Interview", "Offer", "Rejected"];
const stageColor: Record<Application["stage"], string> = {
  Saved: "bg-muted-foreground/10 text-muted-foreground",
  Applied: "bg-blue-500/10 text-blue-500",
  OA: "bg-warning/10 text-warning",
  Interview: "bg-primary/10 text-primary",
  Offer: "bg-success/10 text-success",
  Rejected: "bg-destructive/10 text-destructive",
};

export default function Applications() {
  const [apps, setApps] = useState<Application[]>(initial);
  const [dragId, setDragId] = useState<string | null>(null);

  const move = (id: string, stage: Application["stage"]) =>
    setApps(prev => prev.map(a => a.id === id ? { ...a, stage } : a));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Application Tracker</h1>
          <p className="text-muted-foreground mt-1">Drag cards between stages. {apps.length} total applications.</p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2">
          <Plus className="h-4 w-4" /> New application
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {stages.map((stage) => {
          const stageApps = apps.filter(a => a.stage === stage);
          return (
            <div
              key={stage}
              className="flex flex-col min-h-[400px]"
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => { if (dragId) { move(dragId, stage); setDragId(null); } }}
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
                      <span className="text-xl">{a.logo}</span>
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
    </div>
  );
}
