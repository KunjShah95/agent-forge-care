import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  Sparkles, Brain, Target, FileSearch, MessageSquare, Network,
  Bell, ArrowRight, Zap, Check,
} from "lucide-react";

const agents = [
  { name: "Internship Agent", icon: Target, desc: "Hunts internships across 200+ sources daily." },
  { name: "Job Agent", icon: Zap, desc: "Tracks new grad & experienced roles in real time." },
  { name: "Research Agent", icon: FileSearch, desc: "Compiles company insights, salary intel, interview leaks." },
  { name: "Resume Agent", icon: Sparkles, desc: "Tailors resumes per role with ATS + keyword analysis." },
  { name: "Interview Agent", icon: MessageSquare, desc: "Runs mock interviews and grades your answers." },
  { name: "Networking Agent", icon: Network, desc: "Drafts outreach, tracks recruiter relationships." },
  { name: "Opportunity Monitor", icon: Bell, desc: "Watches your filters 24/7 with smart alerts." },
];

export default function Landing() {
  return (
    <div className="min-h-screen mesh-bg">
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/60 border-b border-border/50">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-primary shadow-glow">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <div className="font-display font-bold leading-none">AgentForge</div>
              <div className="text-[10px] text-muted-foreground">Career OS</div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#agents" className="hover:text-foreground transition">Agents</a>
            <a href="#features" className="hover:text-foreground transition">Features</a>
            <a href="#pricing" className="hover:text-foreground transition">Pricing</a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" asChild><Link to="/onboarding">Sign in</Link></Button>
            <Button size="sm" className="bg-gradient-primary shadow-glow" asChild>
              <Link to="/onboarding">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="container py-24 md:py-36 text-center">
        <Badge variant="outline" className="glass mb-6 gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse-glow" />
          7 specialized agents working for you, 24/7
        </Badge>
        <h1 className="font-display text-5xl md:text-7xl font-bold tracking-tight max-w-4xl mx-auto">
          Your AI career team.
          <br />
          <span className="gradient-text">Always recruiting for you.</span>
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
          AgentForge orchestrates a fleet of specialized agents that find opportunities,
          tailor your resume, prep your interviews, and grow your network — while you sleep.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" className="bg-gradient-primary shadow-glow gap-2" asChild>
            <Link to="/onboarding">Launch your career OS <ArrowRight className="h-4 w-4" /></Link>
          </Button>
          <Button size="lg" variant="outline" className="glass" asChild>
            <Link to="/app">Live demo</Link>
          </Button>
        </div>

        {/* Agent diagram */}
        <div className="mt-20 max-w-4xl mx-auto">
          <div className="glass rounded-2xl p-8 shadow-elegant">
            <div className="flex flex-col items-center gap-6">
              <div className="flex items-center gap-3 px-5 py-3 rounded-xl bg-gradient-primary shadow-glow text-primary-foreground">
                <Brain className="h-5 w-5" />
                <span className="font-display font-semibold">Planner Agent</span>
              </div>
              <div className="h-8 w-px bg-gradient-to-b from-primary to-transparent" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 w-full">
                {agents.slice(0, 7).map((a) => (
                  <div key={a.name} className="glass rounded-xl p-3 text-center hover:shadow-glow transition">
                    <a.icon className="h-5 w-5 mx-auto mb-2 text-primary" />
                    <div className="text-xs font-medium">{a.name}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Agents */}
      <section id="agents" className="container py-24">
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4">Agent System</Badge>
          <h2 className="font-display text-4xl md:text-5xl font-bold">A coordinated multi-agent fleet</h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            Every agent has a single job and does it exceptionally well. The Planner orchestrates them based on your goals.
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((a) => (
            <div key={a.name} className="glass rounded-2xl p-6 hover:shadow-glow transition group">
              <div className="h-10 w-10 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center mb-4 group-hover:scale-110 transition">
                <a.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-display font-semibold">{a.name}</h3>
              <p className="text-sm text-muted-foreground mt-1">{a.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="container py-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <Badge variant="outline" className="mb-4">Built for ambition</Badge>
            <h2 className="font-display text-4xl font-bold">Everything you need to land your next role.</h2>
            <ul className="mt-8 space-y-4">
              {[
                "Discover internships, jobs, hackathons, fellowships, scholarships",
                "Match scoring with explainable reasoning",
                "Kanban application tracker with reminders & timeline",
                "Resume Studio with ATS + keyword gap analysis",
                "Mock interviews — behavioral, technical, system design",
                "Networking CRM with outreach templates",
                "Analytics: conversion funnel, interview rate, skill demand",
              ].map((f) => (
                <li key={f} className="flex items-start gap-3">
                  <div className="h-5 w-5 rounded-full bg-gradient-primary flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Check className="h-3 w-3 text-primary-foreground" />
                  </div>
                  <span className="text-sm">{f}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="glass rounded-2xl p-2 shadow-elegant">
            <div className="rounded-xl bg-gradient-primary/5 border border-primary/10 aspect-[4/3] flex items-center justify-center">
              <div className="font-mono text-xs text-muted-foreground p-6 space-y-2">
                <div className="text-primary">{`>`} Planner Agent dispatching…</div>
                <div>{`>`} Internship Agent → scan complete (47 new)</div>
                <div>{`>`} Resume Agent → tailoring for Anthropic</div>
                <div>{`>`} Match score: <span className="text-success font-semibold">96%</span></div>
                <div>{`>`} Networking Agent → draft sent ✓</div>
                <div className="text-primary animate-pulse-glow">{`>`} _</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container py-24">
        <div className="glass rounded-3xl p-12 text-center bg-gradient-primary/5 border-primary/20">
          <h2 className="font-display text-4xl md:text-5xl font-bold">Stop searching. Start landing.</h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
            Set up your career profile in 3 minutes. Your agents start working immediately.
          </p>
          <Button size="lg" className="mt-8 bg-gradient-primary shadow-glow gap-2" asChild>
            <Link to="/onboarding">Get started free <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        </div>
      </section>

      <footer className="border-t border-border/50">
        <div className="container py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>© 2026 AgentForge Career OS</span>
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-foreground">Privacy</a>
            <a href="#" className="hover:text-foreground">Terms</a>
            <a href="#" className="hover:text-foreground">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
