import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  agentActivity, applications, opportunities, pipelineData,
  upcomingDeadlines, weeklyActivity,
} from "@/lib/sample-data";
import { Link } from "react-router-dom";
import {
  ArrowRight, Briefcase, Target, TrendingUp, Calendar, Brain,
  Sparkles, Activity,
} from "lucide-react";
import {
  Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  Area, AreaChart, CartesianGrid,
} from "recharts";

const stats = [
  { label: "Active Matches", value: "47", change: "+12 this week", icon: Target, accent: "text-primary" },
  { label: "Applications", value: "23", change: "5 in motion", icon: Briefcase, accent: "text-accent" },
  { label: "Interview Rate", value: "21%", change: "+4% vs avg", icon: TrendingUp, accent: "text-success" },
  { label: "Deadlines", value: "5", change: "Next: Dec 8", icon: Calendar, accent: "text-warning" },
];

export default function Dashboard() {
  const topMatches = opportunities.slice().sort((a, b) => b.matchScore - a.matchScore).slice(0, 4);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Good morning, Alex 👋</h1>
          <p className="text-muted-foreground mt-1">Your agents have been busy. Here's what's new today.</p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2">
          <Sparkles className="h-4 w-4" /> Run Planner Agent
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <Card key={s.label} className="glass p-5 hover:shadow-glow transition">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{s.label}</span>
              <s.icon className={`h-4 w-4 ${s.accent}`} />
            </div>
            <div className="text-3xl font-display font-bold mt-2">{s.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.change}</div>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Planner reasoning */}
        <Card className="glass p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-primary flex items-center justify-center">
                <Brain className="h-4 w-4 text-primary-foreground" />
              </div>
              <div>
                <h2 className="font-display font-semibold">Planner Agent — Today's Reasoning</h2>
                <p className="text-xs text-muted-foreground">Updated 2 min ago</p>
              </div>
            </div>
            <Badge className="bg-success/10 text-success border-success/20">Active</Badge>
          </div>
          <div className="space-y-3 text-sm">
            <div className="p-3 rounded-lg bg-muted/40 border-l-2 border-primary">
              <span className="font-medium">Goal:</span> Land an ML research internship by mid-Feb.
            </div>
            <div className="p-3 rounded-lg bg-muted/40 border-l-2 border-accent">
              <span className="font-medium">Priority this week:</span> Stripe OA (due 12/8), Anthropic interview prep (12/10), 2 new applications to research labs.
            </div>
            <div className="p-3 rounded-lg bg-muted/40 border-l-2 border-success">
              <span className="font-medium">Dispatched:</span> Resume Agent → tailoring for MIT REU. Interview Agent → 8 ML system design questions queued.
            </div>
          </div>
        </Card>

        {/* Pipeline */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Application Pipeline</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={pipelineData}>
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
              <XAxis dataKey="stage" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
              />
            </BarChart>
          </ResponsiveContainer>
          <Button variant="ghost" size="sm" className="w-full mt-2 gap-1" asChild>
            <Link to="/app/applications">View board <ArrowRight className="h-3 w-3" /></Link>
          </Button>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Top matches */}
        <Card className="glass p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold">Top Matches for You</h2>
            <Button variant="ghost" size="sm" className="gap-1" asChild>
              <Link to="/app/opportunities">See all <ArrowRight className="h-3 w-3" /></Link>
            </Button>
          </div>
          <div className="space-y-3">
            {topMatches.map((o) => (
              <div key={o.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition cursor-pointer">
                <div className="text-2xl">{o.logo}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{o.title}</div>
                  <div className="text-xs text-muted-foreground">{o.company} · {o.location} · {o.salary}</div>
                </div>
                <div className="text-right hidden sm:block">
                  <div className="text-sm font-display font-bold gradient-text">{o.matchScore}%</div>
                  <div className="text-[10px] text-muted-foreground">match</div>
                </div>
                <Progress value={o.matchScore} className="w-20 h-1.5 hidden md:block" />
              </div>
            ))}
          </div>
        </Card>

        {/* Deadlines */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Upcoming Deadlines</h2>
          <div className="space-y-3">
            {upcomingDeadlines.map((d) => (
              <div key={d.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/50 transition">
                <div className={`h-10 w-10 rounded-lg flex flex-col items-center justify-center text-[10px] font-medium ${d.urgent ? "bg-destructive/10 text-destructive" : "bg-muted text-muted-foreground"}`}>
                  {d.date.split(" ")[0]}<br/>
                  <span className="font-bold text-sm">{d.date.split(" ")[1]}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{d.title}</div>
                  <div className="text-xs text-muted-foreground">{d.company}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Activity */}
        <Card className="glass p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold">Weekly Activity</h2>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={weeklyActivity}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.6} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.6} />
                  <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="applications" stroke="hsl(var(--primary))" fill="url(#g1)" strokeWidth={2} />
              <Area type="monotone" dataKey="interviews" stroke="hsl(var(--accent))" fill="url(#g2)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Agent feed */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Agent Activity</h2>
          <div className="space-y-3 max-h-[260px] overflow-y-auto scrollbar-thin">
            {agentActivity.map((t) => (
              <div key={t.id} className="flex gap-3 text-xs">
                <div className={`h-2 w-2 rounded-full mt-1.5 flex-shrink-0 ${
                  t.status === "running" ? "bg-primary animate-pulse-glow" :
                  t.status === "queued" ? "bg-muted-foreground" : "bg-success"
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{t.agent}</div>
                  <div className="text-muted-foreground">{t.action}</div>
                  <div className="text-muted-foreground/60 mt-0.5">{t.timestamp}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
