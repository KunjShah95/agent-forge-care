import { useEffect, useRef, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

import { ThemeToggle } from "@/components/ThemeToggle";
import { ScrollReveal, StaggerContainer, StaggerItem, ScaleReveal } from "@/components/ScrollReveal";
import { ParallaxSection, ParallaxBackground } from "@/components/ParallaxSection";
import {
  ArrowRight,
  Bell,
  Brain,
  ChevronRight,
  ClipboardList,
  Cpu,
  FileSearch,
  Layers3,
  MessageSquare,
  Network,
  Orbit,
  Radar,
  Sparkles,
  Star,
  Target,
  Wand2,
  Zap,
} from "lucide-react";

const agentModules = [
  { name: "Planner Agent", icon: Brain, desc: "Breaks a vague goal into search, scoring, prep, and follow-up tasks.", accent: "from-violet-500/20 to-purple-500/20" },
  { name: "Opportunity Monitor", icon: Radar, desc: "Watches new openings, deadlines, and alerts across your sources.", accent: "from-orange-500/20 to-amber-500/20" },
  { name: "Internship Agent", icon: Target, desc: "Specialized discovery for internships, fellowships, hackathons, and research roles.", accent: "from-blue-500/20 to-cyan-500/20" },
  { name: "Job Agent", icon: Zap, desc: "Finds new grad, internship-to-full-time, remote, and startup roles.", accent: "from-amber-500/20 to-yellow-500/20" },
  { name: "Research Agent", icon: FileSearch, desc: "Collects company intel, interview signals, and market context.", accent: "from-purple-500/20 to-pink-500/20" },
  { name: "Resume Agent", icon: Sparkles, desc: "Optimizes resumes, cover letters, and keywords for each opportunity.", accent: "from-emerald-500/20 to-green-500/20" },
  { name: "Interview Agent", icon: MessageSquare, desc: "Generates mock questions, feedback, and interview plans.", accent: "from-rose-500/20 to-red-500/20" },
  { name: "Networking Agent", icon: Network, desc: "Drafts outreach and tracks recruiter, founder, and engineer relationships.", accent: "from-cyan-500/20 to-teal-500/20" },
];

const stats = [
  { value: "24/7", label: "Opportunity monitoring", icon: Radar },
  { value: "8", label: "Specialist agents", icon: Cpu },
  { value: "50+", label: "Job sources scanned", icon: Layers3 },
  { value: "78%", label: "Match accuracy", icon: Star },
];

const dailyLoop = [
  { step: "01", title: "Sense", detail: "The monitor scans trusted sources, career pages, and public feeds for fresh opportunities.", icon: Radar },
  { step: "02", title: "Reason", detail: "The planner compares openings against your profile, goals, and past outcomes.", icon: Brain },
  { step: "03", title: "Act", detail: "Specialist agents tailor your resume, create outreach, and prepare interview material.", icon: Zap },
  { step: "04", title: "Learn", detail: "Memory updates with every save, application, interview, and outcome so the system improves.", icon: Layers3 },
];

const features = [
  "Search across internships, jobs, research programs, hackathons, and open-source programs",
  "Explainable match scoring with skills, location, experience, company fit, and role type",
  "Application tracker with stages, deadlines, reminders, and follow-up nudges",
  "Resume Studio for ATS checks, keyword gaps, and role-specific rewrites",
  "Interview Copilot for behavioral, technical, system design, and ML interviews",
  "Networking Hub with outreach templates, relationship tracking, and follow-up timing",
  "Opportunity Monitor that runs daily and notifies you when the right openings appear",
  "Long-term memory for skills, targets, preferences, interview notes, and applications",
];

const principles = [
  {
    title: "Old way",
    icon: "×",
    points: [
      "Jump between job boards, docs, and spreadsheets",
      "Repeat the same search every day",
      "Manual resume edits for every application",
    ],
    color: "border-red-500/30",
  },
  {
    title: "AgentForge way",
    icon: "✓",
    points: [
      "One command center for discovery, prep, and tracking",
      "Always-on agents watching your market and goals",
      "Personalized actions based on long-term memory",
    ],
    color: "border-emerald-500/30",
  },
];

export default function Landing() {
  const [mousePos, setMousePos] = useState({ x: 50, y: 0 });
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (heroRef.current) {
        const rect = heroRef.current.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        setMousePos({ x, y });
      }
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <div className="min-h-screen bg-background noise-overlay">
      <Helmet>
        <title>AgentForge Career OS — AI-Powered Career Platform</title>
        <meta name="description" content="AgentForge Career OS is a multi-agent AI system that automates your entire job search and career management workflow. Discover opportunities, optimize resumes, prepare for interviews, and track your career pipeline." />
        <meta property="og:title" content="AgentForge Career OS — AI-Powered Career Platform" />
        <meta property="og:description" content="A multi-agent AI system that automates your entire job search and career management workflow with 8 specialized agents." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://agentforge.ai" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="AgentForge Career OS" />
        <meta name="twitter:description" content="AI-powered career operating system with 8 specialized agents for job search automation." />
      </Helmet>

      {/* ── Navigation ── */}
      <header className="fixed top-0 left-0 right-0 z-50">
        <div className="absolute inset-0 bg-background/70 backdrop-blur-xl border-b border-border/40" />
        <div className="relative container flex h-16 items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-1 shadow-glow transition-transform duration-300 group-hover:scale-110">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
              <div className="absolute inset-0 rounded-xl bg-gradient-1 animate-pulse-glow opacity-50" />
            </div>
            <div>
              <div className="font-display font-bold leading-none tracking-tight">AgentForge</div>
              <div className="text-[10px] text-muted-foreground tracking-wider uppercase">Career OS</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {["Vision", "Agents", "Workflow", "Roadmap"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="px-3.5 py-2 text-sm text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted/50 transition-all duration-200"
              >
                {item}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
            <Button size="sm" className="bg-gradient-1 shadow-glow hover:shadow-glow-lg transition-all duration-300" asChild>
              <Link to="/register">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section ref={heroRef} className="relative min-h-screen flex items-center overflow-hidden pt-16">
        {/* Animated grid background */}
        <div className="absolute inset-0 animated-grid" />
        
        {/* Background beams */}
        <div className="absolute inset-0 bg-beams opacity-60" />

        {/* Spotlight effect */}
        <div
          className="absolute inset-0 transition-opacity duration-700 pointer-events-none"
          style={{
            background: `radial-gradient(800px circle at ${mousePos.x}% ${mousePos.y}%, hsl(var(--primary) / 0.10), transparent 60%)`,
          }}
        />

        {/* Floating orbs */}
        <div className="absolute top-1/4 right-1/4 w-64 h-64 rounded-full bg-gradient-1 opacity-[0.04] blur-3xl animate-float-slow" />
        <div className="absolute bottom-1/3 left-1/4 w-48 h-48 rounded-full bg-gradient-3 opacity-[0.04] blur-3xl animate-float" style={{ animationDelay: "-2s" }} />

        {/* Orbital lines */}
        <div className="absolute top-1/3 right-[15%] w-32 h-32 border border-primary/10 rounded-full animate-orbit" />
        <div className="absolute top-1/3 right-[15%] w-20 h-20 border border-accent/10 rounded-full animate-orbit-reverse" />

        <div className="relative container py-24 md:py-32">
          <div className="max-w-4xl">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.25, 0.1, 0, 1] }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/5 border border-primary/20 text-sm text-primary mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
                </span>
                Multi-agent career operating system
                <ChevronRight className="h-3.5 w-3.5 ml-1" />
              </div>
            </motion.div>

            {/* Headline */}
            <motion.h1
              className="font-display text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95]"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15, ease: [0.25, 0.1, 0, 1] }}
            >
              Your AI career team,
              <br />
              <span className="gradient-text-1">working before you</span>
              <br />
              <span className="gradient-text-shimmer">even ask.</span>
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl leading-relaxed"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3, ease: [0.25, 0.1, 0, 1] }}
            >
              AgentForge Career OS is your personal career team — 8 specialized AI agents working 24/7 to discover opportunities across 50+ sources, optimize your resume with 78% match accuracy, and prepare you for every interview.
            </motion.p>

            {/* CTA */}
            <motion.div
              className="mt-10 flex flex-wrap items-center gap-4"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.45, ease: [0.25, 0.1, 0, 1] }}
            >
              <Button size="lg" className="bg-gradient-1 shadow-glow hover:shadow-glow-lg transition-all duration-300 gap-2 h-12 px-6 text-base" asChild>
                <Link to="/register">
                  Launch your career OS
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" className="glass-strong h-12 px-6 text-base gap-2" asChild>
                <Link to="/app">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Open the dashboard
                </Link>
              </Button>
            </motion.div>

            {/* Stats */}
            <motion.div
              className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4"
              initial="hidden"
              animate="visible"
              variants={{
                hidden: {},
                visible: {
                  transition: { staggerChildren: 0.1, delayChildren: 0.6 },
                },
              }}
            >
              {stats.map((stat) => (
                <motion.div
                  key={stat.label}
                  variants={{
                    hidden: { opacity: 0, y: 30 },
                    visible: {
                      opacity: 1,
                      y: 0,
                      transition: { duration: 0.5, ease: [0.25, 0.1, 0, 1] },
                    },
                  }}
                  className="group relative p-5 rounded-2xl glass-card"
                >
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/5 via-transparent to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <div className="relative">
                    <stat.icon className="h-4 w-4 text-primary/60 mb-2" />
                    <div className="text-3xl font-display font-bold gradient-text-1">{stat.value}</div>
                    <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Vision / Architecture Section ── */}
      <ParallaxSection speed={0.08}>
        <section id="vision" className="relative py-24 md:py-32">
          <ParallaxBackground className="animated-grid-subtle" speed={0.2} />
          <div className="relative container">
            <ScrollReveal>
              <div className="text-center mb-16">
                <Badge variant="outline" className="mb-4 px-3 py-1.5 text-xs tracking-wider uppercase">Architecture</Badge>
                <h2 className="font-display text-4xl md:text-6xl font-bold">Planner-first agent engine</h2>
                <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
                  One goal. Eight agents. Zero repetition. The planner decomposes your ambition into an execution graph and delegates each branch to the right specialist.
                </p>
              </div>
            </ScrollReveal>

            <div className="grid lg:grid-cols-[1.3fr_0.7fr] gap-8 items-start">
              {/* Planner hub */}
              <ScrollReveal direction="left" distance={40}>
                <div className="bento-card p-8 md:p-10">
                  <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
                  <div className="relative">
                    <div className="inline-flex items-center gap-3 px-5 py-2.5 rounded-full bg-gradient-1 shadow-glow text-primary-foreground text-sm font-medium">
                      <Brain className="h-5 w-5" />
                      Planner Agent
                      <Badge className="bg-white/20 text-white border-none text-[10px]">Central orchestrator</Badge>
                    </div>
                    <p className="mt-5 text-base text-muted-foreground leading-relaxed max-w-lg">
                      Turns one goal into an execution plan and delegates the work to specialist agents. Each agent reports back with structured results that feed into the next step.
                    </p>

                    {/* Agent grid - top row */}
                    <motion.div
                      className="mt-8 grid grid-cols-4 gap-3"
                      initial="hidden"
                      whileInView="visible"
                      viewport={{ once: true }}
                      variants={{
                        hidden: {},
                        visible: { transition: { staggerChildren: 0.06 } },
                      }}
                    >
                      {agentModules.slice(0, 4).map((agent) => (
                        <motion.div
                          key={agent.name}
                          variants={{
                            hidden: { opacity: 0, y: 20, scale: 0.9 },
                            visible: {
                              opacity: 1,
                              y: 0,
                              scale: 1,
                              transition: { duration: 0.4, ease: [0.25, 0.1, 0, 1] },
                            },
                          }}
                          className="group relative"
                        >
                          <div className={`rounded-xl p-4 text-center bg-gradient-to-br ${agent.accent} border border-border/50 hover:border-primary/30 transition-all duration-300 hover:shadow-glow`}>
                            <agent.icon className="h-6 w-6 mx-auto mb-2 text-primary group-hover:scale-110 transition-transform duration-300" />
                            <div className="text-xs font-medium line-clamp-1">{agent.name.split(" ")[0]}</div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>

                    {/* Agent grid - bottom row */}
                    <motion.div
                      className="mt-3 grid grid-cols-4 gap-3"
                      initial="hidden"
                      whileInView="visible"
                      viewport={{ once: true }}
                      variants={{
                        hidden: {},
                        visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
                      }}
                    >
                      {agentModules.slice(4, 8).map((agent) => (
                        <motion.div
                          key={agent.name}
                          variants={{
                            hidden: { opacity: 0, y: 20, scale: 0.9 },
                            visible: {
                              opacity: 1,
                              y: 0,
                              scale: 1,
                              transition: { duration: 0.4, ease: [0.25, 0.1, 0, 1] },
                            },
                          }}
                          className="group relative"
                        >
                          <div className={`rounded-xl p-4 text-center bg-gradient-to-br ${agent.accent} border border-border/50 hover:border-accent/30 transition-all duration-300 hover:shadow-glow`}>
                            <agent.icon className="h-6 w-6 mx-auto mb-2 text-accent group-hover:scale-110 transition-transform duration-300" />
                            <div className="text-xs font-medium line-clamp-1">{agent.name.split(" ")[0]}</div>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  </div>
                </div>
              </ScrollReveal>

              {/* Info panel */}
              <div className="space-y-4">
                {[
                  { icon: Brain, title: "Task Decomposition", desc: "Breaks goals into discrete, assignable sub-tasks for specialist agents." },
                  { icon: Layers3, title: "Shared Memory", desc: "All agents access the same evolving knowledge base of your profile and history." },
                  { icon: Radar, title: "Continuous Loop", desc: "Sense → Reason → Act → Learn. The system compounds knowledge every cycle." },
                ].map((item, i) => (
                  <ScrollReveal key={item.title} direction="right" distance={30} delay={i * 0.1}>
                    <div className="bento-card p-5">
                      <div className="flex items-start gap-4">
                        <div className="h-10 w-10 rounded-lg bg-gradient-1/10 border border-primary/20 flex items-center justify-center shrink-0">
                          <item.icon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <div className="font-display font-semibold">{item.title}</div>
                          <p className="text-sm text-muted-foreground mt-1">{item.desc}</p>
                        </div>
                      </div>
                    </div>
                  </ScrollReveal>
                ))}
              </div>
            </div>
          </div>
        </section>
      </ParallaxSection>

      {/* ── Agents Section ── */}
      <ParallaxSection speed={0.06}>
        <section id="agents" className="relative py-24 md:py-32">
          <ParallaxBackground className="bg-beams opacity-30" speed={0.25} />
          <div className="relative container">
            <ScrollReveal>
              <div className="text-center mb-16">
                <Badge variant="outline" className="mb-4 px-3 py-1.5 text-xs tracking-wider uppercase">Agent system</Badge>
                <h2 className="font-display text-4xl md:text-6xl font-bold">Specialized agents,<br />one shared objective</h2>
                <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
                  Each agent owns a single part of the workflow. The planner coordinates them so the whole system behaves like a personal career team.
                </p>
              </div>
            </ScrollReveal>

            <StaggerContainer staggerDelay={0.06}>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
                {agentModules.map((agent) => (
                  <StaggerItem key={agent.name}>
                    <div className="glow-card">
                      <div className="bento-card p-6 h-full">
                        <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${agent.accent} opacity-60`} />
                        <div className="relative pt-2">
                          <div className="h-12 w-12 rounded-xl bg-gradient-1/10 border border-primary/20 flex items-center justify-center mb-5">
                            <agent.icon className="h-6 w-6 text-primary" />
                          </div>
                          <h3 className="font-display text-lg font-semibold">{agent.name}</h3>
                          <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{agent.desc}</p>
                        </div>
                      </div>
                    </div>
                  </StaggerItem>
                ))}
              </div>
            </StaggerContainer>
          </div>
        </section>
      </ParallaxSection>

      {/* ── Workflow Section ── */}
      <ParallaxSection speed={0.06}>
        <section id="workflow" className="relative py-24 md:py-32">
          <ParallaxBackground className="animated-grid-subtle opacity-50" speed={0.2} />
          <div className="relative container">
            <ScrollReveal>
              <div className="text-center mb-16">
                <Badge variant="outline" className="mb-4 px-3 py-1.5 text-xs tracking-wider uppercase">Daily workflow</Badge>
                <h2 className="font-display text-4xl md:text-6xl font-bold">A loop that compounds<br />every day</h2>
                <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
                  The real product isn't just search. It is continuous execution: discover, reason, act, learn, repeat.
                </p>
              </div>
            </ScrollReveal>

            <div className="grid lg:grid-cols-2 gap-8 items-start">
              {/* Loop steps */}
              <div className="relative space-y-4">
                {/* Connecting line */}
                <div className="absolute left-[23px] top-8 bottom-8 w-px bg-gradient-to-b from-primary/30 via-accent/20 to-primary/10 hidden md:block" />

                {dailyLoop.map((step, i) => (
                  <ScrollReveal key={step.step} direction="left" distance={40} delay={i * 0.1}>
                    <div className="bento-card p-6 md:pl-16 relative">
                      <div className="hidden md:flex absolute left-0 top-0 bottom-0 w-14 items-center justify-center">
                        <div className="h-10 w-10 rounded-full bg-gradient-1 shadow-glow flex items-center justify-center">
                          <step.icon className="h-5 w-5 text-primary-foreground" />
                        </div>
                        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-[10px] font-mono font-bold text-primary">
                          {step.step}
                        </div>
                      </div>
                      <div className="md:hidden flex items-center gap-3 mb-3">
                        <div className="h-8 w-8 rounded-full bg-gradient-1 shadow-glow flex items-center justify-center">
                          <step.icon className="h-4 w-4 text-primary-foreground" />
                        </div>
                        <span className="font-mono text-sm font-bold text-primary">{step.step}</span>
                        <span className="font-display font-semibold">{step.title}</span>
                      </div>
                      <div className="hidden md:block font-display text-lg font-semibold mb-2">{step.step} — {step.title}</div>
                      <p className="text-sm text-muted-foreground leading-relaxed">{step.detail}</p>
                    </div>
                  </ScrollReveal>
                ))}
              </div>

              {/* Comparison + example */}
              <div className="space-y-5">
                <ScrollReveal direction="right" distance={40}>
                  <div className="grid gap-4">
                    {principles.map((group) => (
                      <div key={group.title} className={`bento-card p-6 border-l-2 ${group.color}`}>
                        <div className="flex items-center gap-2 mb-3">
                          <span className={`text-lg font-bold ${group.color.includes("red") ? "text-red-400" : "text-emerald-400"}`}>
                            {group.icon}
                          </span>
                          <div className="font-display text-lg font-bold">{group.title}</div>
                        </div>
                        <ul className="space-y-3">
                          {group.points.map((point) => (
                            <li key={point} className="flex items-start gap-3 text-sm text-muted-foreground">
                              <div className={`h-1.5 w-1.5 rounded-full mt-2 ${group.color.includes("red") ? "bg-red-400" : "bg-emerald-400"}`} />
                              <span>{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </ScrollReveal>

                {/* Example flow */}
                <ScaleReveal>
                  <div className="bento-card p-6 bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
                    <div className="flex items-center gap-2 text-sm font-medium mb-4">
                      <div className="h-8 w-8 rounded-lg bg-gradient-1 flex items-center justify-center">
                        <Wand2 className="h-4 w-4 text-primary-foreground" />
                      </div>
                      <span className="text-primary">Example query flow</span>
                    </div>
                    <div className="space-y-2.5 text-sm">
                      {[
                        { agent: "You", text: "Find AI internships in Ahmedabad", color: "text-foreground" },
                        { agent: "Planner", text: "Breaks down the task into sub-tasks", color: "text-violet-400" },
                        { agent: "Internship Agent", text: "Searches 50+ sources for matching roles", color: "text-blue-400" },
                        { agent: "Match Engine", text: "Ranks by skills, location & experience", color: "text-emerald-400" },
                        { agent: "Resume Agent", text: "Prepares tailored application assets", color: "text-amber-400" },
                        { agent: "Monitor", text: "Watches deadlines and alerts you", color: "text-cyan-400" },
                      ].map((line, i) => (
                        <motion.div
                          key={i}
                          className="flex items-start gap-2.5 font-mono text-xs"
                          initial={{ opacity: 0, x: -10 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ delay: i * 0.08, duration: 0.3 }}
                        >
                          <span className="text-primary font-semibold shrink-0">▸</span>
                          <span className={line.color}>
                            <span className="font-semibold">{line.agent}:</span> {line.text}
                          </span>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                </ScaleReveal>
              </div>
            </div>
          </div>
        </section>
      </ParallaxSection>

      {/* ── Features Section ── */}
      <section className="relative py-24 md:py-32">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/[0.02] to-transparent" />
        <div className="relative container">
          <ScrollReveal>
            <div className="text-center mb-16">
              <Badge variant="outline" className="mb-4 px-3 py-1.5 text-xs tracking-wider uppercase">Platform modules</Badge>
              <h2 className="font-display text-4xl md:text-6xl font-bold">Built as a complete<br />career operating system</h2>
              <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
                The MVP starts with discovery and matching, then expands into applications, networking, interview prep, and personalized monitoring.
              </p>
            </div>
          </ScrollReveal>

          <StaggerContainer staggerDelay={0.05}>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {features.map((feature) => (
                <StaggerItem key={feature}>
                  <div className="bento-card p-6">
                    <div className="h-10 w-10 rounded-xl bg-gradient-1/10 border border-primary/20 flex items-center justify-center mb-4">
                      <ClipboardList className="h-5 w-5 text-primary" />
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{feature}</p>
                  </div>
                </StaggerItem>
              ))}
            </div>
          </StaggerContainer>
        </div>
      </section>

      {/* ── Roadmap / CTA Section ── */}
      <ParallaxSection speed={0.08}>
        <section id="roadmap" className="relative py-24 md:py-32">
          <ParallaxBackground className="animated-grid opacity-30" speed={0.25} />
          <div className="relative container">
            <ScrollReveal>
              <div className="bento-card p-12 md:p-16 text-center relative overflow-hidden">
                {/* Decorative gradient orbs */}
                <motion.div
                  className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-gradient-1 opacity-[0.06] blur-3xl"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
                />
                <motion.div
                  className="absolute -bottom-20 -left-20 w-64 h-64 rounded-full bg-gradient-3 opacity-[0.06] blur-3xl"
                  animate={{ rotate: -360 }}
                  transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                />

                <div className="relative">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                  >
                    <Badge className="mb-6 bg-gradient-1 text-primary-foreground border-none px-4 py-1.5 text-xs tracking-wider uppercase">
                      <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                      MVP roadmap
                    </Badge>
                  </motion.div>
                  <motion.h2
                    className="font-display text-4xl md:text-6xl font-bold leading-tight"
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                  >
                    Start with search.<br />
                    <span className="gradient-text-1">Grow into autopilot.</span>
                  </motion.h2>
                  <motion.p
                    className="mt-6 text-lg text-muted-foreground max-w-3xl mx-auto leading-relaxed"
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                  >
                    Phase 1 focuses on opportunity discovery, profile memory, and match scoring. Phase 2 adds resume tailoring, applications, and interview prep. Phase 3 turns the product into a fully proactive career companion.
                  </motion.p>
                  <motion.div
                    className="mt-10 flex flex-wrap items-center justify-center gap-4"
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                  >
                    <Button size="lg" className="bg-gradient-1 shadow-glow hover:shadow-glow-lg transition-all duration-300 gap-2 h-12 px-6 text-base" asChild>
                      <Link to="/register">
                        Build your profile
                        <ArrowRight className="h-5 w-5" />
                      </Link>
                    </Button>
                    <Button size="lg" variant="outline" className="glass-strong h-12 px-6 text-base" asChild>
                      <Link to="/app">See the dashboard</Link>
                    </Button>
                  </motion.div>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>
      </ParallaxSection>

      {/* ── Footer ── */}
      <footer className="relative border-t border-border/40">
        <div className="container py-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded-lg bg-gradient-1 flex items-center justify-center">
              <Sparkles className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <span className="text-sm text-muted-foreground">© 2026 AgentForge Career OS</span>
          </div>
          <div className="flex gap-6 text-sm">
            {["Vision", "Agents", "Workflow", "Roadmap"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-muted-foreground hover:text-foreground transition-colors duration-200"
              >
                {item}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
