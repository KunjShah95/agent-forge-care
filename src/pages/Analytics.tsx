import { Card } from "@/components/ui/card";
import { funnelData, skillDemand, weeklyActivity } from "@/lib/sample-data";
import {
  Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  Line, LineChart, CartesianGrid, Legend,
} from "recharts";

const metrics = [
  { label: "Applications sent", value: "42", change: "+18%" },
  { label: "Interview rate", value: "21%", change: "+4%" },
  { label: "Offer rate", value: "7%", change: "+2%" },
  { label: "Avg response time", value: "4.2d", change: "-1.1d" },
];

export default function Analytics() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="font-display text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground mt-1">Your search, quantified.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <Card key={m.label} className="glass p-5">
            <div className="text-xs text-muted-foreground">{m.label}</div>
            <div className="text-3xl font-display font-bold mt-1">{m.value}</div>
            <div className="text-xs text-success mt-1">{m.change} vs last month</div>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Conversion Funnel</h2>
          <div className="space-y-3">
            {funnelData.map((f, i) => (
              <div key={f.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span>{f.name}</span>
                  <span className="text-muted-foreground">{f.value} · {f.rate}</span>
                </div>
                <div className="h-8 rounded-lg bg-muted/30 overflow-hidden relative">
                  <div
                    className="h-full bg-gradient-primary opacity-90 transition"
                    style={{ width: `${(f.value / funnelData[0].value) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Skill Demand Index</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={skillDemand} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="skill" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={70} />
              <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="demand" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="glass p-6 lg:col-span-2">
          <h2 className="font-display font-semibold mb-4">Weekly Output</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={weeklyActivity}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="day" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="applications" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="interviews" stroke="hsl(var(--accent))" strokeWidth={2.5} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
