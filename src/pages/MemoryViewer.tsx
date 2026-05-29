import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Layers3, Brain, Target, MapPin, Star, BookOpen,
  Plus, X, Sparkles, Clock, Database, Zap,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

// Sample memory data
const skillCategories = [
  {
    name: "Technical Skills",
    items: [
      { name: "TypeScript", level: "Expert", weight: 1.0 },
      { name: "React", level: "Expert", weight: 1.0 },
      { name: "Python", level: "Advanced", weight: 0.9 },
      { name: "PyTorch", level: "Advanced", weight: 0.85 },
      { name: "PostgreSQL", level: "Intermediate", weight: 0.7 },
      { name: "Docker", level: "Intermediate", weight: 0.65 },
      { name: "GraphQL", level: "Intermediate", weight: 0.6 },
      { name: "Rust", level: "Beginner", weight: 0.3 },
    ],
  },
  {
    name: "Soft Skills",
    items: [
      { name: "Technical Writing", level: "Expert", weight: 0.9 },
      { name: "Public Speaking", level: "Advanced", weight: 0.8 },
      { name: "Leadership", level: "Advanced", weight: 0.85 },
      { name: "Mentoring", level: "Intermediate", weight: 0.7 },
    ],
  },
];

const memoryEntries = [
  { key: "Target Role", value: "ML Research Internship at frontier AI lab", weight: 1.0, updated: "2d ago" },
  { key: "Preferred Locations", value: "Ahmedabad, San Francisco, Remote", weight: 0.9, updated: "1w ago" },
  { key: "Salary Expectation", value: "$150k+ (FTE) / $8k+/mo (intern)", weight: 0.8, updated: "1w ago" },
  { key: "Company Preference", value: "Startup to mid-size, strong mentorship culture", weight: 0.7, updated: "2w ago" },
  { key: "Portfolio", value: "https://alexkim.dev", weight: 0.6, updated: "1mo ago" },
  { key: "LinkedIn", value: "linkedin.com/in/alexkim", weight: 0.5, updated: "1mo ago" },
  { key: "Graduation", value: "June 2026 - Stanford University", weight: 1.0, updated: "2d ago" },
  { key: "Career Goal", value: "Land ML research intern at frontier lab by Feb 2026", weight: 1.0, updated: "2d ago" },
];

const learningEntries = [
  { insight: "Stripe interviews focus heavily on API design and idempotency", source: "Interview feedback", date: "Dec 1" },
  { insight: "Anthropic values alignment research experience in final rounds", source: "Networking chat", date: "Nov 28" },
  { insight: "Startup offers 20% more equity in current market but 10% lower base", source: "Trend analysis", date: "Nov 20" },
  { insight: "MATS fellowship prefers candidates with published blog posts on AI safety", source: "Research Agent", date: "Nov 15" },
  { insight: "Remote-first roles increased 35% for AI internships this cycle", source: "Monitor Agent", date: "Nov 10" },
];

