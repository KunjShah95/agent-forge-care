import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Play, Mic, Trophy, Clock, BookOpen, Loader2 } from "lucide-react";
import { useInterviewPrep } from "@/api/hooks";
import { toast } from "sonner";

const questionBank: Record<string, string[]> = {
  Behavioral: [
    "Tell me about a time you led a team through ambiguity.",
    "Describe your most impactful project and the tradeoffs.",
    "How do you handle disagreement with a manager?",
    "Walk me through a failure and what you learned.",
  ],
  Technical: [
    "Design a URL shortener that handles 1B requests/day.",
    "Implement LRU cache in TypeScript.",
    "Explain how React reconciliation works.",
    "Find the longest palindromic substring.",
  ],
  "System Design": [
    "Design Twitter's timeline service.",
    "How would you build a real-time collaborative editor?",
    "Architect a global CDN.",
  ],
  "ML/AI": [
    "Explain attention vs convolution.",
    "How do you evaluate an LLM?",
    "Design a recommendation system for opportunities.",
  ],
};

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
  const navigate = useNavigate();
  const [category, setCategory] = useState<string>("Behavioral");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [type, setType] = useState("behavioral");
  const [generatedQuestions, setGeneratedQuestions] = useState<string[]>([]);
  const [generatedTips, setGeneratedTips] = useState<string[]>([]);

  const interviewPrep = useInterviewPrep();

  const handleGenerate = async () => {
    if (!company || !role) {
      toast.error("Please fill in company and role");
      return;
    }
    try {
      const result = await interviewPrep.mutateAsync({ company, role, type });
      setGeneratedQuestions(result.questions);
      setGeneratedTips(result.tips);
      setDialogOpen(false);
      toast.success("Questions generated!");
    } catch {
      toast.error("Failed to generate questions");
    }
  };

  const displayQuestions = generatedQuestions.length > 0
    ? { Generated: generatedQuestions, ...questionBank }
    : questionBank;

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Interview Prep</h1>
          <p className="text-muted-foreground mt-1">Mock interviews, question banks, and skill tracking.</p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2" onClick={() => setDialogOpen(true)}>
          <Mic className="h-4 w-4" /> Start mock interview
        </Button>
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

      {generatedTips.length > 0 && (
        <Card className="glass p-5 border-primary/30">
          <h3 className="font-display font-semibold mb-2">AI Tips for {company} — {role}</h3>
          <ul className="space-y-1">
            {generatedTips.map((tip, i) => (
              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="text-primary mt-0.5">•</span> {tip}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="glass p-6 lg:col-span-2">
          <h2 className="font-display font-semibold mb-4">Question Bank</h2>
          <Tabs value={category} onValueChange={setCategory}>
            <TabsList className="glass">
              {Object.keys(displayQuestions).map((c) => (
                <TabsTrigger key={c} value={c}>{c}</TabsTrigger>
              ))}
            </TabsList>
            {Object.entries(displayQuestions).map(([cat, qs]) => (
              <TabsContent key={cat} value={cat} className="mt-4 space-y-2">
                {qs.map((q, i) => (
                  <div key={i} className="flex items-center gap-3 p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition cursor-pointer">
                    <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center text-xs font-display font-bold text-primary">
                      Q{i + 1}
                    </div>
                    <div className="flex-1 text-sm">{q}</div>
                    <Button variant="ghost" size="sm" className="gap-1" onClick={() => navigate("/app/agents")}>
                      <Play className="h-3 w-3" /> Practice
                    </Button>
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
            <BookOpen className="h-3 w-3" /> Review all sessions
          </Button>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Interview Questions</DialogTitle>
            <DialogDescription>
              AI will generate tailored questions based on your target company and role.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Company</Label>
              <Input placeholder="e.g. Stripe" value={company} onChange={(e) => setCompany(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Input placeholder="e.g. Senior Software Engineer" value={role} onChange={(e) => setRole(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Interview Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="behavioral">Behavioral</SelectItem>
                  <SelectItem value="technical">Technical</SelectItem>
                  <SelectItem value="system_design">System Design</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button className="bg-gradient-primary shadow-glow gap-2" onClick={handleGenerate} disabled={interviewPrep.isPending}>
              {interviewPrep.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
