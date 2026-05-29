import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Bell, Mail, Smartphone, Zap } from "lucide-react";

const alerts = [
  { id: "al1", name: "ML Research Internships", filters: "ML + Research, Remote OK, $7k+/mo", lastTriggered: "2h ago", new: 4, on: true },
  { id: "al2", name: "Startup Founding Engineer", filters: "Startup, 5-20 people, SF/Remote", lastTriggered: "Yesterday", new: 2, on: true },
  { id: "al3", name: "AI Safety Fellowships", filters: "Fellowship, AI Alignment", lastTriggered: "3d ago", new: 1, on: true },
  { id: "al4", name: "Hackathons - Weekend", filters: "Virtual hackathons, prize > $5k", lastTriggered: "1w ago", new: 0, on: false },
];

export default function OpportunityMonitor() {
  return (
    <div className="space-y-6 max-w-[1200px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Opportunity Monitor</h1>
          <p className="text-muted-foreground mt-1">Configure alerts. Your Monitor Agent watches 24/7.</p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2"><Bell className="h-4 w-4" /> New alert</Button>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="glass p-6 lg:col-span-2 space-y-3">
          <h2 className="font-display font-semibold mb-2">Active Alerts</h2>
          {alerts.map((a) => (
            <div key={a.id} className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition">
              <Switch defaultChecked={a.on} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{a.name}</span>
                  {a.new > 0 && <Badge className="bg-primary/15 text-primary border-primary/30">{a.new} new</Badge>}
                </div>
                <div className="text-xs text-muted-foreground">{a.filters}</div>
              </div>
              <div className="text-xs text-muted-foreground hidden md:block">{a.lastTriggered}</div>
              <Button variant="ghost" size="sm">Edit</Button>
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
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Smartphone className="h-4 w-4 text-muted-foreground" />
                <div>
                  <Label className="text-sm">Push notifications</Label>
                  <div className="text-xs text-muted-foreground">For 90%+ matches only</div>
                </div>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Zap className="h-4 w-4 text-muted-foreground" />
                <div>
                  <Label className="text-sm">Real-time alerts</Label>
                  <div className="text-xs text-muted-foreground">Slack & SMS</div>
                </div>
              </div>
              <Switch />
            </div>
          </div>
          <div className="pt-4 border-t border-border/50">
            <Label className="text-xs">Match score threshold</Label>
            <Input defaultValue="85" type="number" className="mt-1.5" />
          </div>
        </Card>
      </div>
    </div>
  );
}
