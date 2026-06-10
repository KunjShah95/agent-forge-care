import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import {
  ArrowRight, Briefcase, Target, TrendingUp, Calendar, Brain,
  Sparkles, Activity, Layers3, Radar, ClipboardList, MapPin,
  Clock, Zap, ChevronRight,
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
  const { data: matchesData, isLoading: matchesLoading, isError: matchesError } = useMatches();
  const { data: tasksData, isLoading: tasksLoading, isError: tasksError } = useAgentTasks();
  const { data: analytics, isLoading: analyticsLoading, isError: analyticsError } = useAnalyticsSummary();
  const { data: activityData, isLoading: activityLoading, isError: activityError } = useAnalyticsActivity();
  const { data: funnelData, isLoading: funnelLoading, isError: funnelError } = useAnalyticsFunnel();
  const { data: oppsData, isLoading: oppsLoading, isError: oppsError } = useOpportunities();

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
        return { id: o.id, title: o.title, company: o.company, date: `${month} ${day}`, urgent: isUrgent };
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
      { label: "Active Matches", value: String(analytics.active_matches), change: "Recent matches", icon: Target, accent: "from-violet-500 to-purple-600" },
      { label: "Applications", value: String(analytics.applications), change: "Total sent", icon: Briefcase, accent: "from-cyan-500 to-blue-600" },
      { label: "Interview Rate", value: `${analytics.interview_rate}%`, change: "Conversion rate", icon: TrendingUp, accent: "from-emerald-500 to-green-600" },
      { label: "Deadlines", value: String(analytics.deadlines), change: "Upcoming", icon: Calendar, accent: "from-amber-500 to-orange-600" },
    ];
  }, [analytics]);

  const errors = [matchesError && "matches", tasksError && "tasks", analyticsError && "analytics", funnelError && "pipeline", activityError && "activity", oppsError && "opportunities"].filter(Boolean);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-6 max-w-[1400px] animate-fade-in">
      {errors.length > 0 && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive">
          <span className="h-2 w-2 rounded-full bg-destructive flex-shrink-0" />
          <span>Some data failed to load: {errors.join(", ")}. Refresh the page or check your connection.</span>
        </div>
      )}

      {/* ── Welcome Banner ── */}
      <div className="bento-card p-6 md:p-8 overflow-hidden relative">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.07] via-transparent to-accent/[0.05] pointer-events-none" />
        <div className="absolute top-0 left-1/4 w-64 h-64 rounded-full bg-gradient-1 opacity-[0.03] blur-3xl" />
        <div className="relative flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div>
            <Badge className="mb-3 bg-gradient-1 text-primary-foreground border-none">
              <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse-glow mr-1.5" />
              Career OS active
            </Badge>
            <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight">
              {greeting}, {auth?.full_name || "there"} <span className="inline-block animate-float" style={{ animationDuration: "2s" }}>👋</span>
            </h1>
            <p className="text-muted-foreground mt-2 max-w-2xl">
              The planner has already scanned the market, scored fresh matches, and queued actions for today. Your career OS is working while you focus on what matters.
            </p>
          </div>
          <Button
            className="bg-gradient-1 shadow-glow hover:shadow-glow-lg transition-all duration-300 gap-2 shrink-0 group"
            onClick={() => runPlanner.mutate("Plan my job search strategy for this week")}
            disabled={runPlanner.isPending}
          >
            <Sparkles className="h-4 w-4 group-hover:rotate-12 transition-transform" />
            {runPlanner.isPending ? "Running…" : "Run Planner Agent"}
          </Button>
        </div>

        {/* Quick stats row */}
        <div className="relative mt-6 grid sm:grid-cols-3 gap-3">
          {[
            { icon: Target, label: "Match score", value: analytics ? `${analytics.interview_rate}%` : "—", color: "from-violet-500/20 to-purple-500/20" },
            { icon: MapPin, label: "Targets", value: profile?.target_locations?.length ? profile.target_locations.join(" • ") : "—", color: "from-cyan-500/20 to-blue-500/20" },
            { icon: ClipboardList, label: "Auto actions", value: tasksData?.items?.length ? `${tasksData.items.length} queued` : "—", color: "from-emerald-500/20 to-green-500/20" },
          ].map((item) => (
            <div key={item.label} className="glass-card rounded-xl p-4 bg-gradient-to-br from-background/80 to-muted/50">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span>{item.label}</span>
                <item.icon className="h-4 w-4 text-primary" />
              </div>
              <div className="mt-1 font-display text-xl font-bold tracking-tight">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats ? stats.map((s, i) => (
          <div
            key={s.label}
            className="bento-card p-5 animate-fade-in-up group"
            style={{ animationDelay: `${i * 0.08}s` }}
          >
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-transparent via-transparent to-primary/[0.02] opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground tracking-wide">{s.label}</span>
                <div className={`h-8 w-8 rounded-lg bg-gradient-to-br ${s.accent} bg-opacity-20 flex items-center justify-center`}>
                  <s.icon className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="text-3xl font-display font-bold mt-3 tracking-tight">{s.value}</div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                <span className="h-1 w-1 rounded-full bg-primary/40" />
                {s.change}
              </div>
            </div>
          </div>
        )) : (
          Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
        )}
      </div>

      {/* ── Main Content Grid ── */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Planner reasoning */}
        <div className="bento-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-1 flex items-center justify-center shadow-glow">
                <Brain className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h2 className="font-display font-semibold">Planner Agent — Today's Reasoning</h2>
                <p className="text-xs text-muted-foreground">{agentTasks.length > 0 ? "Latest agent activity" : "Run the planner to get started"}</p>
              </div>
            </div>
            {agentTasks.length > 0 && (
              <Badge className="bg-gradient-1 text-primary-foreground border-none gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse-glow" />
                Active
              </Badge>
            )}
          </div>
          {agentTasks.length > 0 ? (
            <div className="space-y-3">
              {agentTasks.slice(0, 3).map((t, i) => (
                <div key={t.id} className="relative p-4 rounded-xl bg-gradient-to-r from-primary/[0.04] to-transparent border-l-2 border-primary/40 animate-fade-in-up" style={{ animationDelay: `${i * 0.08}s` }}>
                  <div className="flex items-start gap-3">
                    <Brain className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                    <div>
                      <span className="font-medium text-sm capitalize">{t.agent.replace(/_/g, " ")}</span>
                      <p className="text-sm text-muted-foreground mt-0.5">{t.action}</p>
                      {t.timestamp && <span className="text-xs text-muted-foreground/60 mt-1 block">{t.timestamp}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Brain className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No planner reasoning yet. Click "Run Planner Agent" to generate a strategy.</p>
            </div>
          )}
        </div>

        {/* Application Pipeline */}
        <div className="bento-card p-6">
          <div className="flex items-center justify-between mb-5">
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
            <div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={pipeline}>
                  <defs>
                    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                      <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    </linearGradient>
                  </defs>
                  <Bar dataKey="count" fill="url(#barGrad)" radius={[8, 8, 0, 0]} />
                  <XAxis dataKey="stage" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 12,
                      fontSize: 12,
                      boxShadow: "var(--shadow-elegant)",
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-4 space-y-2">
                {pipeline.map((p) => (
                  <div key={p.stage} className="flex items-center gap-3 text-xs">
                    <span className="w-16 text-muted-foreground">{p.stage}</span>
                    <div className="flex-1 h-2 rounded-full bg-muted/30 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-1 opacity-80 transition-all"
                        style={{ width: `${(p.count / Math.max(...pipeline.map((x) => x.count))) * 100}%` }}
                      />
                    </div>
                    <span className="font-medium w-6 text-right">{p.count}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-12 text-center">
              <Radar className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No pipeline data yet</p>
            </div>
          )}
          <Button variant="ghost" size="sm" className="w-full mt-4 gap-1 text-primary" asChild>
            <Link to="/app/applications">
              View board <ChevronRight className="h-3 w-3" />
            </Link>
          </Button>
        </div>
      </div>

      {/* ── Matches & Deadlines ── */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Top Matches */}
        <div className="bento-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-display font-semibold">Top Matches for You</h2>
            <Button variant="ghost" size="sm" className="gap-1 text-primary" asChild>
              <Link to="/app/opportunities">
                See all <ChevronRight className="h-3 w-3" />
              </Link>
            </Button>
          </div>
          {matchesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
            </div>
          ) : topMatches.length > 0 ? (
            <div className="space-y-2">
              {topMatches.map((o, i) => (
                <div
                  key={o.id}
                  className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-r from-muted/30 to-transparent hover:from-primary/[0.04] transition-all duration-200 cursor-pointer group"
                >
                  <div className="h-12 w-12 rounded-xl bg-gradient-1/10 border border-primary/20 flex items-center justify-center font-bold text-primary text-lg group-hover:scale-110 transition-transform duration-300">
                    {o.company.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate group-hover:text-primary transition-colors">{o.title}</div>
                    <div className="text-xs text-muted-foreground">{o.company} · {o.location} · {o.salary}</div>
                  </div>
                  <div className="text-right hidden sm:block">
                    <div className="text-lg font-display font-bold gradient-text-1">{o.matchScore}%</div>
                    <div className="text-[10px] text-muted-foreground">match</div>
                  </div>
                  <Progress value={o.matchScore} className="w-20 h-1.5 hidden md:block" />
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Target className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No matches yet. Run the planner to find opportunities.</p>
            </div>
          )}
        </div>

        {/* Deadlines */}
        <div className="bento-card p-6">
          <div className="flex items-center gap-2 mb-5">
            <Calendar className="h-5 w-5 text-primary" />
            <h2 className="font-display font-semibold">Upcoming Deadlines</h2>
          </div>
          {oppsLoading ? (
            <ListSkeleton count={5} />
          ) : deadlines.length > 0 ? (
            <div className="space-y-3">
              {deadlines.map((d) => (
                <div key={d.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-muted/30 transition-all duration-200 group">
                  <div className={`h-12 w-12 rounded-xl flex flex-col items-center justify-center text-[10px] font-medium ${
                    d.urgent
                      ? "bg-gradient-to-br from-red-500/20 to-orange-500/20 text-red-400 border border-red-500/20"
                      : "bg-gradient-to-br from-primary/10 to-accent/10 text-primary border border-primary/20"
                  }`}>
                    {d.date.split(" ")[0]}
                    <span className="font-bold text-sm leading-none mt-0.5">{d.date.split(" ")[1]}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate group-hover:text-primary transition-colors">{d.title}</div>
                    <div className="text-xs text-muted-foreground">{d.company}</div>
                  </div>
                  <div className={`h-2 w-2 rounded-full ${d.urgent ? "bg-red-400 animate-pulse-glow" : "bg-primary/30"}`} />
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Calendar className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No upcoming deadlines</p>
            </div>
          )}
          <div className="mt-4 pt-4 border-t border-border/40">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              Deadlines are synced from your saved opportunities
            </div>
          </div>
        </div>
      </div>

      {/* ── Activity & Agent Feed ── */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Weekly Activity */}
        <div className="bento-card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <h2 className="font-display font-semibold">Weekly Activity</h2>
            </div>
            <Badge variant="outline" className="text-[10px]">
              <TrendingUp className="h-3 w-3 mr-1" />
              {activity.length > 0 ? `${activity.reduce((s: number, d: Record<string, unknown>) => s + Number(d.applications || 0), 0)} actions` : "No data"}
            </Badge>
          </div>
          {activityLoading ? (
            <div className="h-[220px] flex items-center justify-center text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                Loading activity...
              </div>
            </div>
          ) : activity.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={activity}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 12,
                    fontSize: 12,
                    boxShadow: "var(--shadow-elegant)",
                  }}
                />
                <Area type="monotone" dataKey="applications" stroke="hsl(var(--primary))" fill="url(#g1)" strokeWidth={2.5} />
                <Area type="monotone" dataKey="interviews" stroke="hsl(var(--accent))" fill="url(#g2)" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center">
              <div className="text-center">
                <Activity className="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
                <p className="text-sm text-muted-foreground">No activity data yet</p>
              </div>
            </div>
          )}
        </div>

        {/* Agent Activity Feed */}
        <div className="bento-card p-6">
          <div className="flex items-center gap-2 mb-5">
            <Zap className="h-5 w-5 text-primary" />
            <h2 className="font-display font-semibold">Agent Activity</h2>
          </div>
          {tasksLoading ? (
            <ListSkeleton count={6} />
          ) : agentTasks.length > 0 ? (
            <div className="space-y-3 max-h-[260px] overflow-y-auto scrollbar-thin pr-1">
              {agentTasks.map((t) => (
                <div key={t.id} className="flex gap-3 p-2.5 rounded-lg hover:bg-muted/20 transition-colors">
                  <div className={`h-2.5 w-2.5 rounded-full mt-1.5 flex-shrink-0 ${
                    t.status === "running" ? "bg-primary animate-pulse-glow" :
                    t.status === "complete" ? "bg-success" : "bg-muted-foreground/40"
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium capitalize">{t.agent.replace(/_/g, " ")}</div>
                    <div className="text-[11px] text-muted-foreground line-clamp-1">{t.action}</div>
                    <div className="text-[10px] text-muted-foreground/50 mt-0.5">{t.timestamp}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Zap className="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
              <p className="text-sm text-muted-foreground">No agent activity yet</p>
            </div>
          )}
          {agentTasks.length > 0 && (
            <Button variant="ghost" size="sm" className="w-full mt-4 text-xs text-muted-foreground" asChild>
              <Link to="/app/tasks">
                View all tasks <ChevronRight className="h-3 w-3" />
              </Link>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
