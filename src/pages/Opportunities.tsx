import { useState, useMemo, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import {
  Search, MapPin, Building2, Sparkles, X, RefreshCw, Target,
  TrendingUp, Calendar, DollarSign, Globe, Layers, Trophy,
  ExternalLink, Clock, MapIcon, LayoutGrid,
} from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
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

import { DayPicker } from "react-day-picker";
import { format, parseISO } from "date-fns";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useMatches, useRefreshOpportunities, useCreateApplication, useHackathons, useFilterOptions, useLocations, useScanHackathons, useProfile } from "@/api/hooks";
import type { ScoredOpportunity, HackathonResult, HackathonMatch } from "@/api/client";
import OpportunityMap from "@/components/OpportunityMap";
import type { LocationPoint } from "@/components/OpportunityMap";

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
};  function matchColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 75) return "text-primary";
  if (score >= 60) return "text-amber-400";
  return "text-muted-foreground";
}

function skillColor(score: number): string {
  if (score >= 75) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
  if (score >= 50) return "text-amber-400 border-amber-500/30 bg-amber-500/10";
  if (score >= 25) return "text-primary border-primary/20 bg-primary/10";
  return "text-muted-foreground border-border/30 bg-muted/30";
}

export default function Opportunities() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("All");
  const [size, setSize] = useState("All sizes");
  const [workType, setWorkType] = useState<string>("all");
  const [cityFilter, setCityFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [industryFilter, setIndustryFilter] = useState("");
  const [showHackathons, setShowHackathons] = useState(false);
  const [hackathonAlerts, setHackathonAlerts] = useState(() => localStorage.getItem("hackathon_alert_enabled") === "true");
  const [emailAlerts, setEmailAlerts] = useState(() => localStorage.getItem("hackathon_email_enabled") === "true");
  const [hackathonSearch, setHackathonSearch] = useState("");
  const [hackathonGroupFilter, setHackathonGroupFilter] = useState<string>("all");
  const [alertKeywords, setAlertKeywords] = useState(() => localStorage.getItem("hackathon_alert_keywords") || "");
  const [recentMatches, setRecentMatches] = useState<HackathonMatch[]>(() => {
    try { return JSON.parse(localStorage.getItem("hackathon_recent_matches") || "[]"); }
    catch { return []; }
  });
  const [viewMode, setViewMode] = useState<"cards" | "map">("cards");
  const [hackathonViewMode, setHackathonViewMode] = useState<"cards" | "calendar">("cards");
  const [selectedDeadlineDate, setSelectedDeadlineDate] = useState<Date | undefined>(undefined);
  const [selected, setSelected] = useState<ScoredOpportunity | null>(null);
  const [page, setPage] = useState(1);
  const [isPolling, setIsPolling] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevCountRef = useRef(0);

  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useMatches();
  const refreshMutation = useRefreshOpportunities();
  const createApp = useCreateApplication();
  const { data: hackathonData, isLoading: hackathonLoading } = useHackathons();
  const { data: filterOptions } = useFilterOptions();
  const { data: locationData, isLoading: locationsLoading } = useLocations();
  const { data: profile } = useProfile();
  const scanHackathons = useScanHackathons();

  // Persist alert settings to localStorage
  const toggleHackathonAlert = (enabled: boolean) => {
    setHackathonAlerts(enabled);
    localStorage.setItem("hackathon_alert_enabled", String(enabled));
    if (enabled) {
      toast.success("Hackathon alerts enabled — scanning now…");
      const opts: { alert_enabled: boolean; email_enabled?: boolean } = {
        alert_enabled: true,
        email_enabled: emailAlerts || undefined,
      };
      scanHackathons.mutate(opts, {
        onSuccess: (res) => {
          if (res.new_matches.length > 0) {
            setRecentMatches(res.new_matches);
            localStorage.setItem("hackathon_recent_matches", JSON.stringify(res.new_matches));
            toast.success(res.message);
          }
        },
      });
    }
  };

  const toggleEmailAlerts = (enabled: boolean) => {
    setEmailAlerts(enabled);
    localStorage.setItem("hackathon_email_enabled", String(enabled));
    // Persist to backend when alerts are already enabled
    if (hackathonAlerts) {
      scanHackathons.mutate(
        { email_enabled: enabled },
        {
          onSuccess: (res) => {
            toast.success(enabled ? "Email notifications enabled" : "Email notifications disabled");
          },
          onError: () => {
            toast.error("Failed to update email preference");
            setEmailAlerts(!enabled);
            localStorage.setItem("hackathon_email_enabled", String(!enabled));
          },
        }
      );
    }
  };

  const handleScanHackathons = () => {
    const skills = alertKeywords
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const opts: { skills?: string[] } = {};
    if (skills.length > 0) opts.skills = skills;
    scanHackathons.mutate(opts, {
      onSuccess: (res) => {
        if (res.new_matches.length > 0) {
          setRecentMatches(res.new_matches);
          localStorage.setItem("hackathon_recent_matches", JSON.stringify(res.new_matches));
        }
        toast.success(res.message || "Scan complete");
      },
      onError: () => toast.error("Failed to scan hackathons"),
    });
  };

  const clearRecentMatches = () => {
    setRecentMatches([]);
    localStorage.removeItem("hackathon_recent_matches");
  };

  const filtered = useMemo(() => {
    if (!data?.items) return [];
    const items = data.items;

    // Deduplicate by title + company to avoid showing the same opportunity twice
    const seen = new Set<string>();
    return items.filter((o) => {
      const key = `${o.title.toLowerCase()}|${o.company.toLowerCase()}`;
      if (seen.has(key)) return false;
      seen.add(key);
      const q = query.toLowerCase().trim();
      const matchesQ = !q || (() => {
        const tokens = q.split(/\s+/).filter(Boolean);
        const raw = `${o.title} ${o.company} ${(o.skills_required || []).join(" ")}`.toLowerCase();
        const normalized = raw.replace(/[/.,-]+/g, "");
        return tokens.every((t) => raw.includes(t) || normalized.includes(t));
      })();
      const matchesT = type === "All" || o.type === type;
      const matchesS = size === "All sizes" || o.company_size === size;
      const matchesR = workType === "all" || (workType === "remote" && o.remote) || (workType === "hybrid" && o.work_type === "hybrid") || (workType === "onsite" && (o.work_type === "onsite" || (!o.remote && o.work_type !== "hybrid")));
      const matchesCity = !cityFilter || (o.city && o.city.toLowerCase().includes(cityFilter.toLowerCase()));
      const matchesState = !stateFilter || (o.state && o.state.toLowerCase().includes(stateFilter.toLowerCase()));
      const matchesCountry = !countryFilter || (o.country && o.country.toLowerCase().includes(countryFilter.toLowerCase()));
      const matchesIndustry = !industryFilter || (o.industry && o.industry.toLowerCase().includes(industryFilter.toLowerCase()));
      return matchesQ && matchesT && matchesS && matchesR && matchesCity && matchesState && matchesCountry && matchesIndustry;
    }).sort((a, b) => b.match_score - a.match_score);
  }, [data, query, type, size,    workType, cityFilter, stateFilter, countryFilter, industryFilter]);

  // Poll for results after triggering an async scan
  useEffect(() => {
    if (!isPolling) return;
    prevCountRef.current = data?.items?.length ?? 0;
    const maxWait = 180_000;
    const interval = setInterval(() => { refetch(); }, 3000);
    pollTimer.current = interval;
    const safety = setTimeout(() => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      setIsPolling(false);
    }, maxWait);
    return () => {
      clearInterval(interval);
      clearTimeout(safety);
      pollTimer.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPolling]);

  // Stop polling once we get MORE results than when polling started
  useEffect(() => {
    if (isPolling && (data?.items?.length ?? 0) > prevCountRef.current) {
      if (pollTimer.current) clearInterval(pollTimer.current);
      setIsPolling(false);
    }
  }, [isPolling, data?.items?.length]);

  const handleRefresh = () => {
    refreshMutation.mutate(query || undefined, {
      onSuccess: () => setIsPolling(true),
    });
  };

  useEffect(() => { setPage(1); }, [query, type, size,    workType, cityFilter, stateFilter, countryFilter, industryFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const pageItems = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const salaryDisplay = (o: ScoredOpportunity) => {
    if (o.salary_min && o.salary_max) {
      return `$${(o.salary_min / 1000).toFixed(0)}k–$${(o.salary_max / 1000).toFixed(0)}k`;
    }
    if (o.salary_min) return `From $${(o.salary_min / 1000).toFixed(0)}k`;
    return "";
  };

  // ── Urgency helpers ──
  function parseDeadline(d: string | undefined): Date | null {
    if (!d) return null;
    try {
      const dt = parseISO(d.slice(0, 10));
      return isNaN(dt.getTime()) ? null : dt;
    } catch {
      return null;
    }
  }

  // Combine saved + search hackathons
  const allHackathons = useMemo(() => {
    const results: HackathonResult[] = [];
    if (hackathonData?.saved) results.push(...hackathonData.saved);
    if (hackathonData?.from_search) {
      // Only add from_search entries that aren't already saved (dedup by title)
      const savedTitles = new Set(hackathonData.saved.map((h) => h.title.toLowerCase()));
      for (const h of hackathonData.from_search) {
        if (!savedTitles.has(h.title.toLowerCase())) {
          results.push(h);
        }
      }
    }
    return results;
  }, [hackathonData]);

  // Filter hackathons by search query
  const filteredHackathons = useMemo(() => {
    if (!hackathonSearch.trim()) return allHackathons;
    const q = hackathonSearch.toLowerCase();
    return allHackathons.filter(
      (h) =>
        h.title.toLowerCase().includes(q) ||
        h.company.toLowerCase().includes(q)
    );
  }, [allHackathons, hackathonSearch]);

  // ── Calendar deadline map ──
  const deadlineMap = useMemo(() => {
    const map = new Map<string, HackathonResult[]>();
    for (const h of filteredHackathons) {
      if (!h.deadline) continue;
      const normalized = h.deadline.slice(0, 10);
      if (!map.has(normalized)) map.set(normalized, []);
      map.get(normalized)!.push(h);
    }
    return map;
  }, [filteredHackathons]);

  const deadlineDates = useMemo(() => {
    return Array.from(deadlineMap.keys()).map((d) => {
      try { return parseISO(d); } catch { return new Date(d); }
    }).filter((d) => !isNaN(d.getTime()));
  }, [deadlineMap]);

  const selectedDayHackathons = useMemo(() => {
    if (!selectedDeadlineDate) return [];
    const key = format(selectedDeadlineDate, "yyyy-MM-dd");
    return deadlineMap.get(key) || [];
  }, [selectedDeadlineDate, deadlineMap]);

  // ── Group hackathons by urgency ──
  const groupedHackathons = useMemo(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const weekEnd = new Date(now);
    weekEnd.setDate(weekEnd.getDate() + 7);
    const monthEnd = new Date(now);
    monthEnd.setMonth(monthEnd.getMonth() + 1);

    const groups: { label: string; icon: string; color: string; items: HackathonResult[] }[] = [
      { label: "Urgent — Overdue & This Week", icon: "🔴", color: "from-red-500/20 to-red-600/10", items: [] },
      { label: "Due This Month", icon: "🟡", color: "from-amber-500/20 to-orange-500/10", items: [] },
      { label: "Due Later", icon: "📅", color: "from-blue-500/20 to-cyan-500/10", items: [] },
      { label: "No Deadline", icon: "📌", color: "from-muted-foreground/20 to-muted/10", items: [] },
    ];
    for (const h of filteredHackathons) {
      const dl = parseDeadline(h.deadline);
      if (dl && dl <= weekEnd) {
        groups[0].items.push(h);  // Past-due + this week = most urgent
      } else if (dl && dl <= monthEnd) {
        groups[1].items.push(h);
      } else if (dl && dl > monthEnd) {
        groups[2].items.push(h);
      } else {
        groups[3].items.push(h);
      }
    }
    return groups;
  }, [filteredHackathons]);

  // ── Skill-match scores for hackathon cards ──
  const userSkillNames = useMemo(() => {
    return new Set((profile?.skills || []).map((s) => s.skill.name.toLowerCase()));
  }, [profile]);

  function computeSkillMatch(h: HackathonResult): number {
    const skills = (h.skills_required || []).map((s) => s.toLowerCase());
    if (skills.length === 0) return 0;
    let matches = 0;
    for (const s of skills) {
      if (userSkillNames.has(s)) matches++;
    }
    return Math.round((matches / skills.length) * 100);
  }

  // Month with the most deadlines — used as defaultMonth for DayPicker
  const busiestMonth = useMemo(() => {
    if (deadlineDates.length === 0) return undefined;
    const monthCount = new Map<string, number>();
    for (const d of deadlineDates) {
      const key = format(d, "yyyy-MM");
      monthCount.set(key, (monthCount.get(key) || 0) + 1);
    }
    let maxKey = "";
    let maxCount = 0;
    for (const [key, count] of monthCount) {
      if (count > maxCount) { maxKey = key; maxCount = count; }
    }
    try { return parseISO(maxKey + "-01"); } catch { return undefined; }
  }, [deadlineDates]);

  return (
    <div className="space-y-6 max-w-[1400px] relative">
      {/* Animated grid background */}
      <div className="fixed inset-0 animated-grid opacity-40 pointer-events-none" />
      <div className="fixed inset-0 bg-beams opacity-20 pointer-events-none" />

      <div className="relative">
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold">Opportunities</h1>
            <p className="text-muted-foreground mt-1">
              {isLoading ? "Loading…" : `${filtered.length} matches from your agent fleet`}
            </p>
          </div>
          <div className="flex gap-2">
            {/* View mode toggle */}
            <Button
              variant={viewMode === "map" ? "default" : "outline"}
              size="sm"
              className="gap-2"
              onClick={() => setViewMode(viewMode === "cards" ? "map" : "cards")}
            >
              {viewMode === "map" ? (
                <><LayoutGrid className="h-4 w-4" /> Cards</>
              ) : (
                <><MapIcon className="h-4 w-4" /> Map</>
              )}
            </Button>
            <Button
              variant={showHackathons ? "default" : "outline"}
              size="sm"
              className="gap-2"
              onClick={() => setShowHackathons(!showHackathons)}
            >
              <Trophy className="h-4 w-4" />
              {showHackathons ? "Hide Hackathons" : `Hackathons (${allHackathons.length})`}
            </Button>
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
        </div>

        {/* Filters — Bento Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0.1, 0, 1] }}
          className="mt-6"
        >
          <div className="bento-card p-4 space-y-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
            <div className="relative">
              {/* Row 1: Search + Quick toggles */}
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
                <div className="flex items-center gap-1">
                  {[
                    { key: "all", label: "All" },
                    { key: "remote", label: "Remote" },
                    { key: "hybrid", label: "Hybrid" },
                    { key: "onsite", label: "On-site" },
                  ].map((wt) => (
                    <button
                      key={wt.key}
                      onClick={() => setWorkType(wt.key)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all duration-200 ${
                        workType === wt.key
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                      }`}
                    >
                      {wt.label}
                    </button>
                  ))}
                </div>
                <Select value={size} onValueChange={setSize}>
                  <SelectTrigger className="h-10 w-[140px] text-sm">
                    <SelectValue placeholder="Company size" />
                  </SelectTrigger>
                  <SelectContent>
                    {sizeFilters.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Row 2: City, State, Country, Industry filters */}
              <div className="flex gap-3 flex-wrap mt-3">
                <div className="relative flex-1 min-w-[160px]">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="City…"
                    className="pl-8 h-9 text-sm"
                    value={cityFilter}
                    onChange={(e) => setCityFilter(e.target.value)}
                    list="city-suggestions"
                  />
                  {filterOptions?.cities && (
                    <datalist id="city-suggestions">
                      {filterOptions.cities.map((c) => <option key={c} value={c} />)}
                    </datalist>
                  )}
                </div>
                <div className="relative flex-1 min-w-[120px]">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="State…"
                    className="pl-8 h-9 text-sm"
                    value={stateFilter}
                    onChange={(e) => setStateFilter(e.target.value)}
                    list="state-suggestions"
                  />
                  {filterOptions?.states && (
                    <datalist id="state-suggestions">
                      {filterOptions.states.map((s) => <option key={s} value={s} />)}
                    </datalist>
                  )}
                </div>
                <div className="relative flex-1 min-w-[120px]">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Country…"
                    className="pl-8 h-9 text-sm"
                    value={countryFilter}
                    onChange={(e) => setCountryFilter(e.target.value)}
                    list="country-suggestions"
                  />
                  {filterOptions?.countries && (
                    <datalist id="country-suggestions">
                      {filterOptions.countries.map((c) => <option key={c} value={c} />)}
                    </datalist>
                  )}
                </div>
                <div className="relative flex-1 min-w-[140px]">
                  <Layers className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Industry…"
                    className="pl-8 h-9 text-sm"
                    value={industryFilter}
                    onChange={(e) => setIndustryFilter(e.target.value)}
                    list="industry-suggestions"
                  />
                  {filterOptions?.industries && (
                    <datalist id="industry-suggestions">
                      {filterOptions.industries.map((ind) => <option key={ind} value={ind} />)}
                    </datalist>
                  )}
                </div>
                {(cityFilter || stateFilter || countryFilter || industryFilter) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-9 text-xs"
                    onClick={() => { setCityFilter(""); setStateFilter(""); setCountryFilter(""); setIndustryFilter(""); }}
                  >
                    <X className="h-3 w-3 mr-1" /> Clear
                  </Button>
                )}
              </div>

              {/* Row 3: Type filter buttons */}
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

        {/* Hackathons Section */}
        {showHackathons && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.25, 0.1, 0, 1] }}
            className="mt-6"
          >
            <div className="bento-card p-5 relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/30 to-transparent" />
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
                  <Trophy className="h-5 w-5 text-amber-400" />
                </div>
                <div className="flex-1">
                  <h2 className="font-display font-semibold text-lg">Upcoming Hackathons</h2>
                  <p className="text-xs text-muted-foreground">
                    {hackathonLoading ? "Searching…" : `${allHackathons.length} hackathons found`}
                  </p>
                </div>

                {/* Hackathon Alert Controls */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <Switch
                      id="hackathon-alert"
                      checked={hackathonAlerts}
                      onCheckedChange={toggleHackathonAlert}
                    />
                    <Label htmlFor="hackathon-alert" className="text-xs cursor-pointer whitespace-nowrap">
                      Auto-alert
                    </Label>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Switch
                      id="email-alert"
                      checked={emailAlerts}
                      onCheckedChange={toggleEmailAlerts}
                      disabled={!hackathonAlerts}
                      className="data-[state=unchecked]:opacity-50"
                    />
                    <Label htmlFor="email-alert" className="text-xs cursor-pointer whitespace-nowrap">
                      ✉️ Email
                    </Label>
                  </div>
                  <div className="relative">
                    <Input
                      placeholder="Skills to match…"
                      className="h-8 w-32 text-xs"
                      value={alertKeywords}
                      onChange={(e) => {
                        setAlertKeywords(e.target.value);
                        localStorage.setItem("hackathon_alert_keywords", e.target.value);
                      }}
                    />
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 h-8 text-xs"
                    onClick={handleScanHackathons}
                    disabled={scanHackathons.isPending}
                  >
                    <RefreshCw className={`h-3 w-3 ${scanHackathons.isPending ? "animate-spin" : ""}`} />
                    {scanHackathons.isPending ? "Scanning…" : "Check matches"}
                  </Button>
                  <Button
                    variant={hackathonViewMode === "calendar" ? "default" : "outline"}
                    size="sm"
                    className="gap-1.5 h-8 text-xs"
                    onClick={() => {
                      setHackathonViewMode(hackathonViewMode === "cards" ? "calendar" : "cards");
                      setSelectedDeadlineDate(undefined);
                    }}
                  >
                    <Calendar className="h-3 w-3" />
                    {hackathonViewMode === "calendar" ? "Cards" : "Deadlines"}
                  </Button>
                </div>
              </div>

              {/* Hackathon search */}
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  placeholder="Filter hackathons by title or company…"
                  className="h-9 pl-8 text-sm"
                  value={hackathonSearch}
                  onChange={(e) => setHackathonSearch(e.target.value)}
                />
              </div>

              {/* Quick group filters */}
              <div className="flex items-center gap-1.5 mb-4 flex-wrap text-xs">
                <span className="text-muted-foreground mr-0.5">Show:</span>
                {[
                  { key: "all", label: "All", color: "" },
                  { key: "urgent", label: "🔴 Urgent", color: "from-red-500/20 to-red-600/10" },
                  { key: "month", label: "🟡 This Month", color: "from-amber-500/20 to-orange-500/10" },
                  { key: "later", label: "📅 Later", color: "from-blue-500/20 to-cyan-500/10" },
                  { key: "no-deadline", label: "📌 No Deadline", color: "from-muted-foreground/20 to-muted/10" },
                ].map((f) => (
                  <button
                    key={f.key}
                    onClick={() => setHackathonGroupFilter(f.key)}
                    className={`px-2 py-1 rounded-lg font-medium transition-all duration-200 ${
                      hackathonGroupFilter === f.key
                        ? f.key === "all"
                          ? "bg-primary/15 text-primary shadow-sm"
                          : `bg-gradient-to-br ${f.color} border border-border/40 text-foreground shadow-sm`
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Recent Hackathon Matches Banner */}
              {recentMatches.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mb-4 p-3 rounded-xl bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent border border-emerald-500/20"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Sparkles className="h-4 w-4 text-emerald-400" />
                      <span>{recentMatches.length} new hackathon{recentMatches.length > 1 ? "s" : ""} matched your skills!</span>
                    </div>
                    <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={clearRecentMatches}>
                      <X className="h-3 w-3 mr-1" /> Dismiss
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {recentMatches.slice(0, 5).map((m, i) => (
                      <Badge
                        key={i}
                        variant="secondary"
                        className="text-xs gap-1 cursor-pointer hover:bg-emerald-500/20 transition-colors"
                        onClick={() => m.apply_url && window.open(m.apply_url, "_blank")}
                      >
                        {m.title.length > 30 ? m.title.slice(0, 30) + "…" : m.title}
                        <span className="text-emerald-400 font-medium">{m.skill_score}%</span>
                      </Badge>
                    ))}
                    {recentMatches.length > 5 && (
                      <Badge variant="outline" className="text-xs">
                        +{recentMatches.length - 5} more
                      </Badge>
                    )}
                  </div>
                </motion.div>
              )}

              {hackathonLoading ? (
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <CardSkeleton key={i} />
                  ))}
                </div>
              ) : allHackathons.length === 0 ? (
                <EmptyState
                  icon={Trophy}
                  title="No hackathons found"
                  description="Try refreshing to search for upcoming hackathons."
                  action={
                    <Button variant="outline" size="sm" className="gap-2" onClick={handleRefresh}>
                      <RefreshCw className="h-4 w-4" /> Search Hackathons
                    </Button>
                  }
                />
              ) : hackathonViewMode === "calendar" ? (
                <div className="space-y-4">
                  {/* Calendar View */}
                  <div className="flex flex-col lg:flex-row gap-6">
                    <div className="lg:w-[360px] shrink-0">
                      <div className="bento-card p-3 rounded-xl">
                        <DayPicker
                          mode="single"
                          defaultMonth={busiestMonth}
                          selected={selectedDeadlineDate}
                          onSelect={setSelectedDeadlineDate}
                          modifiers={{
                            hasDeadline: deadlineDates,
                            past: deadlineDates.filter((d) => d < new Date()),
                          }}
                          modifiersStyles={{
                            hasDeadline: {
                              fontWeight: 700,
                              color: "#fbbf24",
                              backgroundColor: "rgba(251, 191, 36, 0.12)",
                              borderRadius: "999px",
                            },
                            past: {
                              opacity: 0.4,
                            },
                          }}
                        />
                      </div>
                      {/* Calendar legend */}
                      <div className="flex items-center gap-4 mt-2 px-1 text-[11px] text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "rgba(251, 191, 36, 0.25)" }} />
                          Deadline
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="inline-block h-2.5 w-2.5 rounded-full bg-muted-foreground/20" />
                          Past
                        </div>
                      </div>
                    </div>
                    {/* Selected day events */}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-display font-semibold text-sm mb-3 flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-amber-400" />
                        {selectedDeadlineDate
                          ? `${selectedDayHackathons.length} deadline${selectedDayHackathons.length !== 1 ? "s" : ""} on ${format(selectedDeadlineDate, "MMM d, yyyy")}`
                          : "Select a date to see deadlines"}
                      </h3>
                      {selectedDayHackathons.length > 0 ? (
                        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                          {selectedDayHackathons.map((h, idx) => (
                            <Card
                              key={idx}
                              className="bento-card p-3 hover:shadow-glow transition-all duration-200 cursor-pointer border-amber-500/10 hover:border-amber-500/30"
                              onClick={() => h.apply_url && window.open(h.apply_url, "_blank")}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0 flex-1">
                                  <div className="font-display font-semibold text-sm leading-tight text-amber-400">
                                    {h.title}
                                  </div>
                                  <div className="text-xs text-muted-foreground mt-0.5">{h.company}</div>
                                </div>
                                <Clock className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" />
                              </div>
                              {h.description && (
                                <p className="text-xs text-muted-foreground line-clamp-2 mt-1.5">
                                  {h.description}
                                </p>
                              )}
                              <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-border/20">
                                <div className="flex flex-wrap gap-1">
                                  {(h.skills_required || []).slice(0, 2).map((s) => (
                                    <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>
                                  ))}
                                  {profile && (h.skills_required?.length ?? 0) > 0 && (
                                    <span className={`inline-flex text-[10px] font-medium px-1.5 py-0.5 rounded-md border ${skillColor(computeSkillMatch(h))}`}>
                                      {computeSkillMatch(h)}% match
                                    </span>
                                  )}
                                </div>
                                {h.apply_url && (
                                  <ExternalLink className="h-3 w-3 text-muted-foreground" />
                                )}
                              </div>
                            </Card>
                          ))}
                        </div>
                      ) : (
                        selectedDeadlineDate && (
                          <div className="p-6 rounded-xl bg-muted/30 border border-border/20 text-center">
                            <p className="text-sm text-muted-foreground">No deadlines on this day</p>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {hackathonSearch && filteredHackathons.length === 0 ? (
                    <div className="p-8 rounded-xl bg-muted/30 border border-border/20 text-center">
                      <Search className="h-6 w-6 mx-auto mb-2 text-muted-foreground/50" />
                      <p className="text-sm text-muted-foreground">
                        No hackathons matching <span className="font-medium text-foreground">"{hackathonSearch}"</span>
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-2 h-7 text-xs"
                        onClick={() => setHackathonSearch("")}
                      >
                        <X className="h-3 w-3 mr-1" /> Clear filter
                      </Button>
                    </div>
                  ) : (() => {
                    const visibleGroups = groupedHackathons.filter((group, idx) => {
                      if (hackathonGroupFilter === "all") return true;
                      const keys = ["urgent", "month", "later", "no-deadline"];
                      return keys.indexOf(hackathonGroupFilter) === idx;
                    });
                    return visibleGroups.map((group) =>
                      group.items.length === 0 ? null : (
                        <div key={group.label}>
                        {/* Group header */}
                        <div className="flex items-center gap-2 mb-2.5">
                          <div className={`h-6 w-6 rounded-lg bg-gradient-to-br ${group.color} border border-border/30 flex items-center justify-center text-xs`}>
                            {group.icon}
                          </div>
                          <h3 className="font-display font-semibold text-sm">{group.label}</h3>
                          <span className="text-xs text-muted-foreground ml-auto">{group.items.length} hackathon{group.items.length !== 1 ? "s" : ""}</span>
                        </div>
                        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                          {group.items.map((h, idx) => (
                            <motion.div
                              key={`${group.label}-${idx}`}
                              initial={{ opacity: 0, y: 16 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ duration: 0.35, delay: Math.min(idx * 0.03, 0.3), ease: [0.25, 0.1, 0, 1] }}
                            >
                              <Card className="bento-card p-4 hover:shadow-glow transition-all duration-300 group cursor-pointer border-amber-500/10 hover:border-amber-500/30"
                                onClick={() => {
                                  if (h.apply_url) {
                                    window.open(h.apply_url, "_blank");
                                  }
                                }}
                              >
                                {/* Header */}
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center gap-2.5">
                                    <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20 flex items-center justify-center font-bold text-sm text-amber-400">
                                      {h.company.charAt(0)}
                                    </div>
                                    <div className="min-w-0">
                                      <div className="font-display font-semibold text-sm leading-tight group-hover:text-amber-400 transition flex items-center gap-1">
                                        {h.title}
                                      </div>
                                      <div className="text-xs text-muted-foreground">{h.company}</div>
                                    </div>
                                  </div>
                                </div>

                                {/* Meta */}
                                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-2.5">
                                  {h.location && (
                                    <span className="flex items-center gap-1">
                                      <MapPin className="h-3 w-3" /> {h.location}
                                    </span>
                                  )}
                                  {h.deadline && (
                                    <span className="flex items-center gap-1">
                                      <Clock className="h-3 w-3" /> Due {h.deadline}
                                    </span>
                                  )}
                                </div>

                                {/* Description */}
                                {h.description && (
                                  <p className="text-xs text-muted-foreground line-clamp-2 mb-2.5">
                                    {h.description}
                                  </p>
                                )}

                                {/* Skills */}
                                {h.skills_required && h.skills_required.length > 0 && (
                                  <div className="flex flex-wrap gap-1.5">
                                    {h.skills_required.slice(0, 3).map((s) => (
                                      <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>
                                    ))}
                                  </div>
                                )}

                                {/* Source badge + skill match */}
                                <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-border/30">
                                  <div className="flex items-center gap-1.5">
                                    <Badge variant="outline" className="text-[10px] text-muted-foreground">
                                      {h.source || "Web"}
                                    </Badge>
                                    {profile && (h.skills_required?.length ?? 0) > 0 && (
                                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md border ${skillColor(computeSkillMatch(h))}`}>
                                        {computeSkillMatch(h)}% match
                                      </span>
                                    )}
                                  </div>
                                  {h.apply_url && (
                                    <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                  )}
                                </div>
                              </Card>
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    )
                    );
                  })()}
                </div>
              )}
            </div>
          </motion.div>
        )}

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
        ) : viewMode === "map" ? (
          /* Map View */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mt-2"
          >
            {/* Map type filter chips */}
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <span className="text-xs text-muted-foreground font-medium mr-1">Filter by type:</span>
              {typeFilters.map((t) => (
                <button
                  key={t}
                  onClick={() => setType(t)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200 ${
                    type === t
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {typeIcons[t] && <span className="mr-1">{typeIcons[t]}</span>}
                  {t}
                  {t !== "All" && (
                    <span className="ml-1 opacity-60">
                      {data?.items?.filter((o) => o.type === t).length || 0}
                    </span>
                  )}
                </button>
              ))}
              <div className="flex-1 text-right">
                <p className="text-xs text-muted-foreground">
                  {locationData?.locations?.length
                    ? `${locationData.locations.length} locations with ${filtered.length} opportunity${filtered.length !== 1 ? "ies" : "y"}`
                    : "Loading location data…"}
                </p>
              </div>
            </div>
            <OpportunityMap
              locations={(locationData?.locations ?? []).map((loc) => ({
                ...loc,
                opportunities: filtered.filter(
                  (o) =>
                (!loc.city || (o.city && o.city.toLowerCase() === loc.city.toLowerCase())) &&
                (!loc.state || (o.state && o.state.toLowerCase() === loc.state.toLowerCase()))
                ),
              }))}
              isLoading={locationsLoading}
              onSelectOpp={(opp) => setSelected(opp)}
            />
          </motion.div>
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

                      {/* Meta row - now includes city/state/country/industry */}
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-3">
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> {o.city || o.location || "Remote"}{o.state ? `, ${o.state}` : ""}
                        </span>
                        {o.country && (
                          <span className="flex items-center gap-1">
                            <Globe className="h-3 w-3" /> {o.country}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Building2 className="h-3 w-3" /> {o.company_size || "—"}
                        </span>
                        {o.industry && (
                          <span className="flex items-center gap-1">
                            <Layers className="h-3 w-3" /> {o.industry}
                          </span>
                        )}
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
                            <MapPin className="h-3.5 w-3.5" /> {selected.city || selected.location || "Remote"}
                            {selected.state ? `, ${selected.state}` : ""}
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
                  {selected.industry && (
                    <div className="bento-card p-4">
                      <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                        <Layers className="h-3 w-3" /> Industry
                      </div>
                      <div className="font-medium">{selected.industry}</div>
                    </div>
                  )}
                  {selected.country && (
                    <div className="bento-card p-4">
                      <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                        <Globe className="h-3 w-3" /> Country
                      </div>
                      <div className="font-medium">{selected.country}</div>
                    </div>
                  )}
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
