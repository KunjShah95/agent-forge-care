import { useState, useMemo, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Search, MapPin, Building2, Sparkles, X, RefreshCw, Target,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import {
  Pagination, PaginationContent, PaginationItem, PaginationLink,
  PaginationPrevious, PaginationNext, PaginationEllipsis,
} from "@/components/ui/pagination";

import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useMatches, useRefreshOpportunities, useCreateApplication } from "@/api/hooks";
import type { ScoredOpportunity } from "@/api/client";

const typeFilters = ["All", "Internship", "Full-time", "Hackathon", "Scholarship", "Fellowship", "Research"];
const sizeFilters = ["All sizes", "Startup", "Mid-size", "Enterprise"];

const ITEMS_PER_PAGE = 9;

export default function Opportunities() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All");
  const [size, setSize] = useState("All sizes");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [selected, setSelected] = useState<ScoredOpportunity | null>(null);
  const [page, setPage] = useState(1);

  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useMatches();
  const refreshMutation = useRefreshOpportunities();
  const createApp = useCreateApplication();

  const filtered = useMemo(() => {
    if (!data?.items) return [];
    const items = data.items;

    return items.filter((o) => {
      const q = query.toLowerCase();
      const matchesQ = !q
        || o.title.toLowerCase().includes(q)
        || o.company.toLowerCase().includes(q)
        || (o.skills_required || []).some((s) => s.toLowerCase().includes(q));
      const matchesT = type === "All" || o.type === type;
      const matchesS = size === "All sizes" || o.company_size === size;
      const matchesR = !remoteOnly || o.remote;
      return matchesQ && matchesT && matchesS && matchesR;
    }).sort((a, b) => b.match_score - a.match_score);
  }, [data, query, type, size, remoteOnly]);

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  useEffect(() => { setPage(1); }, [query, type, size, remoteOnly]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const pageItems = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const salaryDisplay = (o: ScoredOpportunity) => {
    if (o.salary_min && o.salary_max) {
      return `$${(o.salary_min / 1000).toFixed(0)}k–$${(o.salary_max / 1000).toFixed(0)}k`;
    }
    if (o.salary_min) return `From $${(o.salary_min / 1000).toFixed(0)}k`;
    return "";
  };

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Opportunities</h1>
          <p className="text-muted-foreground mt-1">
            {isLoading ? "Loading…" : `${filtered.length} matches from your agent fleet`}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleRefresh}
          disabled={refreshMutation.isPending}
        >
          <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
          {refreshMutation.isPending ? "Scanning…" : "Refresh"}
        </Button>
      </div>

      {/* Filters */}
      <Card className="glass p-4 space-y-4">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by role, company, or skill…"
              className="pl-9"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <Button variant={remoteOnly ? "default" : "outline"} onClick={() => setRemoteOnly(!remoteOnly)}>
            Remote only
          </Button>
          <select
            className="h-10 rounded-md border bg-background px-3 text-sm"
            value={size}
            onChange={(e) => setSize(e.target.value)}
          >
            {sizeFilters.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div className="flex gap-2 flex-wrap">
          {typeFilters.map((t) => (
            <Button
              key={t}
              variant={type === t ? "default" : "outline"}
              size="sm"
              onClick={() => setType(t)}
              className={type === t ? "bg-gradient-primary" : ""}
            >
              {t}
            </Button>
          ))}
        </div>
      </Card>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive flex items-center gap-3">
          <X className="h-4 w-4 shrink-0" />
          {error instanceof Error ? error.message : "Failed to load opportunities"}
          <Button variant="ghost" size="sm" onClick={() => refetch()}>Retry</Button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Target}
          title="No opportunities found"
          description="Try adjusting your filters or search query, or run the agent to find new matches."
          action={
            <Button
              className="bg-gradient-primary shadow-glow gap-2"
              onClick={handleRefresh}
              disabled={refreshMutation.isPending}
            >
              <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
              {refreshMutation.isPending ? "Scanning…" : "Run Agent Search"}
            </Button>
          }
        />
      ) : (
        /* Cards grid */
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {pageItems.map((o) => (
            <Card
              key={o.id}
              className="glass p-5 hover:shadow-glow transition cursor-pointer group"
              onClick={() => setSelected(o)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary">
                    {o.company.charAt(0)}
                  </div>
                  <div>
                    <div className="font-display font-semibold leading-tight group-hover:text-primary transition">
                      {o.title}
                    </div>
                    <div className="text-xs text-muted-foreground">{o.company}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-display font-bold gradient-text">{o.match_score}%</div>
                  <div className="text-[10px] text-muted-foreground">match</div>
                </div>
              </div>
              <Progress value={o.match_score} className="h-1 mb-3" />
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-3">
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> {o.location || "Remote"}
                </span>
                <span className="flex items-center gap-1">
                  <Building2 className="h-3 w-3" /> {o.company_size || "—"}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 mb-3">
                <Badge variant="outline" className="text-[10px]">{o.type}</Badge>
                {(o.skills_required || []).slice(0, 3).map((s) => (
                  <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>
                ))}
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{salaryDisplay(o) || "—"}</span>
                <span className="text-muted-foreground">{o.deadline ? `Due ${o.deadline}` : "Open"}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {filtered.length > ITEMS_PER_PAGE && (
        <div className="flex flex-col items-center gap-3 pt-4">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * ITEMS_PER_PAGE + 1}–{Math.min(page * ITEMS_PER_PAGE, filtered.length)} of{" "}
            {filtered.length}
          </p>
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  onClick={(e) => { e.preventDefault(); setPage(Math.max(1, page - 1)); }}
                  className={page <= 1 ? "pointer-events-none opacity-50" : ""}
                />
              </PaginationItem>
              {Array.from({ length: totalPages }).map((_, i) => {
                const p = i + 1;
                const show = p === 1 || p === totalPages || Math.abs(p - page) <= 1;
                if (!show) {
                  if (p === page - 2 || p === page + 2) {
                    return (
                      <PaginationItem key={p}>
                        <PaginationEllipsis />
                      </PaginationItem>
                    );
                  }
                  return null;
                }
                return (
                  <PaginationItem key={p}>
                    <PaginationLink
                      href="#"
                      isActive={p === page}
                      onClick={(e) => { e.preventDefault(); setPage(p); }}
                    >
                      {p}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}
              <PaginationItem>
                <PaginationNext
                  href="#"
                  onClick={(e) => { e.preventDefault(); setPage(Math.min(totalPages, page + 1)); }}
                  className={page >= totalPages ? "pointer-events-none opacity-50" : ""}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      {/* Detail dialog */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-2xl glass">
          {selected && (
            <>
              <DialogHeader>
                <div className="flex items-start gap-4">
                  <div className="h-14 w-14 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary text-2xl">
                    {selected.company.charAt(0)}
                  </div>
                  <div>
                    <DialogTitle className="font-display text-2xl">{selected.title}</DialogTitle>
                    <p className="text-muted-foreground mt-1">
                      {selected.company} · {selected.location || "Remote"}
                    </p>
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
                    <span className="text-2xl font-display font-bold gradient-text">{selected.match_score}%</span>
                  </div>
                  <div className="space-y-1 text-sm">
                    {(selected.match_reasons || []).map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-muted-foreground">
                        <span className="text-success mt-0.5">✓</span>{r}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><span className="text-muted-foreground">Type:</span> {selected.type}</div>
                  <div><span className="text-muted-foreground">Salary:</span> {salaryDisplay(selected) || "—"}</div>
                  <div><span className="text-muted-foreground">Size:</span> {selected.company_size || "—"}</div>
                  <div><span className="text-muted-foreground">Deadline:</span> {selected.deadline || "Open"}</div>
                </div>
                <div>
                  <div className="text-sm font-medium mb-2">Required skills</div>
                  <div className="flex flex-wrap gap-1.5">
                    {(selected.skills_required || []).map((s) => (
                      <Badge key={s} variant="secondary">{s}</Badge>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button
                    className="bg-gradient-primary shadow-glow flex-1"
                    disabled={createApp.isPending}
                    onClick={() => {
                      createApp.mutate(
                        { opportunity_id: selected.id },
                        {
                          onSuccess: () => {
                            toast.success("Saved to pipeline");
                            setSelected(null);
                          },
                          onError: () => toast.error("Failed to save to pipeline"),
                        },
                      );
                    }}
                  >
                    {createApp.isPending ? "Saving…" : "Save to pipeline"}
                  </Button>
                  <Button variant="outline" className="flex-1" onClick={() => { setSelected(null); navigate("/app/resume"); }}>
                    Tailor resume
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
