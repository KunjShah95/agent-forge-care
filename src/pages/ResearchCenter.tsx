import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { companies } from "@/lib/sample-data";
import { Building2, Star, TrendingUp, BookOpen, FileText } from "lucide-react";

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

export default function ResearchCenter() {
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

        <TabsContent value="companies" className="mt-4">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {companies.map((c) => (
              <Card key={c.id} className="glass p-5 hover:shadow-glow transition">
                <div className="flex items-start gap-3 mb-3">
                  <div className="text-4xl">{c.logo}</div>
                  <div className="flex-1">
                    <div className="font-display font-semibold">{c.name}</div>
                    <div className="text-xs text-muted-foreground">{c.industry} · {c.size}</div>
                  </div>
                  <Badge variant="outline" className="gap-1">
                    <Star className="h-3 w-3 fill-warning text-warning" /> {c.glassdoor}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-3">{c.notes}</p>
                <Button variant="outline" size="sm" className="w-full">View profile</Button>
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
          <Card className="glass p-6">
            <h3 className="font-display font-semibold mb-3">Personal research notes</h3>
            <Textarea
              rows={14}
              defaultValue={`# Anthropic deep dive\n- Core values: helpful, harmless, honest\n- Eng blog posts: focus on constitutional AI, mech interp\n- Recent paper to mention: "Toy Models of Superposition"\n\n# Stripe\n- API design philosophy: durable objects, idempotency-first\n- Talk to: Maya P. (recruiter, already replied)\n\n# Questions to ask:\n- "How does your team balance research velocity vs publishing?"\n- "What did the last person in this role struggle with most?"`}
              className="font-mono text-xs"
            />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
