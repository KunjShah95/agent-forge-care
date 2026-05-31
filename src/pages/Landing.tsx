import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  ArrowRight,
  Bell,
  Brain,
  Check,
  ClipboardList,
  FileSearch,
  Layers3,
  MessageSquare,
  Network,
  Radar,
  Sparkles,
  Target,
  Wand2,
  Zap,
} from "lucide-react";

const agentModules = [
  { name: "Planner Agent", icon: Brain, desc: "Breaks a vague goal into search, scoring, prep, and follow-up tasks." },
  { name: "Opportunity Monitor", icon: Radar, desc: "Watches new openings, deadlines, and alerts across your sources." },
  { name: "Internship Agent", icon: Target, desc: "Specialized discovery for internships, fellowships, hackathons, and research roles." },
  { name: "Job Agent", icon: Zap, desc: "Finds new grad, internship-to-full-time, remote, and startup roles." },
  { name: "Research Agent", icon: FileSearch, desc: "Collects company intel, interview signals, and market context." },
  { name: "Resume Agent", icon: Sparkles, desc: "Optimizes resumes, cover letters, and keywords for each opportunity." },
  { name: "Interview Agent", icon: MessageSquare, desc: "Generates mock questions, feedback, and interview plans." },
  { name: "Networking Agent", icon: Network, desc: "Drafts outreach and tracks recruiter, founder, and engineer relationships." },
];

const platformModules = [
  "Search across internships, jobs, research programs, hackathons, scholarships, and open-source programs",
  "Explainable match scoring with skills, location, experience, company fit, and role type",
  "Application tracker with stages, deadlines, reminders, and follow-up nudges",
  "Resume Studio for ATS checks, keyword gaps, and role-specific rewrites",
  "Interview Copilot for behavioral, technical, system design, and ML interviews",
  "Networking Hub for outreach templates, relationship tracking, and follow-up timing",
  "Opportunity Monitor that runs daily and notifies you when the right openings appear",
  "Long-term memory for skills, targets, preferences, interview notes, and applications",
];

const dailyLoop = [
  {
    step: "1. Sense",
    detail: "The monitor scans trusted sources, career pages, and public feeds for fresh opportunities.",
  },
  {
    step: "2. Reason",
    detail: "The planner compares openings against your profile, goals, and past outcomes.",
  },
  {
    step: "3. Act",
    detail: "Specialist agents tailor your resume, create outreach, and prepare interview material.",
  },
  {
    step: "4. Learn",
    detail: "Memory updates with every save, application, interview, and outcome so the system improves.",
  },
];

