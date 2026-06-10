import { useState, useMemo, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import {
  Search, MapPin, Building2, Sparkles, X, RefreshCw, Target,
  TrendingUp, Calendar, DollarSign,
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

const typeIcons: Record<string, string> = {
  Internship: "🎓",
  "Full-time": "💼",
  Hackathon: "⚡",
  Scholarship: "📚",
  Fellowship: "🏆",
  Research: "🔬",
};

function matchColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-primary";
  if (score >= 60) return "text-amber-400";
  return "text-muted-foreground";
}



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
    <div className="space-y-6 max-w-[1400px] relative">
      {/* Animated grid background */}
      <div className="fixed inset-0 animated-grid opacity-40 pointer-events-none" />
      
      {/* Subtle beam overlay */}
      <div className="fixed inset-0 bg-beams opacity-20 pointer-events-none" />

      <div className="relative">
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
            className="gap-2 glass-strong"
            onClick={handleRefresh}
            disabled={refreshMutation.isPending}
          >
            <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
            {refreshMutation.isPending ? "Scanning…" : "Refresh"}
          </Button>
        </div>

        {/* Filters — Bento Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0.1, 0, 1] }}
          className="mt-6"
        >
          <div className="bento-card p-4 space-y-4 relative overflow-hidden">
            {/* Subtle beam line */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
            <div className="relative">
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
              <div className="flex gap-2 flex-wrap mt-3">
                {typeFilters.map((t) => (
                  <Button
                    key={t}
                    variant={type === t ? "default" : "outline"}
                    size="sm"
                    onClick={() => setType(t)}
                    className={type === t ? "bg-gradient-1 shadow-glow" : ""}
                  >
                    {t}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Error state */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-sm text-destructive flex items-center gap-3"
          >
            <X className="h-4 w-4 shrink-0" />
            {error instanceof Error ? error.message : "Failed to load opportunities"}
            <Button variant="ghost" size="sm" onClick={() => refetch()}>Retry</Button>
          </motion.div>
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
                className="bg-gradient-1 shadow-glow gap-2"
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
          <motion.div
            className="grid md:grid-cols-2 xl:grid-cols-3 gap-4"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {
                transition: { staggerChildren: 0.06 },
              },
            }}
          >
            {pageItems.map((o) => {
              const isHighMatch = o.match_score >= 85;
              const CardWrapper = isHighMatch ? "div" : motion.div;
              const wrapperProps = isHighMatch
                ? { className: "glow-card" }
                : {
                    variants: {
                      hidden: { opacity: 0, y: 24 },
                      visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.25, 0.1, 0, 1] } },
                    },
                  };

              return (
                <CardWrapper key={o.id} {...wrapperProps}>
                  <motion.div
                    variants={{
                      hidden: { opacity: 0, y: 24 },
                      visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.25, 0.1, 0, 1] } },
                    }}
                  >
                    <Card
                      className={`bento-card p-5 cursor-pointer group ${
                        isHighMatch ? "!shadow-glow border-primary/30 hover:!shadow-glow-lg" : "hover:shadow-glow"
                      } transition-all duration-300`}
                      onClick={() => setSelected(o)}
                    >
                      {/* Top row: Company logo + Title + Score */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className={`h-11 w-11 rounded-xl flex items-center justify-center font-bold text-lg ${
                            isHighMatch
                              ? "bg-gradient-1 text-primary-foreground shadow-glow"
                              : "bg-gradient-1/10 border border-primary/20 text-primary"
                          }`}>
                            {o.company.charAt(0)}
                          </div>
                          <div className="min-w-0">
                            <div className="font-display font-semibold leading-tight group-hover:text-primary transition flex items-center gap-1.5">
                              {o.title}
                              {isHighMatch && <Sparkles className="h-3.5 w-3.5 text-amber-400 shrink-0" />}
                            </div>
                            <div className="text-xs text-muted-foreground">{o.company}</div>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className={`font-display font-bold text-lg ${matchColor(o.match_score)}`}>
                            {o.match_score}%
                          </div>
                          <div className="text-[10px] text-muted-foreground">match</div>
                        </div>
                      </div>

                      {/* Progress bar with gradient */}
                      <div className="relative mb-3">
                        <Progress value={o.match_score} className="h-1.5 bg-muted/40" />
                      </div>

                      {/* Meta row */}
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-3">
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> {o.location || "Remote"}
                        </span>
                        <span className="flex items-center gap-1">
                          <Building2 className="h-3 w-3" /> {o.company_size || "—"}
                        </span>
                        {o.salary_min && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3" /> {salaryDisplay(o)}
                          </span>
                        )}
                      </div>

                      {/* Badges */}
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        <Badge variant="outline" className="text-[10px] flex items-center gap-1">
                          {typeIcons[o.type] || "📌"} {o.type}
                        </Badge>
                        {(o.skills_required || []).slice(0, 3).map((s) => (
                          <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>
                        ))}
                        {(o.skills_required || []).length > 3 && (
                          <Badge variant="outline" className="text-[10px] text-muted-foreground">
                            +{o.skills_required.length - 3}
                          </Badge>
                        )}
                      </div>

                      {/* Footer */}
                      <div className="flex items-center justify-between text-xs pt-2 border-t border-border/40">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> {o.deadline ? `Due ${o.deadline}` : "Open"}
                        </span>
                        {isHighMatch && (
                          <span className="text-emerald-400 font-medium flex items-center gap-1">
                            <Sparkles className="h-3 w-3" /> Top match
                          </span>
                        )}
                      </div>
                    </Card>
                  </motion.div>
                </CardWrapper>
              );
            })}
          </motion.div>
        )}

        {/* Pagination */}
        {filtered.length > ITEMS_PER_PAGE && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col items-center gap-3 pt-4"
          >
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
          </motion.div>
        )}
      </div>

      {/* Detail dialog */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-2xl glass-strong !p-0 overflow-hidden">
          {selected && (
            <>
              {/* Gradient header */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-b from-primary/10 via-accent/5 to-transparent" />
                <div className="relative p-6 pb-4">
                  <DialogHeader>
                    <div className="flex items-start gap-4">
                      <div className="h-16 w-16 rounded-2xl bg-gradient-1 flex items-center justify-center font-bold text-primary-foreground text-3xl shadow-glow shrink-0">
                        {selected.company.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <DialogTitle className="font-display text-2xl">{selected.title}</DialogTitle>
                        <p className="text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
                          <span>{selected.company}</span>
                          <span className="text-muted-foreground/40">·</span>
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" /> {selected.location || "Remote"}
                          </span>
                        </p>
                      </div>
                      <div className="text-right shrink-0 self-start">
                        <div className={`font-display font-bold text-3xl ${matchColor(selected.match_score)}`}>
                          {selected.match_score}%
                        </div>
                        <div className="text-xs text-muted-foreground">match</div>
                      </div>
                    </div>
                  </DialogHeader>
                </div>
              </div>

              <div className="p-6 pt-0 space-y-5">
                {/* Match Score Section */}
                <div className="p-5 rounded-2xl bg-gradient-to-br from-primary/5 via-primary/[0.02] to-accent/5 border border-primary/10">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      <span className="font-display font-semibold">Why this match?</span>
                    </div>
                    {selected.match_score >= 80 && (
                      <Badge className="bg-gradient-1 text-primary-foreground border-none text-[10px]">
                        Highly recommended
                      </Badge>
                    )}
                  </div>
                  <div className="space-y-2 text-sm">
                    {(selected.match_reasons || []).map((r, i) => (
                      <div key={i} className="flex items-start gap-2.5 text-muted-foreground">
                        <span className="h-5 w-5 rounded-full bg-success/10 text-success flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                          ✓
                        </span>
                        <span>{r}</span>
                      </div>
                    ))}
                    {(!selected.match_reasons || selected.match_reasons.length === 0) && (
                      <div className="text-sm text-muted-foreground italic">No detailed match reasons available.</div>
                    )}
                  </div>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bento-card p-4">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" /> Type
                    </div>
                    <div className="font-medium flex items-center gap-1.5">
                      {typeIcons[selected.type] || "📌"} {selected.type}
                    </div>
                  </div>
                  <div className="bento-card p-4">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <DollarSign className="h-3 w-3" /> Salary
                    </div>
                    <div className="font-medium">{salaryDisplay(selected) || "—"}</div>
                  </div>
                  <div className="bento-card p-4">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <Building2 className="h-3 w-3" /> Company size
                    </div>
                    <div className="font-medium">{selected.company_size || "—"}</div>
                  </div>
                  <div className="bento-card p-4">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <Calendar className="h-3 w-3" /> Deadline
                    </div>
                    <div className="font-medium">{selected.deadline || "Open"}</div>
                  </div>
                </div>

                {/* Skills */}
                <div>
                  <div className="text-sm font-medium mb-2.5">Required skills</div>
                  <div className="flex flex-wrap gap-1.5">
                    {(selected.skills_required || []).map((s) => (
                      <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                    ))}
                    {(!selected.skills_required || selected.skills_required.length === 0) && (
                      <span className="text-sm text-muted-foreground italic">No skills listed</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-2 border-t border-border/40">
                  <Button
                    className="bg-gradient-1 shadow-glow flex-1 h-11"
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
                  <Button variant="outline" className="flex-1 h-11" onClick={() => { setSelected(null); navigate("/app/resume"); }}>
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
