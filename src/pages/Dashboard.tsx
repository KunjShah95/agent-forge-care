import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Briefcase, Target, TrendingUp, Calendar,
  Brain, Activity, Radar, Clock, Zap, ChevronRight, Sparkles,
} from "lucide-react";
import {
  Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import {
  useAuth, useProfile, useRunPlanner, useMatches, useAgentTasks,
  useAnalyticsSummary, useAnalyticsActivity, useAnalyticsFunnel, useOpportunities,
} from "@/api/hooks";
import { StatSkeleton } from "@/components/ui/skeleton";

const BORDER = "rgba(255,255,255,0.08)";
const CARD = "rgba(255,255,255,0.03)";
const MUTED = "hsl(240, 4%, 60%)";

function Cell({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={className}
      style={{ background: CARD, border: `1px solid ${BORDER}` }}
    >
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] tracking-widest uppercase mb-4" style={{ color: "rgba(255,255,255,0.3)" }}>
      {children}
    </p>
  );
}

const STATUS_COLOR: Record<string, string> = {
  running: "hsl(200, 70%, 55%)",
  complete: "hsl(152, 60%, 48%)",
  queued:   "rgba(255,255,255,0.25)",
};

export default function Dashboard() {
  const { data: auth }      = useAuth();
  const { data: profile }   = useProfile();
  const runPlanner          = useRunPlanner();
  const { data: matchesData,  isLoading: matchesLoading  } = useMatches();
  const { data: tasksData,    isLoading: tasksLoading    } = useAgentTasks();
  const { data: analytics,    isLoading: analyticsLoading} = useAnalyticsSummary();
  const { data: activityData, isLoading: activityLoading } = useAnalyticsActivity();
  const { data: funnelData                                } = useAnalyticsFunnel();
  const { data: oppsData,     isLoading: oppsLoading     } = useOpportunities();

  const topMatches = useMemo(() => {
    if (!matchesData?.items) return [];
    return matchesData.items.slice(0, 6).map((m) => ({
      id: m.id,
      title: m.title,
      company: m.company,
      location: m.location || "Remote",
      salary: m.salary_min && m.salary_max
        ? `$${(m.salary_min / 1000).toFixed(0)}k–$${(m.salary_max / 1000).toFixed(0)}k`
        : null,
      score: m.match_score,
    }));
  }, [matchesData]);

  const deadlines = useMemo(() => {
    if (!oppsData?.items) return [];
    return oppsData.items
      .filter((o) => o.deadline)
      .sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime())
      .slice(0, 6)
      .map((o) => {
        const d = new Date(o.deadline!);
        const urgent = d.getTime() - Date.now() < 3 * 24 * 60 * 60 * 1000;
        return {
          id: o.id,
          title: o.title,
          company: o.company,
          date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          urgent,
        };
      });
  }, [oppsData]);

  const pipeline = useMemo(
    () => (funnelData ?? []).map((f) => ({ stage: f.name, count: f.value })),
    [funnelData]
  );

  const agentTasks = useMemo(() => {
    if (!tasksData?.items) return [];
    return tasksData.items.slice(0, 8).map((t) => ({
      id: t.id,
      agent: t.agent_type.replace(/_/g, " "),
      action: t.input?.goal
        ? String(t.input.goal)
        : t.output?.message
        ? String(t.output.message)
        : t.status,
      status: t.status === "running" ? "running" : t.status === "completed" ? "complete" : "queued",
      time: t.created_at ? new Date(t.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "",
    }));
  }, [tasksData]);

  const stats = useMemo(() => {
    if (!analytics) return null;
    return [
      { label: "Active matches",    value: analytics.active_matches, icon: Target },
      { label: "Applications sent", value: analytics.applications,   icon: Briefcase },
      { label: "Interview rate",    value: `${analytics.interview_rate}%`, icon: TrendingUp },
      { label: "Deadlines",         value: analytics.deadlines,       icon: Calendar },
    ];
  }, [analytics]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const name = profile?.full_name || auth?.full_name || null;

  const pipelineMax = pipeline.length ? Math.max(...pipeline.map((p) => p.count)) : 1;

  return (
    <div className="p-6 space-y-6 max-w-[1440px]">

      {/* ── Header row ── */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1
            className="text-3xl font-normal text-white"
            style={{ fontFamily: "'Instrument Serif', serif", letterSpacing: "-0.03em" }}
          >
            {greeting}{name ? `, ${name}` : ""}.
          </h1>
          <p className="text-sm mt-1" style={{ color: MUTED }}>
            Your agents are running. Here's where things stand.
          </p>
        </div>
        <button
          className="flex items-center gap-2 px-4 py-2 rounded text-sm transition-colors"
          style={{
            background: "rgba(255,255,255,0.07)",
            border: `1px solid ${BORDER}`,
            color: runPlanner.isPending ? MUTED : "white",
          }}
          onClick={() => runPlanner.mutate("Plan my job search strategy for this week")}
          disabled={runPlanner.isPending}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {runPlanner.isPending ? "Running…" : "Run Planner"}
        </button>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-px" style={{ border: `1px solid ${BORDER}` }}>
        {analyticsLoading || !stats
          ? Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
          : stats.map((s) => (
              <div
                key={s.label}
                className="px-6 py-5 flex flex-col gap-1"
                style={{ background: CARD, borderRight: `1px solid ${BORDER}` }}
              >
                <p className="text-[10px] tracking-widest uppercase" style={{ color: MUTED }}>
                  {s.label}
                </p>
                <p
                  className="text-4xl font-normal text-white mt-1"
                  style={{ fontFamily: "'Instrument Serif', serif" }}
                >
                  {s.value}
                </p>
              </div>
            ))}
      </div>

      {/* ── Main grid ── */}
      <div className="grid lg:grid-cols-3 gap-6">

        {/* Top matches — spans 2 cols */}
        <Cell className="rounded-lg p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>Top matches</SectionLabel>
            <Link
              to="/app/opportunities"
              className="text-xs flex items-center gap-1 transition-colors hover:text-white"
              style={{ color: MUTED }}
            >
              See all <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          {matchesLoading ? (
            <p className="text-sm py-8 text-center" style={{ color: MUTED }}>Loading…</p>
          ) : topMatches.length > 0 ? (
            <div>
              {topMatches.map((m, i) => (
                <div
                  key={m.id}
                  className="flex items-center gap-4 py-3 transition-colors hover:bg-white/[0.03] -mx-2 px-2 rounded"
                  style={{ borderBottom: i < topMatches.length - 1 ? `1px solid ${BORDER}` : "none" }}
                >
                  <div
                    className="h-8 w-8 rounded flex items-center justify-center text-xs font-medium flex-shrink-0"
                    style={{ background: "rgba(255,255,255,0.07)", color: "white" }}
                  >
                    {m.company.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium truncate">{m.title}</p>
                    <p className="text-xs truncate mt-0.5" style={{ color: MUTED }}>
                      {m.company} · {m.location}
                      {m.salary ? ` · ${m.salary}` : ""}
                    </p>
                  </div>
                  <p
                    className="text-xl font-normal flex-shrink-0"
                    style={{ fontFamily: "'Instrument Serif', serif", color: "white" }}
                  >
                    {m.score}%
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Target className="h-8 w-8 mx-auto mb-3" style={{ color: MUTED, opacity: 0.4 }} />
              <p className="text-sm" style={{ color: MUTED }}>
                No matches yet — run the planner to start.
              </p>
            </div>
          )}
        </Cell>

        {/* Deadlines */}
        <Cell className="rounded-lg p-6">
          <SectionLabel>Upcoming deadlines</SectionLabel>
          {oppsLoading ? (
            <p className="text-sm py-8 text-center" style={{ color: MUTED }}>Loading…</p>
          ) : deadlines.length > 0 ? (
            <div className="space-y-1">
              {deadlines.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center gap-3 py-2.5 -mx-1 px-1 rounded transition-colors hover:bg-white/[0.03]"
                >
                  <p
                    className="text-xs font-mono w-14 flex-shrink-0"
                    style={{ color: d.urgent ? "hsl(0, 70%, 65%)" : MUTED }}
                  >
                    {d.date}
                  </p>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate">{d.title}</p>
                    <p className="text-xs truncate" style={{ color: MUTED }}>{d.company}</p>
                  </div>
                  {d.urgent && (
                    <div className="h-1.5 w-1.5 rounded-full flex-shrink-0 bg-red-400" />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <Calendar className="h-8 w-8 mx-auto mb-3" style={{ color: MUTED, opacity: 0.4 }} />
              <p className="text-sm" style={{ color: MUTED }}>No upcoming deadlines</p>
            </div>
          )}
          <div className="mt-4 pt-4 flex items-center gap-1.5 text-xs" style={{ borderTop: `1px solid ${BORDER}`, color: MUTED }}>
            <Clock className="h-3 w-3" />
            Synced from saved opportunities
          </div>
        </Cell>
      </div>

      {/* ── Second row ── */}
      <div className="grid lg:grid-cols-3 gap-6">

        {/* Weekly activity chart — 2 cols */}
        <Cell className="rounded-lg p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>Weekly activity</SectionLabel>
            <div className="flex items-center gap-4 text-[10px]" style={{ color: MUTED }}>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: "hsl(200,70%,55%)" }} />
                Applications
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: "rgba(255,255,255,0.3)" }} />
                Interviews
              </span>
            </div>
          </div>

          {activityLoading ? (
            <div className="h-48 flex items-center justify-center text-sm" style={{ color: MUTED }}>
              Loading…
            </div>
          ) : activityData && activityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={activityData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(200,70%,55%)" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(200,70%,55%)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gB" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgba(255,255,255,0.4)" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="rgba(255,255,255,0.4)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
                <XAxis dataKey="day" tick={{ fontSize: 10, fill: MUTED }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: MUTED }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(210,22%,8%)",
                    border: `1px solid ${BORDER}`,
                    borderRadius: 6,
                    fontSize: 12,
                    color: "white",
                  }}
                />
                <Area type="monotone" dataKey="applications" stroke="hsl(200,70%,55%)" fill="url(#gA)" strokeWidth={1.5} />
                <Area type="monotone" dataKey="interviews"   stroke="rgba(255,255,255,0.35)" fill="url(#gB)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center">
              <div className="text-center">
                <Activity className="h-8 w-8 mx-auto mb-2" style={{ color: MUTED, opacity: 0.4 }} />
                <p className="text-sm" style={{ color: MUTED }}>No activity yet</p>
              </div>
            </div>
          )}
        </Cell>

        {/* Agent activity feed */}
        <Cell className="rounded-lg p-6">
          <SectionLabel>Agent activity</SectionLabel>

          {tasksLoading ? (
            <p className="text-sm py-8 text-center" style={{ color: MUTED }}>Loading…</p>
          ) : agentTasks.length > 0 ? (
            <div className="space-y-3 max-h-56 overflow-y-auto pr-1" style={{ scrollbarWidth: "none" }}>
              {agentTasks.map((t) => (
                <div key={t.id} className="flex gap-2.5 items-start">
                  <div
                    className="h-1.5 w-1.5 rounded-full flex-shrink-0 mt-1.5"
                    style={{ background: STATUS_COLOR[t.status] ?? MUTED }}
                  />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-white capitalize">{t.agent}</p>
                    <p className="text-[11px] leading-relaxed line-clamp-2 mt-0.5" style={{ color: MUTED }}>
                      {t.action}
                    </p>
                    {t.time && (
                      <p className="text-[10px] mt-0.5 font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
                        {t.time}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-10 text-center">
              <Zap className="h-8 w-8 mx-auto mb-2" style={{ color: MUTED, opacity: 0.4 }} />
              <p className="text-sm" style={{ color: MUTED }}>No agent activity yet</p>
            </div>
          )}

          {agentTasks.length > 0 && (
            <Link
              to="/app/tasks"
              className="flex items-center gap-1 text-xs mt-4 pt-4 transition-colors hover:text-white"
              style={{ borderTop: `1px solid ${BORDER}`, color: MUTED }}
            >
              All tasks <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </Cell>
      </div>

      {/* ── Pipeline bar ── */}
      {pipeline.length > 0 && (
        <Cell className="rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>Application pipeline</SectionLabel>
            <Link
              to="/app/applications"
              className="text-xs flex items-center gap-1 transition-colors hover:text-white"
              style={{ color: MUTED }}
            >
              View board <ChevronRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {pipeline.map((p) => (
              <div key={p.stage}>
                <div className="flex items-end justify-between mb-2">
                  <p className="text-[10px] uppercase tracking-widest" style={{ color: MUTED }}>
                    {p.stage}
                  </p>
                  <p
                    className="text-lg font-normal text-white"
                    style={{ fontFamily: "'Instrument Serif', serif" }}
                  >
                    {p.count}
                  </p>
                </div>
                <div className="h-1 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(p.count / pipelineMax) * 100}%`,
                      background: "rgba(255,255,255,0.4)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Cell>
      )}

      {/* ── Planner reasoning ── */}
      <Cell className="rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <SectionLabel>Planner — today's reasoning</SectionLabel>
          {agentTasks.some((t) => t.status === "running") && (
            <span className="text-[10px] tracking-widest uppercase" style={{ color: "hsl(200,70%,55%)" }}>
              Active
            </span>
          )}
        </div>

        {agentTasks.filter((t) => t.agent.includes("planner") || t.agent.includes("research")).slice(0, 3).length > 0 ? (
          <div className="space-y-3">
            {agentTasks
              .filter((t) => t.agent.includes("planner") || t.agent.includes("research"))
              .slice(0, 3)
              .map((t) => (
                <div
                  key={t.id}
                  className="flex gap-3 p-3 rounded"
                  style={{ background: "rgba(255,255,255,0.03)", borderLeft: `2px solid rgba(255,255,255,0.15)` }}
                >
                  <Brain className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: MUTED }} />
                  <div>
                    <p className="text-sm text-white capitalize">{t.agent}</p>
                    <p className="text-xs mt-0.5 leading-relaxed" style={{ color: MUTED }}>{t.action}</p>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="py-8 text-center">
            <Brain className="h-8 w-8 mx-auto mb-3" style={{ color: MUTED, opacity: 0.4 }} />
            <p className="text-sm mb-4" style={{ color: MUTED }}>
              No reasoning yet. Run the planner to generate a strategy.
            </p>
            <button
              className="flex items-center gap-2 px-4 py-2 rounded text-sm mx-auto transition-colors"
              style={{
                background: "rgba(255,255,255,0.07)",
                border: `1px solid ${BORDER}`,
                color: "white",
              }}
              onClick={() => runPlanner.mutate("Plan my job search strategy for this week")}
              disabled={runPlanner.isPending}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {runPlanner.isPending ? "Running…" : "Run Planner Agent"}
            </button>
          </div>
        )}
      </Cell>
    </div>
  );
}
