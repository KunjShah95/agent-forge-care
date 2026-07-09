import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sparkles, ArrowRight, ArrowLeft, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { useUpdateProfile, useUploadResume, useAgentTasks, useEnrichProfile } from "@/api/hooks";

const steps = ["Welcome", "About You", "Skills", "Preferences", "Goals", "Launch"];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [skills, setSkills] = useState<string[]>(["TypeScript", "React", "Python"]);
  const [skillInput, setSkillInput] = useState("");
  const [fullName, setFullName] = useState("");
  const [school, setSchool] = useState("");
  const [graduation, setGraduation] = useState("");
  const [bio, setBio] = useState("");
  const [locations, setLocations] = useState("");
  const [salary, setSalary] = useState("");
  const [roleTypes, setRoleTypes] = useState("");
  const [companySizes, setCompanySizes] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [github, setGithub] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const uploadResume = useUploadResume();
  const { data: tasksData } = useAgentTasks();
  const enrichProfile = useEnrichProfile();
  const [enrichProgress, setEnrichProgress] = useState<string>("");
  const [enrichResult, setEnrichResult] = useState<{
    social_links?: Record<string, string | null>;
    discovered_skills?: string[];
    github_analysis?: Record<string, unknown>;
    portfolio_data?: Record<string, unknown>;
  } | null>(null);
  const [enrichError, setEnrichError] = useState<string | null>(null);

  const runningTasks = tasksData?.items?.filter((t) => t.status === "running" || t.status === "queued") || [];
  const [careerGoal, setCareerGoal] = useState("");
  const navigate = useNavigate();
  const updateProfile = useUpdateProfile();

  const handleComplete = () => {
    // Step 1: Run enrichment (scrape GitHub/portfolio/LinkedIn)
    if (github || portfolio || linkedin) {
      setEnrichProgress("Scanning your GitHub, portfolio, and social profiles...");
      enrichProfile.mutate(
        {
          github_url: github || undefined,
          portfolio_url: portfolio || undefined,
          linkedin_url: linkedin || undefined,
        },
        {
          onSuccess: (result) => {
            setEnrichProgress("Profiles scanned! Preparing your dashboard...");
            setEnrichResult(result);

            // Merge discovered skills with user-added skills
            const discovered = result.discovered_skills || [];
            const mergedSkills = [...new Set([...skills, ...discovered])];

            finishOnboarding(mergedSkills);
          },
          onError: (err: Error) => {
            setEnrichError(err.message || "Profile enrichment failed. You can retry later.");
            setEnrichProgress("");
            // Still finish onboarding even if enrichment fails
            finishOnboarding(skills);
          },
        }
      );
    } else {
      finishOnboarding(skills);
    }
  };

  const finishOnboarding = (finalSkills: string[]) => {
    const finish = (resumeUploaded = false) => {
      const parseSalary = (s: string) => {
        const clean = s.replace(/[$,\s]/g, "").toLowerCase();
        const range = clean.match(/^(\d+)(?:k)?\s*[-–to]+\s*(\d+)(?:k)?$/);
        if (range) {
          const mult = clean.includes("k") || range[1].length <= 3 ? 1000 : 1;
          return { min: parseInt(range[1]) * mult, max: parseInt(range[2]) * mult };
        }
        const single = clean.match(/^(\d+)(?:k)?$/);
        if (single) {
          const val = parseInt(single[1]) * (clean.includes("k") || single[1].length <= 3 ? 1000 : 1);
          return { min: val, max: val };
        }
        return null;
      };
      const parsed = salary ? parseSalary(salary) : null;
      updateProfile.mutate(
        {
          full_name: fullName || undefined,
          school: school || undefined,
          graduation_date: graduation || undefined,
          bio: bio || undefined,
          portfolio_url: portfolio || undefined,
          github_url: github || undefined,
          linkedin_url: linkedin || undefined,
          salary_min: parsed?.min,
          salary_max: parsed?.max,
          target_locations: locations ? locations.split(",").map((s) => s.trim()).filter(Boolean) : [],
          role_types: roleTypes ? roleTypes.split(",").map((s) => s.trim()).filter(Boolean) : [],
          company_sizes: companySizes ? companySizes.split(",").map((s) => s.trim()).filter(Boolean) : [],
          career_goal: careerGoal || undefined,
          is_onboarded: true,
          skills: finalSkills.map((s) => ({ name: s, proficiency: "intermediate" })),
        },
        {
          onSuccess: () => {
            toast.success("Profile saved!");
            navigate("/app");
          },
          onError: () => toast.error("Failed to save profile. Please try again."),
        },
      );
    };

    if (resumeFile) {
      uploadResume.mutate(resumeFile, {
        onSuccess: () => {
          toast.success("Resume uploaded successfully");
          finish(true);
        },
        onError: () => {
          toast.error("Failed to upload resume. Please try again.");
          finish(false);
        },
      });
    } else {
      finish(false);
    }
  };

  const next = () => {
    if (step < steps.length - 1) {
      setStep((s) => s + 1);
    } else {
      handleComplete();
    }
  };
  const prev = () => setStep((s) => Math.max(0, s - 1));
  const addSkill = () => { if (skillInput.trim()) { setSkills([...skills, skillInput.trim()]); setSkillInput(""); } };

  return (
    <div className="min-h-screen mesh-bg flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <div className="h-9 w-9 rounded-xl bg-gradient-1 flex items-center justify-center shadow-glow">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-lg">AgentForge Career OS</span>
        </div>

        <div className="bento-card p-8">
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
                <div><Label>Full name</Label><Input value={fullName} onChange={(e) => setFullName(e.target.value)} className="mt-1.5" /></div>
                <div><Label>School</Label><Input value={school} onChange={(e) => setSchool(e.target.value)} className="mt-1.5" /></div>
                <div><Label>Graduation</Label><Input value={graduation} onChange={(e) => setGraduation(e.target.value)} className="mt-1.5" placeholder="e.g., 2026-06-15" /></div>
              </div>
              <div><Label>Bio / pitch</Label><Textarea className="mt-1.5" value={bio} onChange={(e) => setBio(e.target.value)} /></div>
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
                <div><Label>Preferred locations</Label><Input value={locations} onChange={(e) => setLocations(e.target.value)} className="mt-1.5" /></div>
                <div><Label>Salary expectation</Label><Input value={salary} onChange={(e) => setSalary(e.target.value)} className="mt-1.5" /></div>
                <div><Label>Role types</Label><Input value={roleTypes} onChange={(e) => setRoleTypes(e.target.value)} className="mt-1.5" /></div>
                <div><Label>Company size</Label><Input value={companySizes} onChange={(e) => setCompanySizes(e.target.value)} className="mt-1.5" /></div>
              </div>
              <div><Label>Portfolio link</Label><Input value={portfolio} onChange={(e) => setPortfolio(e.target.value)} className="mt-1.5" placeholder="https://your-portfolio.com" /></div>
              <div><Label>GitHub profile</Label><Input value={github} onChange={(e) => setGithub(e.target.value)} className="mt-1.5" placeholder="https://github.com/your-username" /></div>
              <div><Label>LinkedIn profile</Label><Input value={linkedin} onChange={(e) => setLinkedin(e.target.value)} className="mt-1.5" placeholder="https://linkedin.com/in/your-profile" /></div>
              <div>
                <Label>Upload resume (PDF)</Label>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setResumeFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
                  className="mt-1.5"
                />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4 animate-fade-in">
              <h2 className="font-display text-2xl font-bold">Your career goal</h2>
              <p className="text-sm text-muted-foreground">Your Planner Agent uses this to prioritize work.</p>
              <Textarea
                rows={5}
                value={careerGoal}
                onChange={(e) => setCareerGoal(e.target.value)}
                className="mt-1.5"
              />
            </div>
          )}

          {step === 5 && (
            <div className="text-center py-4 animate-fade-in">
              <div className="h-16 w-16 rounded-2xl bg-gradient-1 mx-auto flex items-center justify-center shadow-glow animate-pulse-glow">
                <Sparkles className="h-8 w-8 text-primary-foreground" />
              </div>
              <h2 className="font-display text-3xl font-bold mt-6">You're ready{fullName ? `, ${fullName}` : ""}.</h2>
              <p className="mt-3 text-muted-foreground">Your agents are spinning up now.</p>

              {/* Enrichment progress */}
              {(github || portfolio || linkedin) && !enrichResult && !enrichError && (
                <div className="mt-4 space-y-2">
                  <p className="text-sm text-muted-foreground animate-pulse">
                    {enrichProgress || "Scanning your profiles for skills and opportunities..."}
                  </p>
                  <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-1 animate-progress" style={{ width: "60%" }} />
                  </div>
                </div>
              )}

              {enrichError && (
                <div className="mt-4 px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
                  {enrichError}
                </div>
              )}

              {enrichResult && (
                <div className="mt-4 space-y-3 text-left">
                  {/* Discovered social links */}
                  {enrichResult.social_links && Object.values(enrichResult.social_links).some(Boolean) && (
                    <div className="rounded-lg bg-primary/[0.03] border border-primary/10 p-3">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Discovered Links</p>
                      <div className="space-y-1">
                        {enrichResult.social_links.blog_url && (
                          <p className="text-xs text-primary truncate">📝 Blog: {enrichResult.social_links.blog_url}</p>
                        )}
                        {enrichResult.social_links.twitter_handle && (
                          <p className="text-xs text-primary">🐦 Twitter: @{enrichResult.social_links.twitter_handle}</p>
                        )}
                        {enrichResult.social_links.portfolio_url && (
                          <p className="text-xs text-primary truncate">🌐 Portfolio: {enrichResult.social_links.portfolio_url}</p>
                        )}
                        {enrichResult.social_links.linkedin_url && (
                          <p className="text-xs text-primary truncate">💼 LinkedIn: {enrichResult.social_links.linkedin_url}</p>
                        )}
                        {enrichResult.social_links.location && (
                          <p className="text-xs text-muted-foreground">📍 Location: {enrichResult.social_links.location}</p>
                        )}
                        {enrichResult.social_links.company && (
                          <p className="text-xs text-muted-foreground">🏢 Company: {enrichResult.social_links.company}</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Discovered skills */}
                  {enrichResult.discovered_skills && enrichResult.discovered_skills.length > 0 && (
                    <div className="rounded-lg bg-primary/[0.03] border border-primary/10 p-3">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Skills Detected</p>
                      <div className="flex flex-wrap gap-1.5">
                        {enrichResult.discovered_skills.slice(0, 12).map((s) => (
                          <span key={s} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                            {s}
                          </span>
                        ))}
                        {enrichResult.discovered_skills.length > 12 && (
                          <span className="text-xs text-muted-foreground">+{enrichResult.discovered_skills.length - 12} more</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* GitHub analysis summary */}
                  {enrichResult.github_analysis?.summary && (
                    <div className="rounded-lg bg-primary/[0.03] border border-primary/10 p-3">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">GitHub Summary</p>
                      <p className="text-xs text-muted-foreground">{enrichResult.github_analysis.summary as string}</p>
                    </div>
                  )}

                  {/* Agent tasks status */}
                  <div className="mt-4">
                    {runningTasks.length > 0 ? (
                      <div className="text-sm text-muted-foreground">🤖 Agent tasks running: {runningTasks.length}</div>
                    ) : (
                      <div className="text-sm text-muted-foreground">🤖 Agents ready and waiting for your command.</div>
                    )}
                  </div>
                </div>
              )}

              {!github && !portfolio && !linkedin && (
                <div className="mt-4 text-sm text-muted-foreground">
                  You can always connect your GitHub, portfolio, and LinkedIn later in Settings.
                </div>
              )}
            </div>
          )}

          <div className="flex justify-between mt-8 pt-6 border-t border-border/50">
            <Button variant="ghost" onClick={prev} disabled={step === 0} className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <Button onClick={next} className="bg-gradient-1 shadow-glow gap-2" disabled={step === steps.length - 1 && updateProfile.isPending}>
              {step === steps.length - 1 ? (updateProfile.isPending ? "Saving…" : "Enter dashboard") : "Continue"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
