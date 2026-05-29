import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

export default function Settings() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="font-display text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your profile, agents, and preferences.</p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="glass">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4 space-y-4">
          <Card className="glass p-6 space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 border-2 border-primary/30">
                <AvatarFallback className="bg-gradient-primary text-primary-foreground text-lg font-display">AK</AvatarFallback>
              </Avatar>
              <Button variant="outline" size="sm">Upload photo</Button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Name</Label><Input defaultValue="Alex Kim" className="mt-1.5" /></div>
              <div><Label>Email</Label><Input defaultValue="alex@stanford.edu" className="mt-1.5" /></div>
              <div><Label>School</Label><Input defaultValue="Stanford University" className="mt-1.5" /></div>
              <div><Label>Graduation</Label><Input defaultValue="June 2026" className="mt-1.5" /></div>
              <div><Label>Portfolio</Label><Input defaultValue="https://alexkim.dev" className="mt-1.5" /></div>
              <div><Label>LinkedIn</Label><Input defaultValue="linkedin.com/in/alexkim" className="mt-1.5" /></div>
            </div>
            <Button className="bg-gradient-primary shadow-glow">Save changes</Button>
          </Card>
        </TabsContent>

        <TabsContent value="agents" className="mt-4 space-y-3">
          {["Planner", "Internship", "Job", "Research", "Resume", "Interview", "Networking", "Opportunity Monitor"].map((a) => (
            <Card key={a} className="glass p-4 flex items-center gap-4">
              <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                {a[0]}
              </div>
              <div className="flex-1">
                <div className="font-medium">{a} Agent</div>
                <div className="text-xs text-muted-foreground">Active · Last run 12 min ago</div>
              </div>
              <Badge variant="outline" className="bg-success/10 text-success border-success/20">Healthy</Badge>
              <Switch defaultChecked />
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="billing" className="mt-4">
          <Card className="glass p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="font-display font-semibold text-lg">Pro Plan</div>
                <div className="text-xs text-muted-foreground">$19/mo · Renews Jan 14</div>
              </div>
              <Badge className="bg-gradient-primary border-0 text-primary-foreground">Active</Badge>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Agent runs this month</span><span>1,247</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">AI tokens used</span><span>2.4M / 5M</span></div>
            </div>
            <Button variant="outline" className="w-full mt-4">Manage subscription</Button>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
