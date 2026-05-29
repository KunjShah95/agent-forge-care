import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sparkles, ArrowRight, ArrowLeft, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

const steps = ["Welcome", "About You", "Skills", "Preferences", "Goals", "Launch"];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [skills, setSkills] = useState<string[]>(["TypeScript", "React", "Python"]);
  const [skillInput, setSkillInput] = useState("");
  const navigate = useNavigate();

  const next = () => step < steps.length - 1 ? setStep(s => s + 1) : navigate("/app");
  const prev = () => setStep(s => Math.max(0, s - 1));
  const addSkill = () => { if (skillInput.trim()) { setSkills([...skills, skillInput.trim()]); setSkillInput(""); } };

  return (
    <div className="min-h-screen mesh-bg flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="h-9 w-9 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-lg">AgentForge Career OS</span>
        </div>

        <div className="glass rounded-2xl p-8 shadow-elegant">
          <div className="flex items-center justify-between mb-2 text-xs text-muted-foreground">
            <span>Step {step + 1} of {steps.length}</span>
            <span>{steps[step]}</span>
          </div>
          <Progress value={((step + 1) / steps.length) * 100} className="h-1.5 mb-8" />

          {step === 0 && (
            <div className="text-center py-8 animate-fade-in">
              <h1 className="font-display text-3xl font-bold">Welcome to your career OS.</h1>
              <p className="mt-3 text-muted-foreground">In 3 minutes, your agents will be working for you.</p>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="font-display text-2xl font-bold">Tell us about you</h2>
              <div className="grid grid-cols-2 gap-4">
                <div><Label>Full name</Label><Input defaultValue="Alex Kim" className="mt-1.5" /></div>
                <div><Label>Email</Label><Input defaultValue="alex@stanford.edu" className="mt-1.5" /></div>
                <div><Label>School</Label><Input defaultValue="Stanford University" className="mt-1.5" /></div>
                <div><Label>Graduation</Label><Input defaultValue="June 2026" className="mt-1.5" /></div>
              </div>
              <div><Label>Bio / pitch</Label><Textarea className="mt-1.5" defaultValue="CS major focused on AI infrastructure. Shipped 4 OSS projects, intern @ Meta '24." /></div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="font-display text-2xl font-bold">Your skills</h2>
              <p className="text-sm text-muted-foreground">We use these to match you to opportunities.</p>
              <div className="flex flex-wrap gap-2 min-h-[2.5rem] p-3 rounded-lg border bg-muted/30">
                {skills.map((s) => (
                  <Badge key={s} variant="secondary" className="gap-1">
                    {s}
                    <X className="h-3 w-3 cursor-pointer" onClick={() => setSkills(skills.filter(x => x !== s))} />
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                  placeholder="Add a skill (e.g. PyTorch)"
                />
                <Button onClick={addSkill} variant="secondary">Add</Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="font-display text-2xl font-bold">What are you looking for?</h2>
              <div className="grid grid-cols-2 gap-4">
                <div><Label>Preferred locations</Label><Input defaultValue="SF, NYC, Remote" className="mt-1.5" /></div>
                <div><Label>Salary expectation</Label><Input defaultValue="$150k+" className="mt-1.5" /></div>
                <div><Label>Role types</Label><Input defaultValue="Internship, New Grad SWE" className="mt-1.5" /></div>
                <div><Label>Company size</Label><Input defaultValue="Startup, Mid-size" className="mt-1.5" /></div>
              </div>
              <div><Label>Portfolio link</Label><Input defaultValue="https://alexkim.dev" className="mt-1.5" /></div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="font-display text-2xl font-bold">Your career goal</h2>
              <p className="text-sm text-muted-foreground">Your Planner Agent uses this to prioritize work.</p>
              <Textarea
                rows={5}
                defaultValue="Land an ML research internship at a frontier lab for Summer 2026, with an offer by mid-February."
                className="mt-1.5"
              />
            </div>
          )}

          {step === 5 && (
            <div className="text-center py-8 animate-fade-in">
              <div className="h-16 w-16 rounded-2xl bg-gradient-primary mx-auto flex items-center justify-center shadow-glow animate-pulse-glow">
                <Sparkles className="h-8 w-8 text-primary-foreground" />
              </div>
              <h2 className="font-display text-3xl font-bold mt-6">You're ready, Alex.</h2>
              <p className="mt-3 text-muted-foreground">Your 7 agents are spinning up now.</p>
            </div>
          )}

          <div className="flex justify-between mt-8 pt-6 border-t border-border/50">
            <Button variant="ghost" onClick={prev} disabled={step === 0} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button onClick={next} className="bg-gradient-primary shadow-glow gap-2">
              {step === steps.length - 1 ? "Enter dashboard" : "Continue"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
