import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Building2, TrendingUp, BookOpen, FileText, Search, Loader2, Save, Code, Lightbulb, DollarSign, Users, Target } from "lucide-react";
import { useResearch, useCreateMemory, useMemory } from "@/api/hooks";
import { toast } from "sonner";

const companyProfiles = [
  { id: "c1", name: "Anthropic", initials: "A", industry: "AI Research", size: "500-1000", glassdoor: 4.6, notes: "Mission-driven. Values alignment research." },
  { id: "c2", name: "Stripe", initials: "S", industry: "Fintech", size: "5000+", glassdoor: 4.5, notes: "Strong engineering culture. Writing intensive." },
  { id: "c3", name: "Linear", initials: "L", industry: "Productivity", size: "50-100", glassdoor: 4.8, notes: "Design obsessed. Small senior team." },
  { id: "c4", name: "Vercel", initials: "V", industry: "Dev Tools", size: "200-500", glassdoor: 4.4, notes: "Frontend leaders. Remote-first." },
  { id: "c5", name: "Helia Labs", initials: "H", industry: "AI Agents", size: "5-10", glassdoor: 4.9, notes: "Early stage. High equity upside." },
];

const trends = [
  { topic: "AI safety hiring surges +40% YoY", source: "Industry report · 2d ago" },
  { topic: "Rust adoption in fintech: now mainstream", source: "Stack Overflow Survey" },
  { topic: "Remote-first startups offering 15% higher base", source: "Levels.fyi data" },
  { topic: "Founding engineer roles up 3x in 6 months", source: "YC Work at a Startup" },
];

const insights = [
  { company: "Anthropic", text: "Final round emphasizes red-teaming scenarios; expect 2-3 alignment edge case discussions.", date: "Nov 28" },
  { company: "Stripe", text: "OA is API-design heavy. Practice idempotency keys and rate-limiting.", date: "Nov 24" },
  { company: "Linear", text: "Pair-programming round. They watch how you ask clarifying questions.", date: "Nov 20" },
];

const defaultNotes = `# Anthropic deep dive
- Core values: helpful, harmless, honest
- Eng blog posts: focus on constitutional AI, mech interp
- Recent paper to mention: "Toy Models of Superposition"

# Stripe
- API design philosophy: durable objects, idempotency-first
- Talk to: Maya P. (recruiter, already replied)

# Questions to ask:
- "How does your team balance research velocity vs publishing?"
- "What did the last person in this role struggle with most?"`;

export default function ResearchCenter() {
  const [researchInput, setResearchInput] = useState("");
  const [researchResult, setResearchResult] = useState<Record<string, unknown> | null>(null);
  const [researchedCompany, setResearchedCompany] = useState("");
  const [notes, setNotes] = useState(defaultNotes);
  const [showRawJson, setShowRawJson] = useState(false);

  const research = useResearch();
  const createMemory = useCreateMemory();
  const { data: memoriesData } = useMemory();

  const existingNotes = memoriesData?.items?.find?.((m) => m.key === "research_notes");
  if (existingNotes && notes === defaultNotes && typeof existingNotes.value === "string") {
    setNotes(existingNotes.value);
  }

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
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="font-display text-3xl font-bold">Research Center</h1>
        <p className="text-muted-foreground mt-1">Company profiles, interview insights, and industry trends compiled by your Research Agent.</p>
      </div>

      <Tabs defaultValue="companies">
        <TabsList className="glass">
          <TabsTrigger value="companies"><Building2 className="h-3 w-3 mr-1" /> Companies</TabsTrigger>
          <TabsTrigger value="insights"><BookOpen className="h-3 w-3 mr-1" /> Interview Insights</TabsTrigger>
          <TabsTrigger value="trends"><TrendingUp className="h-3 w-3 mr-1" /> Industry Trends</TabsTrigger>
          <TabsTrigger value="notes"><FileText className="h-3 w-3 mr-1" /> Notes</TabsTrigger>
        </TabsList>

        <TabsContent value="companies" className="mt-4 space-y-4">
          <Card className="glass p-4">
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
                className="bg-gradient-primary shadow-glow gap-2"
                onClick={() => handleResearch()}
                disabled={research.isPending}
              >
                {research.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Research
              </Button>
            </div>
          </Card>

          {researchResult && (
            <Card className="glass p-5 border-primary/30">
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

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {companyProfiles.map((c) => (
              <Card key={c.id} className="glass p-5 hover:shadow-glow transition">
                <div className="flex items-start gap-3 mb-3">
                  <div className="h-12 w-12 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center font-bold text-primary text-lg">
                    {c.initials}
                  </div>
                  <div className="flex-1">
                    <div className="font-display font-semibold">{c.name}</div>
                    <div className="text-xs text-muted-foreground">{c.industry} · {c.size}</div>
                  </div>
                  <Badge variant="outline" className="gap-1">
                    <span className="text-warning">★</span> {c.glassdoor}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-3">{c.notes}</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => handleResearch(c.name)}
                  disabled={research.isPending}
                >
                  {research.isPending ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                  View profile
                </Button>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="insights" className="mt-4 space-y-3">
          {insights.map((i, idx) => (
            <Card key={idx} className="glass p-5">
              <div className="flex items-start justify-between mb-2">
                <Badge variant="secondary">{i.company}</Badge>
                <span className="text-xs text-muted-foreground">{i.date}</span>
              </div>
              <p className="text-sm">{i.text}</p>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="trends" className="mt-4 space-y-3">
          {trends.map((t, idx) => (
            <Card key={idx} className="glass p-5 flex items-center gap-4">
              <TrendingUp className="h-5 w-5 text-success flex-shrink-0" />
              <div className="flex-1">
                <div className="font-medium text-sm">{t.topic}</div>
                <div className="text-xs text-muted-foreground">{t.source}</div>
              </div>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="notes" className="mt-4">
          <Card className="glass p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-display font-semibold">Personal research notes</h3>
              <Button
                size="sm"
                className="gap-2 bg-gradient-primary shadow-glow"
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
