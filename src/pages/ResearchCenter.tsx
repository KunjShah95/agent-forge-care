import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Building2, TrendingUp, BookOpen, FileText, Search, Loader2, Save, Code, Lightbulb, DollarSign, Users, Target } from "lucide-react";
import { useResearch, useCreateMemory, useMemory } from "@/api/hooks";
import { toast } from "sonner";

export default function ResearchCenter() {
  const [researchInput, setResearchInput] = useState("");
  const [researchResult, setResearchResult] = useState<Record<string, unknown> | null>(null);
  const [researchedCompany, setResearchedCompany] = useState("");
  const [notes, setNotes] = useState("");
  const [showRawJson, setShowRawJson] = useState(false);
  const [insights, setInsights] = useState<{ company: string; text: string; date: string }[]>([]);
  const [trends, setTrends] = useState<{ topic: string; source: string }[]>([]);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [loadingTrends, setLoadingTrends] = useState(false);

  const research = useResearch();
  const researchInsights = useResearch();
  const researchTrends = useResearch();
  const createMemory = useCreateMemory();
  const { data: memoriesData } = useMemory();

  const notesInitialized = useRef(false);
  useEffect(() => {
    if (notesInitialized.current) return;
    const existing = memoriesData?.items?.find?.((m) => m.key === "research_notes");
    if (existing && typeof existing.value === "string") {
      setNotes(existing.value);
      notesInitialized.current = true;
    }
  }, [memoriesData]);

  useEffect(() => {
    const fetchInsights = async () => {
      setLoadingInsights(true);
      try {
        const result = await researchInsights.mutateAsync({ company: "", focus: "interview-prep", topics: [] });
        const r = result as Record<string, unknown>;
        const results = r.results as Record<string, unknown> | undefined;
        const interviewData = results?.interview_insights as Record<string, unknown> | undefined;
        const questions = interviewData?.common_questions as string[] | undefined;
        if (questions && questions.length > 0) {
          setInsights(questions.map((q, i) => ({
            company: typeof researchInput === "string" && researchInput ? researchInput : "Tech",
            text: q,
            date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          })));
        }
      } catch (err) {
        console.error("Failed to load interview insights:", err);
        toast.error("Could not load interview insights");
      } finally {
        setLoadingInsights(false);
      }
    };
    fetchInsights();
  }, []);

  useEffect(() => {
    const fetchTrends = async () => {
      setLoadingTrends(true);
      try {
        const result = await researchTrends.mutateAsync({ company: "", focus: "market", topics: [] });
        const r = result as Record<string, unknown>;
        const results = r.results as Record<string, unknown> | undefined;
        const marketData = results?.market_trends as Record<string, unknown> | undefined;
        const growthAreas = marketData?.growth_areas as string[] | undefined;
        if (growthAreas && growthAreas.length > 0) {
          const suggestions = marketData?.suggestions as string[] | undefined;
          setTrends([
            ...growthAreas.map((area) => ({
              topic: `${area} — growing demand`,
              source: "Market intelligence · live",
            })),
            ...(suggestions?.slice(0, 2).map((s) => ({
              topic: s,
              source: "AI-suggested strategy · live",
            })) || []),
          ]);
        }
      } catch (err) {
        console.error("Failed to load industry trends:", err);
        toast.error("Could not load industry trends");
      } finally {
        setLoadingTrends(false);
      }
    };
    fetchTrends();
  }, []);

  const handleResearch = async (companyName?: string) => {
    const target = companyName || researchInput;
    if (!target) {
      toast.error("Please enter a company name");
      return;
    }
    try {
      const result = await research.mutateAsync({ company: target });
      setResearchResult(result);
      setResearchedCompany(target);
      toast.success(`Research complete for ${target}`);
    } catch {
      toast.error("Research failed. Please try again.");
    }
  };

  const handleSaveNotes = async () => {
    try {
      await createMemory.mutateAsync({ key: "research_notes", value: notes });
      toast.success("Notes saved");
    } catch {
      toast.error("Failed to save notes");
    }
  };

  const r = researchResult as Record<string, unknown> | null;

  return (
    <div className="space-y-6 max-w-[1400px] relative">
      {/* Animated grid background */}
      <div className="fixed inset-0 animated-grid opacity-40 pointer-events-none" />
      <div className="fixed inset-0 bg-beams opacity-20 pointer-events-none" />
      <div className="fixed top-1/4 right-1/4 w-72 h-72 rounded-full bg-gradient-1 opacity-[0.03] blur-3xl animate-float-slow pointer-events-none" />
      <div className="fixed bottom-1/3 left-1/4 w-56 h-56 rounded-full bg-gradient-3 opacity-[0.03] blur-3xl animate-float pointer-events-none" />

      <div className="relative">
        <h1 className="font-display text-3xl font-bold">Research Center</h1>
        <p className="text-muted-foreground mt-1">Company profiles, interview insights, and industry trends compiled by your Research Agent.</p>
      </div>

      <Tabs defaultValue="companies">
        <TabsList className="bento-card">
          <TabsTrigger value="companies"><Building2 className="h-3 w-3 mr-1" /> Companies</TabsTrigger>
          <TabsTrigger value="insights"><BookOpen className="h-3 w-3 mr-1" /> Interview Insights</TabsTrigger>
          <TabsTrigger value="trends"><TrendingUp className="h-3 w-3 mr-1" /> Industry Trends</TabsTrigger>
          <TabsTrigger value="notes"><FileText className="h-3 w-3 mr-1" /> Notes</TabsTrigger>
        </TabsList>

        <TabsContent value="companies" className="mt-4 space-y-4">
          <Card className="bento-card p-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Enter company name to research..."
                  value={researchInput}
                  onChange={(e) => setResearchInput(e.target.value)}
                  className="pl-9"
                  onKeyDown={(e) => e.key === "Enter" && handleResearch()}
                />
              </div>
              <Button
                className="bg-gradient-1 shadow-glow gap-2"
                onClick={() => handleResearch()}
                disabled={research.isPending}
              >
                {research.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Research
              </Button>
            </div>
          </Card>

          {researchResult && (
            <Card className="bento-card p-5 border-primary/30">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <h3 className="font-display font-semibold">Research: {researchedCompany}</h3>
                  <Badge variant="outline">AI Generated</Badge>
                </div>
                <Button variant="ghost" size="sm" className="gap-1 text-xs" onClick={() => setShowRawJson(!showRawJson)}>
                  <Code className="h-3 w-3" />
                  {showRawJson ? "Hide" : "Show"} Raw JSON
                </Button>
              </div>

              {showRawJson ? (
                <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono bg-muted/30 p-4 rounded-lg overflow-auto max-h-96">
                  {JSON.stringify(researchResult, null, 2)}
                </pre>
              ) : (
                <div className="space-y-4">
                  {r?.summary && (
                    <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/10">
                      <Lightbulb className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                      <div>
                        <div className="text-xs font-semibold text-primary mb-1">Summary</div>
                        <p className="text-sm text-muted-foreground">{r.summary as string}</p>
                      </div>
                    </div>
                  )}

                  {r?.focus && (
                    <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30">
                      <Target className="h-5 w-5 text-warning mt-0.5 flex-shrink-0" />
                      <div>
                        <div className="text-xs font-semibold text-warning mb-1">Focus Areas</div>
                        <p className="text-sm text-muted-foreground">{r.focus as string}</p>
                      </div>
                    </div>
                  )}

                  {r?.company_info && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <Building2 className="h-4 w-4 text-primary" />
                        <h4 className="font-display font-semibold text-sm">Company Info</h4>
                      </div>
                      <div className="grid sm:grid-cols-2 gap-3">
                        {(r.company_info as Record<string, string>)?.description && (
                          <div className="p-3 rounded-lg bg-muted/30 col-span-full">
                            <div className="text-xs text-muted-foreground mb-1">Description</div>
                            <p className="text-sm">{(r.company_info as Record<string, string>).description}</p>
                          </div>
                        )}
                        {(r.company_info as Record<string, string>)?.culture && (
                          <div className="p-3 rounded-lg bg-muted/30">
                            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                              <Users className="h-3 w-3" /> Culture
                            </div>
                            <p className="text-sm">{(r.company_info as Record<string, string>).culture}</p>
                          </div>
                        )}
                        {(r.company_info as Record<string, string>)?.funding && (
                          <div className="p-3 rounded-lg bg-muted/30">
                            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                              <DollarSign className="h-3 w-3" /> Funding
                            </div>
                            <p className="text-sm">{(r.company_info as Record<string, string>).funding}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {r?.market_intelligence && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <TrendingUp className="h-4 w-4 text-success" />
                        <h4 className="font-display font-semibold text-sm">Market Intelligence</h4>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {Object.entries(r.market_intelligence as Record<string, unknown>).map(([key, val]) => (
                          <div key={key} className="p-3 rounded-lg bg-muted/30">
                            <div className="text-xs text-muted-foreground mb-1 capitalize">{key.replace(/_/g, " ")}</div>
                            <div className="font-display font-semibold text-sm">{String(val)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {r?.skill_insights && Array.isArray(r.skill_insights) && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <BookOpen className="h-4 w-4 text-info" />
                        <h4 className="font-display font-semibold text-sm">Skill Insights</h4>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(r.skill_insights as string[]).map((skill, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">{skill}</Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {r?.interview_insights && Array.isArray(r.interview_insights) && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <FileText className="h-4 w-4 text-warning" />
                        <h4 className="font-display font-semibold text-sm">Interview Insights</h4>
                      </div>
                      <ul className="space-y-2">
                        {(r.interview_insights as string[]).map((insight, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                            <span className="text-warning mt-1.5 h-1.5 w-1.5 rounded-full bg-warning flex-shrink-0" />
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}

          
        </TabsContent>

        <TabsContent value="insights" className="mt-4 space-y-3">
          {loadingInsights ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : insights.length === 0 ? (
            <Card className="bento-card p-5 text-center text-sm text-muted-foreground">
              Research a company to get interview insights.
            </Card>
          ) : insights.map((i, idx) => (
            <Card key={idx} className="bento-card p-5">
              <div className="flex items-start justify-between mb-2">
                <Badge variant="secondary">{i.company}</Badge>
                <span className="text-xs text-muted-foreground">{i.date}</span>
              </div>
              <p className="text-sm">{i.text}</p>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="trends" className="mt-4 space-y-3">
          {loadingTrends ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : trends.length === 0 ? (
            <Card className="bento-card p-5 text-center text-sm text-muted-foreground">
              No industry trend data available yet.
            </Card>
          ) : trends.map((t, idx) => (
            <Card key={idx} className="bento-card p-5 flex items-center gap-4">
              <TrendingUp className="h-5 w-5 text-success flex-shrink-0" />
              <div className="flex-1">
                <div className="font-medium text-sm">{t.topic}</div>
                <div className="text-xs text-muted-foreground">{t.source}</div>
              </div>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="notes" className="mt-4">
          <Card className="bento-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-semibold">Personal research notes</h3>
              <Button
                size="sm"
                className="gap-2 bg-gradient-1 shadow-glow"
                onClick={handleSaveNotes}
                disabled={createMemory.isPending}
              >
                {createMemory.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                Save
              </Button>
            </div>
            <Textarea
              rows={14}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="font-mono text-xs"
            />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