export default function MemoryViewer() {
  const [addOpen, setAddOpen] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");

  const handleAdd = () => {
    if (newKey.trim() && newValue.trim()) {
      // In real app, this would call the API
      setNewKey("");
      setNewValue("");
      setAddOpen(false);
    }
  };

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Memory Layer</h1>
          <p className="text-muted-foreground mt-1">
            The system's long-term memory. This data personalizes agent behavior, match scoring, and recommendations.
          </p>
        </div>
        <Button className="bg-gradient-primary shadow-glow gap-2" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" /> Add Memory
        </Button>
      </div>

      {/* Memory Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Memory Entries", value: "24", icon: Database },
          { label: "Skills Tracked", value: "12", icon: Zap },
          { label: "Learning Points", value: "18", icon: BookOpen },
          { label: "Context Score", value: "94%", icon: Brain },
        ].map((s) => (
          <Card key={s.label} className="glass p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{s.label}</span>
              <s.icon className="h-4 w-4 text-primary" />
            </div>
            <div className="text-3xl font-display font-bold mt-2 gradient-text">{s.value}</div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="glass">
          <TabsTrigger value="profile">Profile Memory</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="learnings">Learnings</TabsTrigger>
          <TabsTrigger value="raw">Raw Context</TabsTrigger>
        </TabsList>

        {/* Profile Memory */}
        <TabsContent value="profile" className="mt-4">
          <Card className="glass p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-display font-semibold">Stored Preferences</h2>
                <p className="text-xs text-muted-foreground">Weight indicates importance in match scoring</p>
              </div>
              <Layers3 className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              {memoryEntries.map((entry) => (
                <div
                  key={entry.key}
                  className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition group"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{entry.key}</span>
                      <Badge variant="outline" className="text-[10px]">
                        weight: {entry.weight.toFixed(1)}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-0.5">{entry.value}</p>
                  </div>
                  <div className="text-xs text-muted-foreground hidden md:block">{entry.updated}</div>
                  <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition">
                    Edit
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* Skills */}
        <TabsContent value="skills" className="mt-4 space-y-4">
          {skillCategories.map((category) => (
            <Card key={category.name} className="glass p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display font-semibold">{category.name}</h2>
                <Badge variant="outline" className="gap-1">
                  <Star className="h-3 w-3 fill-warning text-warning" />
                  Total: {category.items.reduce((s, i) => s + i.weight, 0).toFixed(1)}
                </Badge>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {category.items.map((skill) => (
                  <div key={skill.name} className="p-3 rounded-xl bg-muted/30">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm">{skill.name}</span>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          skill.level === "Expert"
                            ? "bg-success/10 text-success border-success/20"
                            : skill.level === "Advanced"
                              ? "bg-primary/10 text-primary border-primary/20"
                              : "bg-muted-foreground/10 text-muted-foreground"
                        }`}
                      >
                        {skill.level}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-primary"
                          style={{ width: `${skill.weight * 100}%` }}
                        />
                      </div>
                      <span>w:{skill.weight.toFixed(1)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </TabsContent>

        {/* Learnings */}
        <TabsContent value="learnings" className="mt-4 space-y-3">
          {learningEntries.map((entry, idx) => (
            <Card key={idx} className="glass p-5 hover:shadow-glow transition">
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                  <Brain className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-sm">{entry.insight}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="text-[10px]">{entry.source}</Badge>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {entry.date}
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </TabsContent>

        {/* Raw Context */}
        <TabsContent value="raw" className="mt-4">
          <Card className="glass p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-display font-semibold">Raw Agent Context</h2>
                <p className="text-xs text-muted-foreground">
                  This condensed view is sent to agents for personalization
                </p>
              </div>
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div className="p-4 rounded-xl bg-muted/40 font-mono text-xs leading-relaxed">
              {`{
  "user": {
    "name": "Alex Kim",
    "school": "Stanford University",
    "graduation": "June 2026",
    "goal": "ML Research Internship at frontier AI lab"
  },
  "skills": ["TypeScript", "React", "Python", "PyTorch"],
  "preferences": {
    "locations": ["Ahmedabad", "San Francisco", "Remote"],
    "salary_min": 8000,
    "role_types": ["Internship", "New Grad SWE"],
    "company_sizes": ["Startup", "Mid-size"]
  },
  "memory": {
    "target_role": "ML Research Internship",
    "application_count": 23,
    "interview_rate": "21%",
    "recent_learnings": [
      "Stripe: API design focus",
      "Anthropic: alignment research valued"
    ]
  },
  "active_applications": [
    { "company": "Anthropic", "stage": "interview", "deadline": "Dec 10" },
    { "company": "Stripe", "stage": "oa", "deadline": "Dec 8" }
  ]
}`}
            </div>
            <div className="flex gap-2 mt-4">
              <Button variant="outline" size="sm" className="gap-1">
                <Database className="h-3 w-3" /> Copy context
              </Button>
              <Button variant="outline" size="sm" className="gap-1">
                <Sparkles className="h-3 w-3" /> Refresh
              </Button>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-w-md glass">
          <DialogHeader>
            <DialogTitle className="font-display">Add Memory Entry</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Key</label>
              <Input
                placeholder="e.g., preferred_company, interview_note"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="mt-1.5"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Value</label>
              <Input
                placeholder="e.g., Anthropic, Stripe, Linear"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="mt-1.5"
              />
            </div>
            <Button className="w-full bg-gradient-primary shadow-glow" onClick={handleAdd}>
              Save Memory
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
