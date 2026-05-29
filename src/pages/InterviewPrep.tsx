import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { interviewQuestions } from "@/lib/sample-data";
import { Play, Mic, MessageSquare, Trophy, Clock } from "lucide-react";

const sessions = [
  { id: "s1", company: "Stripe", type: "Behavioral", date: "Dec 3", score: 82, duration: "32 min" },
  { id: "s2", company: "Anthropic", type: "ML Technical", date: "Dec 2", score: 76, duration: "45 min" },
  { id: "s3", company: "Linear", type: "System Design", date: "Nov 28", score: 88, duration: "50 min" },
];

const categoryStats = [
  { name: "Behavioral", done: 24, total: 40, score: 82 },
  { name: "Technical", done: 38, total: 60, score: 76 },
  { name: "System Design", done: 12, total: 20, score: 88 },
  { name: "ML/AI", done: 18, total: 30, score: 79 },
];

export default function InterviewPrep() {
  const [category, setCategory] = useState<keyof typeof interviewQuestions>("Behavioral");

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Interview Prep</h1>
          <p className="text-muted-foreground mt-1">Mock interviews, question banks, and skill tracking.</p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2"><Mic className="h-4 w-4" /> Start mock interview</Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {categoryStats.map((c) => (
          <Card key={c.name} className="glass p-5">
            <div className="text-xs text-muted-foreground">{c.name}</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-display font-bold">{c.done}</span>
              <span className="text-xs text-muted-foreground">/ {c.total}</span>
            </div>
            <Progress value={(c.done / c.total) * 100} className="h-1.5 mt-3" />
            <div className="flex items-center justify-between mt-2 text-xs">
              <span className="text-muted-foreground">Avg score</span>
              <span className="font-display font-semibold gradient-text">{c.score}%</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="glass p-6 lg:col-span-2">
          <h2 className="font-display font-semibold mb-4">Question Bank</h2>
          <Tabs value={category} onValueChange={(v) => setCategory(v as keyof typeof interviewQuestions)}>
            <TabsList className="glass">
              {Object.keys(interviewQuestions).map((c) => (
                <TabsTrigger key={c} value={c}>{c}</TabsTrigger>
              ))}
            </TabsList>
            {Object.entries(interviewQuestions).map(([cat, qs]) => (
              <TabsContent key={cat} value={cat} className="mt-4 space-y-2">
                {qs.map((q, i) => (
                  <div key={i} className="flex items-center gap-3 p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition cursor-pointer">
                    <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center text-xs font-display font-bold text-primary">
                      Q{i + 1}
                    </div>
                    <div className="flex-1 text-sm">{q}</div>
                    <Button variant="ghost" size="sm" className="gap-1"><Play className="h-3 w-3" /> Practice</Button>
                  </div>
                ))}
              </TabsContent>
            ))}
          </Tabs>
        </Card>

        <Card className="glass p-6">
          <h2 className="font-display font-semibold mb-4">Recent Sessions</h2>
          <div className="space-y-3">
            {sessions.map((s) => (
              <div key={s.id} className="p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition cursor-pointer">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{s.company}</span>
                  <Badge variant="outline" className="text-[10px]">{s.type}</Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {s.duration}</span>
                  <span className="flex items-center gap-1"><Trophy className="h-3 w-3" /> {s.score}%</span>
                  <span className="ml-auto">{s.date}</span>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" size="sm" className="w-full mt-4 gap-2">
            <MessageSquare className="h-3 w-3" /> Review all sessions
          </Button>
        </Card>
      </div>
    </div>
  );
}
