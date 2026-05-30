import { useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import {
  ArrowRight, Briefcase, Target, TrendingUp, Calendar, Brain,
  Sparkles, Activity, Layers3, Radar, ClipboardList, MapPin,
} from "lucide-react";
import {
  Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  Area, AreaChart, CartesianGrid,
} from "recharts";

import { useAuth, useProfile, useRunPlanner, useMatches, useAgentTasks, useAnalyticsSummary, useAnalyticsActivity, useAnalyticsFunnel, useOpportunities } from "@/api/hooks";
import { StatSkeleton, CardSkeleton, ListSkeleton } from "@/components/ui/skeleton";

export default function Dashboard() {
  const { data: auth } = useAuth();
  const { data: profile } = useProfile();
  const runPlanner = useRunPlanner();
  const { data: matchesData, isLoading: matchesLoading } = useMatches();
  const { data: tasksData, isLoading: tasksLoading } = useAgentTasks();
  const { data: analytics, isLoading: analyticsLoading } = useAnalyticsSummary();
  const { data: activityData, isLoading: activityLoading } = useAnalyticsActivity();
  const { data: funnelData, isLoading: funnelLoading } = useAnalyticsFunnel();
  const { data: oppsData, isLoading: oppsLoading } = useOpportunities();

  // ── Derived data ──

  const topMatches = useMemo(() => {
    if (!matchesData?.items) return [];
    return matchesData.items.slice(0, 4).map((m) => ({
      id: m.id,
      title: m.title,
      company: m.company,
      location: m.location || "Remote",
      salary: m.salary_min && m.salary_max
        ? `$${(m.salary_min / 1000).toFixed(0)}k–$${(m.salary_max / 1000).toFixed(0)}k`
        : "",
      matchScore: m.match_score,
      logo: null,
    }));
  }, [matchesData]);

  const deadlines = useMemo(() => {
    if (!oppsData?.items) return [];
    return oppsData.items
      .filter((o) => o.deadline)
      .sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime())
      .slice(0, 5)
      .map((o) => {
        const d = new Date(o.deadline!);
        const month = d.toLocaleString("en-US", { month: "short" });
        const day = d.getDate();
        const isUrgent = d.getTime() - Date.now() < 3 * 24 * 60 * 60 * 1000;
        return {
          id: o.id,
          title: o.title,
          company: o.company,
          date: `${month} ${day}`,
          urgent: isUrgent,
        };
      });
  }, [oppsData]);

  const pipeline = useMemo(() => {
    if (funnelData) return funnelData.map((f) => ({ stage: f.name, count: f.value }));
    return [];
  }, [funnelData]);

  const activity = useMemo(() => {
    if (activityData) return activityData;
    return [];
  }, [activityData]);

  const agentTasks = useMemo(() => {
    if (!tasksData?.items) return [];
    return tasksData.items.slice(0, 7).map((t) => ({
      id: t.id,
      agent: t.agent_type,
      action: t.input?.goal ? `Goal: ${String(t.input.goal)}` : t.output?.message ? String(t.output.message) : t.status,
      timestamp: t.created_at ? new Date(t.created_at).toLocaleString() : "",
      status: t.status === "running" ? "running" as const
        : t.status === "completed" ? "complete" as const
        : "queued" as const,
    }));
  }, [tasksData]);

  const stats = useMemo(() => {
    if (!analytics) return null;
    return [
      { label: "Active Matches", value: String(analytics.active_matches), change: "Recent matches", icon: Target, accent: "text-primary" as const },
      { label: "Applications", value: String(analytics.applications), change: "Total sent", icon: Briefcase, accent: "text-accent" as const },
      { label: "Interview Rate", value: `${analytics.interview_rate}%`, change: "Conversion rate", icon: TrendingUp, accent: "text-success" as const },
      { label: "Deadlines", value: String(analytics.deadlines), change: "Upcoming", icon: Calendar, accent: "text-warning" as const },
    ];
  }, [analytics]);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="grid xl:grid-cols-[1.2fr_0.8fr] gap-4 items-stretch">
        <Card className="glass p-6 overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/10 pointer-events-none" />
          <div className="relative flex flex-col lg:flex-row lg:items-end justify-between gap-6">
            <div>
              <Badge className="mb-3 bg-success/10 text-success border-success/20">Career OS active</Badge>
              <h1 className="font-display text-3xl font-bold">Good morning, {auth?.full_name || "there"} 👋</h1>
              <p className="text-muted-foreground mt-2 max-w-2xl">
                The planner has already scanned the market, scored fresh matches, and queued actions for today.
              </p>
            </div>
            <Button className="bg-gradient-primary shadow-glow gap-2 shrink-0" onClick={() => runPlanner.mutate("Plan my job search strategy for this week")} disabled={runPlanner.isPending}>
              <Sparkles className="h-4 w-4" /> {runPlanner.isPending ? "Running…" : "Run Planner Agent"}
            </Button>
          </div>
          <div className="relative mt-6 grid sm:grid-cols-3 gap-3">
            {[
              { icon: Target, label: "Match score", value: analytics ? `${analytics.interview_rate}%` : "—" },
              { icon: MapPin, label: "Targets", value: "SF • NYC • Remote" },
              { icon: ClipboardList, label: "Auto actions", value: tasksData?.items?.length ? `${tasksData.items.length} queued` : "—" },
            ].map((item) => (
              <div key={item.label} className="glass rounded-xl p-4">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{item.label}</span>
                  <item.icon className="h-4 w-4 text-primary" />
                </div>
                <div className="mt-2 font-display text-xl font-bold">{item.value}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="glass p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Memory snapshot</div>
              <h2 className="font-display font-semibold mt-1">What the system knows</h2>
            </div>
            <Layers3 className="h-4 w-4 text-muted-foreground" />
          </div>
          {profile ? (
            <div className="space-y-3 text-sm">
              {profile.career_goal && (
                <div className="p-3 rounded-lg bg-muted/40 border-l-2 border-primary">
                  <span className="font-medium">Career goal:</span> {profile.career_goal}
                </div>
              )}
              {profile.skills && profile.skills.length > 0 && (
                <div className="p-3 rounded-lg bg-muted/40 border-l-2 border-accent">
                  <span className="font-medium">Skill profile:</span> {profile.skills.map((s) => s.name).join(", ")}
                </div>
              )}
              {profile.target_locations && profile.target_locations.length > 0 && (
                <div className="p-3 rounded-lg bg-muted/40 border-l-2 border-success">
                  <span className="font-medium">Preferences:</span> {profile.target_locations.join(", ")}
                  {profile.role_types && profile.role_types.length > 0 && ` · ${profile.role_types.join(", ")}`}
                </div>
              )}
              {!profile.career_goal && !profile.skills?.length && !profile.target_locations?.length && (
                <div className="py-4 text-center text-sm text-muted-foreground">Complete onboarding to populate your profile.</div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">Loading profile…</div>
          )}
        </Card>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats ? stats.map((s) => (
          <Card key={s.label} className="glass p-5 hover:shadow-glow transition">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{s.label}</span>
              <s.icon className={`h-4 w-4 ${s.accent}`} />
            </div>
            <div className="text-3xl font-display font-bold mt-2">{s.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.change}</div>
          </Card>
        )) : (
          <>
            {Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)}
          </>
        )}
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
                <p className="text-xs text-muted-foreground">{agentTasks.length > 0 ? "Latest agent activity" : "Run the planner to get started"}</p>
              </div>
            </div>
            {agentTasks.length > 0 && <Badge className="bg-success/10 text-success border-success/20">Active</Badge>}
          </div>
          {agentTasks.length > 0 ? (
            <div className="space-y-3 text-sm">
              {agentTasks.slice(0, 3).map((t) => (
                <div key={t.id} className="p-3 rounded-lg bg-muted/40 border-l-2 border-primary">
                  <span className="font-medium capitalize">{t.agent.replace(/_/g, " ")}:</span> {t.action}
                  {t.timestamp && <span className="text-xs text-muted-foreground ml-2">({t.timestamp})</span>}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No planner reasoning yet. Click "Run Planner Agent" to generate a strategy.
            </div>
          )}
        </Card>

        {/* Pipeline */}
        <Card className="glass p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold">Application Pipeline</h2>
            <Radar className="h-4 w-4 text-muted-foreground" />
          </div>
          {funnelLoading ? (
            <div className="space-y-3 py-8">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-4 bg-muted/40 rounded animate-pulse" style={{ width: `${60 + Math.random() * 40}%` }} />
              ))}
            </div>
          ) : pipeline.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={pipeline}>
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
                  <XAxis dataKey="stage" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">No pipeline data yet</div>
          )}
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
          {matchesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
            </div>
          ) : topMatches.length > 0 ? (
            <div className="space-y-3">
              {topMatches.map((o) => (
                <div key={o.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition cursor-pointer">
                  <div className="h-10 w-10 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary">
                    {o.company.charAt(0)}
                  </div>
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
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">No matches yet. Run the planner to find opportunities.</div>
          )}
        </Card>

        {/* Deadlines */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Upcoming Deadlines</h2>
          {oppsLoading ? (
            <ListSkeleton count={5} />
          ) : deadlines.length > 0 ? (
            <div className="space-y-3">
              {deadlines.map((d) => (
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
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">No upcoming deadlines</div>
          )}
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Activity */}
        <Card className="glass p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold">Weekly Activity</h2>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </div>
          {activityLoading ? (
            <div className="h-[220px] flex items-center justify-center text-sm text-muted-foreground">
              Loading activity data...
            </div>
          ) : activity.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={activity}>
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
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm text-muted-foreground">
              No activity data yet
            </div>
          )}
        </Card>

        {/* Agent feed */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Agent Activity</h2>
          {tasksLoading ? (
            <ListSkeleton count={6} />
          ) : agentTasks.length > 0 ? (
            <div className="space-y-3 max-h-[260px] overflow-y-auto scrollbar-thin">
              {agentTasks.map((t) => (
                <div key={t.id} className="flex gap-3 text-xs">
                  <div className={`h-2 w-2 rounded-full mt-1.5 flex-shrink-0 ${
                    t.status === "running" ? "bg-primary animate-pulse-glow" :
                    t.status === "complete" ? "bg-success" : "bg-muted-foreground"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium capitalize">{t.agent.replace(/_/g, " ")}</div>
                    <div className="text-muted-foreground line-clamp-1">{t.action}</div>
                    <div className="text-muted-foreground/60 mt-0.5">{t.timestamp}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">No agent activity yet</div>
          )}
        </Card>
      </div>
    </div>
  );
}
