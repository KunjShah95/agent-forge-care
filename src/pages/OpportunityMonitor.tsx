import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Bell, Mail, Smartphone, Zap, Loader2, Trash2 } from "lucide-react";
import { useAlertConfigs, useCreateAlert, useUpdateAlert, useDeleteAlert } from "@/api/hooks";
import { toast } from "sonner";

export default function OpportunityMonitor() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formKeywords, setFormKeywords] = useState("");
  const [formLocations, setFormLocations] = useState("");
  const [formScore, setFormScore] = useState("75");

  const [dailyDigest, setDailyDigest] = useState(true);
  const [pushNotif, setPushNotif] = useState(true);
  const [realTime, setRealTime] = useState(false);
  const [threshold, setThreshold] = useState("85");

  const { data: alerts, isLoading } = useAlertConfigs();
  const createAlert = useCreateAlert();
  const updateAlert = useUpdateAlert();
  const deleteAlert = useDeleteAlert();

  const resetForm = () => {
    setFormName("");
    setFormKeywords("");
    setFormLocations("");
    setFormScore("75");
    setEditingId(null);
  };

  const openNew = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEdit = (alert: { id: string; name: string; keywords: string[]; locations: string[]; min_match_score: number }) => {
    setEditingId(alert.id);
    setFormName(alert.name);
    setFormKeywords(alert.keywords.join(", "));
    setFormLocations(alert.locations.join(", "));
    setFormScore(String(alert.min_match_score));
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formName) {
      toast.error("Please enter an alert name");
      return;
    }
    const payload = {
      name: formName,
      keywords: formKeywords.split(",").map((k) => k.trim()).filter(Boolean),
      locations: formLocations.split(",").map((l) => l.trim()).filter(Boolean),
      min_match_score: Number(formScore) || 75,
    };

    try {
      if (editingId) {
        await updateAlert.mutateAsync({ id: editingId, data: payload } as never);
        toast.success("Alert updated");
      } else {
        await createAlert.mutateAsync(payload as never);
        toast.success("Alert created");
      }
      setDialogOpen(false);
      resetForm();
    } catch {
      toast.error(editingId ? "Failed to update alert" : "Failed to create alert");
    }
  };

  const handleToggle = async (alert: { id: string; is_active: boolean }) => {
    try {
      await updateAlert.mutateAsync({ id: alert.id, data: { is_active: !alert.is_active } } as never);
    } catch {
      toast.error("Failed to toggle alert");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAlert.mutateAsync(id);
      toast.success("Alert deleted");
    } catch {
      toast.error("Failed to delete alert");
    }
  };

  return (
    <div className="space-y-6 max-w-[1200px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Opportunity Monitor</h1>
          <p className="text-muted-foreground mt-1">Configure alerts. Your Monitor Agent watches 24/7.</p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2" onClick={openNew}>
          <Bell className="h-4 w-4" /> New alert
        </Button>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="glass p-6 lg:col-span-2 space-y-3">
          <h2 className="font-display font-semibold mb-2">Active Alerts</h2>
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
          {!isLoading && alerts && alerts.length === 0 && (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No alerts configured. Click "New alert" to get started.
            </div>
          )}
          {alerts?.map((a) => (
            <div key={a.id} className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition">
              <Switch checked={a.is_active} onCheckedChange={() => handleToggle(a)} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{a.name}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {a.keywords?.join(", ")} · {a.locations?.join(", ")}
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => openEdit(a)}>Edit</Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => handleDelete(a.id)}
                disabled={deleteAlert.isPending}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </Card>

        <Card className="glass p-6 space-y-5">
          <h2 className="font-display font-semibold">Digest Settings</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <div>
                  <Label className="text-sm">Daily email digest</Label>
                  <div className="text-xs text-muted-foreground">8:00 AM PT</div>
                </div>
              </div>
              <Switch checked={dailyDigest} onCheckedChange={setDailyDigest} />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Smartphone className="h-4 w-4 text-muted-foreground" />
                <div>
                  <Label className="text-sm">Push notifications</Label>
                  <div className="text-xs text-muted-foreground">For 90%+ matches only</div>
                </div>
              </div>
              <Switch checked={pushNotif} onCheckedChange={setPushNotif} />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Zap className="h-4 w-4 text-muted-foreground" />
                <div>
                  <Label className="text-sm">Real-time alerts</Label>
                  <div className="text-xs text-muted-foreground">Slack & SMS</div>
                </div>
              </div>
              <Switch checked={realTime} onCheckedChange={setRealTime} />
            </div>
          </div>
          <div className="pt-4 border-t border-border/50">
            <Label className="text-xs">Match score threshold</Label>
            <Input
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              type="number"
              className="mt-1.5"
            />
          </div>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Alert" : "New Alert"}</DialogTitle>
            <DialogDescription>
              Configure what opportunities your Monitor Agent should watch for.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                placeholder="e.g. ML Research Internships"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Keywords (comma-separated)</Label>
              <Input
                placeholder="e.g. ML, Research, AI Safety"
                value={formKeywords}
                onChange={(e) => setFormKeywords(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Locations (comma-separated)</Label>
              <Input
                placeholder="e.g. Remote, SF, NYC"
                value={formLocations}
                onChange={(e) => setFormLocations(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Min Match Score</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={formScore}
                onChange={(e) => setFormScore(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setDialogOpen(false); resetForm(); }}>Cancel</Button>
            <Button
              className="bg-gradient-primary shadow-glow gap-2"
              onClick={handleSubmit}
              disabled={createAlert.isPending || updateAlert.isPending}
            >
              {(createAlert.isPending || updateAlert.isPending) && <Loader2 className="h-4 w-4 animate-spin" />}
              {editingId ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
