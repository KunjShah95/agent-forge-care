import { useMemo } from "react";
import { Card } from "@/components/ui/card";
import {
  Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  Line, LineChart, CartesianGrid, Legend,
} from "recharts";

import { useAnalyticsSummary, useAnalyticsFunnel, useAnalyticsSkillsDemand, useAnalyticsActivity } from "@/api/hooks";
import { StatSkeleton } from "@/components/ui/skeleton";

export default function Analytics() {
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary();
  const { data: funnel, isLoading: funnelLoading } = useAnalyticsFunnel();
  const { data: skillsDemand, isLoading: skillsLoading } = useAnalyticsSkillsDemand();
  const { data: activity, isLoading: activityLoading } = useAnalyticsActivity();

  const metrics = useMemo(() => {
    if (!summary) return null;
    const total = (funnel || []).reduce((s, f) => s + f.value, 0);
    return [
      { label: "Applications sent", value: String(total || summary.applications), change: `Based on ${summary.active_matches} active matches` },
      { label: "Interview rate", value: `${summary.interview_rate}%`, change: "Of applications" },
      { label: "Offer rate", value: funnel && funnel.length > 0 ? `${((funnel[funnel.length - 1]?.value || 0) / (funnel[0]?.value || 1)) * 100}%` : "—", change: "Conversion" },
      { label: "Active matches", value: String(summary.active_matches), change: "Current opportunities" },
    ];
  }, [summary, funnel]);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="font-display text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground mt-1">Your search, quantified.</p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryLoading || !metrics ? (
          Array.from({ length: 4 }).map((_, i) => <StatSkeleton key={i} />)
        ) : (
          metrics.map((m) => (
            <Card key={m.label} className="glass p-5">
              <div className="text-xs text-muted-foreground">{m.label}</div>
              <div className="text-3xl font-display font-bold mt-1">{m.value}</div>
              <div className="text-xs text-success mt-1">{m.change}</div>
            </Card>
          ))
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Funnel */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Conversion Funnel</h2>
          {funnelLoading ? (
            <div className="space-y-4 py-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-8 bg-muted/30 rounded animate-pulse" style={{ width: `${80 - i * 15}%` }} />
              ))}
            </div>
          ) : funnel && funnel.length > 0 ? (
            <div className="space-y-3">
              {funnel.map((f, i) => (
                <div key={f.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{f.name}</span>
                    <span className="text-muted-foreground">{f.value} · {f.rate}</span>
                  </div>
                  <div className="h-8 rounded-lg bg-muted/30 overflow-hidden relative">
                    <div
                      className="h-full bg-gradient-primary opacity-90 transition"
                      style={{ width: `${(f.value / funnel[0].value) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">No funnel data yet</div>
          )}
        </Card>

        {/* Skill Demand */}
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Skill Demand Index</h2>
          {skillsLoading ? (
            <div className="h-[260px] flex items-center justify-center text-sm text-muted-foreground">Loading…</div>
          ) : skillsDemand && skillsDemand.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={skillsDemand} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="skill" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={70} />
                <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="demand" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[260px] flex items-center justify-center text-sm text-muted-foreground">No skill data yet</div>
          )}
        </Card>

        {/* Weekly Activity */}
        <Card className="glass p-6 lg:col-span-2">
          <h2 className="font-display font-semibold mb-4">Weekly Output</h2>
          {activityLoading ? (
            <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">Loading…</div>
          ) : activity && activity.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={activity}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="applications" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="interviews" stroke="hsl(var(--accent))" strokeWidth={2.5} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">No activity data yet</div>
          )}
        </Card>
      </div>
    </div>
  );
}
