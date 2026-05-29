import { useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { opportunities, type Opportunity } from "@/lib/sample-data";
import { Search, MapPin, Building2, Sparkles, X } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";

const typeFilters = ["All", "Internship", "Full-time", "Hackathon", "Scholarship", "Fellowship", "Research"];
const sizeFilters = ["All sizes", "Startup", "Mid-size", "Enterprise"];

export default function Opportunities() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All");
  const [size, setSize] = useState("All sizes");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [selected, setSelected] = useState<Opportunity | null>(null);

  const filtered = useMemo(() => opportunities.filter(o => {
    const matchesQ = (o.title + o.company + o.skills.join(" ")).toLowerCase().includes(query.toLowerCase());
    const matchesT = type === "All" || o.type === type;
    const matchesS = size === "All sizes" || o.companySize === size;
    const matchesR = !remoteOnly || o.remote;
    return matchesQ && matchesT && matchesS && matchesR;
  }), [query, type, size, remoteOnly]);

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="font-display text-3xl font-bold">Opportunities</h1>
        <p className="text-muted-foreground mt-1">{filtered.length} matches from your agent fleet</p>
      </div>

      {/* Filters */}
      <Card className="glass p-4 space-y-4">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search by role, company, or skill…" className="pl-9" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <Button variant={remoteOnly ? "default" : "outline"} onClick={() => setRemoteOnly(!remoteOnly)}>
            Remote only
          </Button>
          <select className="h-10 rounded-md border bg-background px-3 text-sm" value={size} onChange={e => setSize(e.target.value)}>
            {sizeFilters.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div className="flex gap-2 flex-wrap">
          {typeFilters.map((t) => (
            <Button key={t} variant={type === t ? "default" : "outline"} size="sm" onClick={() => setType(t)}
              className={type === t ? "bg-gradient-primary" : ""}>
              {t}
            </Button>
          ))}
        </div>
      </Card>

      {/* Cards grid */}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((o) => (
          <Card key={o.id} className="glass p-5 hover:shadow-glow transition cursor-pointer group" onClick={() => setSelected(o)}>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="text-3xl">{o.logo}</div>
                <div>
                  <div className="font-display font-semibold leading-tight group-hover:text-primary transition">{o.title}</div>
                  <div className="text-xs text-muted-foreground">{o.company}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-display font-bold gradient-text">{o.matchScore}%</div>
                <div className="text-[10px] text-muted-foreground">match</div>
              </div>
            </div>
            <Progress value={o.matchScore} className="h-1 mb-3" />
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-3">
              <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {o.location}</span>
              <span className="flex items-center gap-1"><Building2 className="h-3 w-3" /> {o.companySize}</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-3">
              <Badge variant="outline" className="text-[10px]">{o.type}</Badge>
              {o.skills.slice(0, 3).map(s => <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>)}
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{o.salary || "—"}</span>
              <span className="text-muted-foreground">Due {o.deadline}</span>
            </div>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <X className="h-8 w-8 mx-auto mb-2 opacity-40" />
          No opportunities match your filters.
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-2xl glass">
          {selected && (
            <>
              <DialogHeader>
                <div className="flex items-start gap-4">
                  <div className="text-5xl">{selected.logo}</div>
                  <div>
                    <DialogTitle className="font-display text-2xl">{selected.title}</DialogTitle>
                    <p className="text-muted-foreground mt-1">{selected.company} · {selected.location}</p>
                  </div>
                </div>
              </DialogHeader>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-gradient-primary/10 border border-primary/20">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-primary" />
                      <span className="font-display font-semibold">Match Score</span>
                    </div>
                    <span className="text-2xl font-display font-bold gradient-text">{selected.matchScore}%</span>
                  </div>
                  <div className="space-y-1 text-sm">
                    {selected.matchReasons.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-muted-foreground">
                        <span className="text-success mt-0.5">✓</span>{r}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><span className="text-muted-foreground">Type:</span> {selected.type}</div>
                  <div><span className="text-muted-foreground">Salary:</span> {selected.salary || "—"}</div>
                  <div><span className="text-muted-foreground">Size:</span> {selected.companySize}</div>
                  <div><span className="text-muted-foreground">Deadline:</span> {selected.deadline}</div>
                </div>
                <div>
                  <div className="text-sm font-medium mb-2">Required skills</div>
                  <div className="flex flex-wrap gap-1.5">
                    {selected.skills.map(s => <Badge key={s} variant="secondary">{s}</Badge>)}
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button className="bg-gradient-primary shadow-glow flex-1">Save to pipeline</Button>
                  <Button variant="outline" className="flex-1">Tailor resume</Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