const comparison = [
  {
    title: "Old way",
    points: [
      "Jump between job boards, docs, and spreadsheets",
      "Repeat the same search every day",
      "Manual resume edits for every application",
    ],
  },
  {
    title: "AgentForge way",
    points: [
      "One command center for discovery, prep, and tracking",
      "Always-on agents watching your market and goals",
      "Personalized actions based on long-term memory",
    ],
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen mesh-bg">
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/60 border-b border-border/50">
        <div className="container flex h-16 items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-primary shadow-glow">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <div className="font-display font-bold leading-none">AgentForge</div>
              <div className="text-[10px] text-muted-foreground">Career OS</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#vision" className="hover:text-foreground transition">Vision</a>
            <a href="#agents" className="hover:text-foreground transition">Agents</a>
            <a href="#workflow" className="hover:text-foreground transition">Workflow</a>
            <a href="#roadmap" className="hover:text-foreground transition">Roadmap</a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
            <Button size="sm" className="bg-gradient-primary shadow-glow" asChild>
              <Link to="/onboarding">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      <section className="container py-20 md:py-28">
        <div className="grid gap-10 lg:grid-cols-[1.15fr_0.85fr] items-center">
          <div>
            <Badge variant="outline" className="glass mb-6 gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse-glow" />
              Multi-agent career operating system for internships, jobs, and research
            </Badge>
            <h1 className="font-display text-5xl md:text-7xl font-bold tracking-tight max-w-3xl">
              Your AI career team,
              <br />
              <span className="gradient-text">working before you even ask.</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground max-w-2xl">
              AgentForge is the orchestrator for your career search. It continuously finds opportunities,
              scores the best matches, prepares your applications, and helps you network and interview with confidence.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button size="lg" className="bg-gradient-primary shadow-glow gap-2" asChild>
                <Link to="/onboarding">Launch your career OS <ArrowRight className="h-4 w-4" /></Link>
              </Button>
              <Button size="lg" variant="outline" className="glass" asChild>
                <Link to="/app">Open the dashboard</Link>
              </Button>
            </div>

            <div className="mt-10 grid gap-3 sm:grid-cols-3">
              {[
                { value: "24/7", label: "Opportunity monitoring" },
                { value: "8", label: "Specialist agents" },
                { value: "1", label: "Unified memory layer" },
              ].map((item) => (
                <Card key={item.label} className="glass p-4">
                  <div className="text-2xl font-display font-bold gradient-text">{item.value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{item.label}</div>
                </Card>
              ))}
            </div>
          </div>

          <Card className="glass p-6 shadow-elegant" id="vision">
            <div className="flex items-center justify-between gap-3 mb-5">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Architecture</div>
                <h2 className="font-display text-2xl font-bold mt-1">Planner-first agent engine</h2>
              </div>
              <Badge className="bg-success/10 text-success border-success/20">Live concept</Badge>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-primary/20 bg-gradient-primary/5 p-4 text-center">
                <div className="inline-flex items-center gap-2 rounded-full bg-background/70 px-4 py-2 text-sm font-medium border border-border/60">
                  <Brain className="h-4 w-4 text-primary" />
                  Planner Agent
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  Turns one goal into an execution plan and delegates the work.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { icon: Target, label: "Internship Agent" },
                  { icon: Zap, label: "Job Agent" },
                  { icon: FileSearch, label: "Research Agent" },
                  { icon: Sparkles, label: "Resume Agent" },
                ].map((item) => (
                  <div key={item.label} className="glass rounded-xl p-3 text-center">
                    <item.icon className="h-5 w-5 mx-auto mb-2 text-primary" />
                    <div className="text-xs font-medium">{item.label}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { icon: MessageSquare, label: "Interview Agent" },
                  { icon: Network, label: "Networking Agent" },
                  { icon: Bell, label: "Opportunity Monitor" },
                  { icon: Layers3, label: "Memory Layer" },
                ].map((item) => (
                  <div key={item.label} className="glass rounded-xl p-3 text-center">
                    <item.icon className="h-5 w-5 mx-auto mb-2 text-accent" />
                    <div className="text-xs font-medium">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </section>

      <section id="agents" className="container py-20">
        <div className="text-center mb-12">
          <Badge variant="outline" className="mb-4">Agent system</Badge>
          <h2 className="font-display text-4xl md:text-5xl font-bold">Specialized agents, one shared objective</h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            Each agent owns a single part of the workflow. The planner coordinates them so the whole system behaves like a personal career team.
          </p>
        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
          {agentModules.map((agent) => (
            <Card key={agent.name} className="glass p-5 hover:shadow-glow transition group">
              <div className="h-10 w-10 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center mb-4 group-hover:scale-110 transition">
                <agent.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-display font-semibold">{agent.name}</h3>
              <p className="text-sm text-muted-foreground mt-1">{agent.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      <section id="workflow" className="container py-20">
        <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-10 items-start">
          <div>
            <Badge variant="outline" className="mb-4">What it does daily</Badge>
            <h2 className="font-display text-4xl font-bold">A loop that compounds every day</h2>
            <p className="mt-4 text-muted-foreground">
              The real product isn’t just search. It is continuous execution: discover, reason, act, learn, repeat.
            </p>

            <div className="mt-8 space-y-4">
              {dailyLoop.map((item) => (
                <Card key={item.step} className="glass p-5">
                  <div className="font-semibold">{item.step}</div>
                  <p className="text-sm text-muted-foreground mt-1">{item.detail}</p>
                </Card>
              ))}
            </div>
          </div>

          <div className="grid gap-4">
            <div className="grid md:grid-cols-2 gap-4">
              {comparison.map((group) => (
                <Card key={group.title} className="glass p-5">
                  <div className="font-display text-lg font-bold">{group.title}</div>
                  <ul className="mt-4 space-y-3">
                    {group.points.map((point) => (
                      <li key={point} className="flex items-start gap-3 text-sm text-muted-foreground">
                        <Check className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              ))}
            </div>

            <Card className="glass p-6 border-primary/20 bg-gradient-primary/5">
              <div className="flex items-center gap-2 text-sm font-medium text-primary">
                <Wand2 className="h-4 w-4" />
                Example query flow
              </div>
              <div className="mt-4 font-mono text-xs space-y-2 text-muted-foreground">
                <div>{`>`} Find AI internships in Ahmedabad</div>
                <div>{`>`} Planner Agent → breaks down the task</div>
                <div>{`>`} Internship Agent → searches sources</div>
                <div>{`>`} Match engine → ranks by skills + location</div>
                <div>{`>`} Resume Agent → prepares tailored application assets</div>
                <div>{`>`} Monitor → watches deadlines and alerts you</div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      <section className="container py-20">
        <div className="text-center mb-12">
          <Badge variant="outline" className="mb-4">Platform modules</Badge>
          <h2 className="font-display text-4xl md:text-5xl font-bold">Built as a complete career operating system</h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            The MVP starts with discovery and matching, then expands into applications, networking, interview prep, and personalized monitoring.
          </p>
        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
          {platformModules.map((feature) => (
            <Card key={feature} className="glass p-5">
              <div className="h-10 w-10 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                <ClipboardList className="h-5 w-5 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">{feature}</p>
            </Card>
          ))}
        </div>
      </section>

      <section id="roadmap" className="container py-20">
        <Card className="glass rounded-3xl p-10 md:p-12 text-center bg-gradient-primary/5 border-primary/20">
          <Badge className="mb-4 bg-primary/10 text-primary border-primary/20">MVP roadmap</Badge>
          <h2 className="font-display text-4xl md:text-5xl font-bold">Start with search. Grow into autopilot.</h2>
          <p className="mt-4 text-muted-foreground max-w-3xl mx-auto">
            Phase 1 focuses on opportunity discovery, profile memory, and match scoring. Phase 2 adds resume tailoring, applications, and interview prep. Phase 3 turns the product into a fully proactive career companion.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" className="bg-gradient-primary shadow-glow gap-2" asChild>
              <Link to="/onboarding">Build your profile <ArrowRight className="h-4 w-4" /></Link>
            </Button>
            <Button size="lg" variant="outline" className="glass" asChild>
              <Link to="/app">See the dashboard</Link>
            </Button>
          </div>
        </Card>
      </section>

      <footer className="border-t border-border/50">
        <div className="container py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>© 2026 AgentForge Career OS</span>
          </div>
          <div className="flex gap-6">
            <a href="#vision" className="hover:text-foreground">Vision</a>
            <a href="#workflow" className="hover:text-foreground">Workflow</a>
            <a href="#roadmap" className="hover:text-foreground">Roadmap</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
