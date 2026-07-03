import { useEffect, useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Camera, Loader2, CreditCard, LogOut, Shield, ChevronDown, Trash2 } from "lucide-react";
import { useProfile, useUpdateProfile, useMemory, useCreateMemory } from "@/api/hooks";
import { useAuthContext } from "@/lib/auth-context";
import {
  hasAnalyticsConsent,
  grantAnalyticsConsent,
  revokeAnalyticsConsent,
  clearAllStoredData,
} from "@/lib/firebase";
import { profile as profileApi } from "@/api/client";
import { AGENT_LABELS } from "@/lib/agent-types";

type ProfileFormValues = {
  full_name: string;
  school: string;
  graduation_date: string;
  portfolio_url: string;
  linkedin_url: string;
  github_url: string;
  bio: string;
  career_goal: string;
  salary_min: string;
  salary_max: string;
  target_locations: string;
  role_types: string;
  company_sizes: string;
};

const agentNames = AGENT_LABELS;

export default function Settings() {
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const [agentToggles, setAgentToggles] = useState<Record<string, boolean>>({});
  const [togglesLoaded, setTogglesLoaded] = useState(false);
  const [consentState, setConsentState] = useState(hasAnalyticsConsent());
  const [avatarUploading, setAvatarUploading] = useState(false);
  const queryClient = useQueryClient();
  const { data: memoryData } = useMemory();
  const createMemory = useCreateMemory();
  const { logout } = useAuthContext();
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const apiBase = import.meta.env.VITE_API_URL?.replace("/api/v1", "") || "http://localhost:8000";

  const { register, handleSubmit, reset, formState: { isDirty } } = useForm<ProfileFormValues>({
    defaultValues: {
      full_name: "",
      school: "",
      graduation_date: "",
      portfolio_url: "",
      linkedin_url: "",
      github_url: "",
      bio: "",
      career_goal: "",
      salary_min: "",
      salary_max: "",
      target_locations: "",
      role_types: "",
      company_sizes: "",
    },
  });

  useEffect(() => {
    if (profile) {
      reset({
        full_name: profile.full_name || "",
        school: profile.school || "",
        graduation_date: profile.graduation_date || "",
        portfolio_url: profile.portfolio_url || "",
        linkedin_url: profile.linkedin_url || "",
        github_url: profile.github_url || "",
        bio: profile.bio || "",
        career_goal: profile.career_goal || "",
        salary_min: profile.salary_min?.toString() || "",
        salary_max: profile.salary_max?.toString() || "",
        target_locations: profile.target_locations?.join(", ") || "",
        role_types: profile.role_types?.join(", ") || "",
        company_sizes: profile.company_sizes?.join(", ") || "",
      });
    }
  }, [profile, reset]);

  useEffect(() => {
    if (!togglesLoaded && memoryData?.items) {
      const entry = memoryData.items.find((m) => m.key === "agent_toggles");
      if (entry && entry.value && typeof entry.value === "object") {
        setAgentToggles(entry.value as Record<string, boolean>);
      } else {
        setAgentToggles(Object.fromEntries(agentNames.map((a) => [a, true])));
      }
      setTogglesLoaded(true);
    }
  }, [memoryData, togglesLoaded]);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarUploading(true);
    try {
      await profileApi.uploadAvatar(file);
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Photo updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setAvatarUploading(false);
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  };

  const onSubmit = (data: ProfileFormValues) => {
    updateProfile.mutate(
      {
        full_name: data.full_name || undefined,
        school: data.school || undefined,
        graduation_date: data.graduation_date || undefined,
        portfolio_url: data.portfolio_url || undefined,
        linkedin_url: data.linkedin_url || undefined,
        github_url: data.github_url || undefined,
        bio: data.bio || undefined,
        career_goal: data.career_goal || undefined,
        salary_min: data.salary_min ? Number(data.salary_min) : undefined,
        salary_max: data.salary_max ? Number(data.salary_max) : undefined,
        target_locations: data.target_locations ? data.target_locations.split(",").map((s) => s.trim()).filter(Boolean) : [],
        role_types: data.role_types ? data.role_types.split(",").map((s) => s.trim()).filter(Boolean) : [],
        company_sizes: data.company_sizes ? data.company_sizes.split(",").map((s) => s.trim()).filter(Boolean) : [],
      },
      {
        onSuccess: () => toast.success("Profile updated successfully"),
        onError: () => toast.error("Failed to update profile"),
      }
    );
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="font-display text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your profile, agents, and preferences.</p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="glass">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>            <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="privacy">Privacy</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4 space-y-4">
          <Card className="bento-card p-6 space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 border-2 border-primary/30">
                {profile?.avatar_url ? (
                  <AvatarImage src={`${apiBase}${profile.avatar_url}`} alt="Avatar" />
                ) : null}
                <AvatarFallback className="bg-gradient-1 text-primary-foreground text-lg font-display">
                  {isLoading ? "..." : profile?.full_name ? profile.full_name.split(" ").map((w) => w[0]).filter(Boolean).slice(0, 2).join("").toUpperCase() : "U"}
                </AvatarFallback>
              </Avatar>
              <div>
                <input
                  type="file"
                  ref={avatarInputRef}
                  className="hidden"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  onChange={handleAvatarUpload}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => avatarInputRef.current?.click()}
                  disabled={avatarUploading}
                >
                  {avatarUploading ? (
                    <><Loader2 className="h-3 w-3 mr-1.5 animate-spin" />Uploading</>
                  ) : (
                    <><Camera className="h-3 w-3 mr-1.5" />Upload photo</>
                  )}
                </Button>
              </div>
            </div>
            {isLoading ? (
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ))}
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)}>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2"><Label>Full Name</Label><Input {...register("full_name")} className="mt-1.5" /></div>
                  <div><Label>School</Label><Input {...register("school")} className="mt-1.5" /></div>
                  <div><Label>Graduation Date</Label><Input {...register("graduation_date")} className="mt-1.5" placeholder="e.g., 2026-06-15" /></div>
                  <div><Label>Portfolio URL</Label><Input {...register("portfolio_url")} className="mt-1.5" /></div>
                  <div><Label>LinkedIn</Label><Input {...register("linkedin_url")} className="mt-1.5" /></div>
                  <div><Label>GitHub</Label><Input {...register("github_url")} className="mt-1.5" /></div>
                  <div><Label>Career Goal</Label><Input {...register("career_goal")} className="mt-1.5" /></div>
                  <div><Label>Min Salary</Label><Input {...register("salary_min")} type="number" className="mt-1.5" /></div>
                  <div><Label>Max Salary</Label><Input {...register("salary_max")} type="number" className="mt-1.5" /></div>
                  <div className="col-span-2"><Label>Target Locations (comma-separated)</Label><Input {...register("target_locations")} className="mt-1.5" placeholder="e.g., San Francisco, Remote" /></div>
                  <div><Label>Role Types (comma-separated)</Label><Input {...register("role_types")} className="mt-1.5" placeholder="e.g., Internship, New Grad" /></div>
                  <div><Label>Company Sizes (comma-separated)</Label><Input {...register("company_sizes")} className="mt-1.5" placeholder="e.g., Startup, Mid-size" /></div>
                  <div className="col-span-2"><Label>Bio</Label><Input {...register("bio")} className="mt-1.5" /></div>
                </div>
                <Button
                  type="submit"
                  className="bg-gradient-1 shadow-glow mt-4"
                  disabled={updateProfile.isPending || !isDirty}
                >
                  {updateProfile.isPending ? "Saving..." : "Save changes"}
                </Button>
              </form>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="agents" className="mt-4 space-y-3">
          {agentNames.map((a) => (
            <Card key={a} className="glass-strong p-4 flex items-center gap-4">
              <div className="h-8 w-8 rounded-lg bg-gradient-1/10 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                {a[0]}
              </div>
              <div className="flex-1">
                <div className="font-medium">{a} Agent</div>

              </div>
              <Badge variant="outline" className="bg-success/10 text-success border-success/20">Healthy</Badge>
              <Switch
                checked={agentToggles[a]}
                onCheckedChange={(checked) => {
                const next = { ...agentToggles, [a]: checked };
                setAgentToggles(next);
                createMemory.mutate({ key: "agent_toggles", value: next });
              }}
              />
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="billing" className="mt-4">
          <Card className="bento-card p-6 text-center py-12">
            <CreditCard className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <div className="font-display font-semibold text-lg mb-1">Billing coming soon</div>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Subscription management, usage tracking, and plan upgrades will be available in a future release.
            </p>
          </Card>
        </TabsContent>

        <TabsContent value="privacy" className="mt-4 space-y-4">
          <Card className="bento-card p-6">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 shrink-0 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 space-y-3">
                <div>
                  <h3 className="font-display font-semibold text-lg">Analytics &amp; Privacy</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    We use analytics to understand feature usage and improve AgentForge. Your resumes, job applications, and personal data are never tracked.
                  </p>
                </div>

                <div className="flex items-center justify-between rounded-lg border border-border/50 p-3">
                  <div>
                    <div className="text-sm font-medium">Usage analytics</div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Page views, feature interactions, session duration
                    </p>
                  </div>
                  <Switch
                    checked={hasAnalyticsConsent()}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        grantAnalyticsConsent();
                      } else {
                        revokeAnalyticsConsent();
                      }
                      // Force re-render
                      setConsentState(checked);
                    }}
                  />
                </div>

                <details className="group rounded-lg border border-border/50 p-3">
                  <summary className="text-sm font-medium cursor-pointer list-none flex items-center justify-between">
                    <span>What we collect</span>
                    <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
                  </summary>
                  <div className="mt-2 space-y-2 text-xs text-muted-foreground">
                    <p><strong>Collected:</strong> Page views, feature usage frequency, session duration, error events, browser type (non-identifying).</p>
                    <p><strong>NOT collected:</strong> Resume content, cover letters, job applications, personal contact info, search queries, AI conversation history.</p>
                    <p><strong>Third parties:</strong> Firebase Analytics (Google). Data is anonymized and used only for product improvement.</p>
                    <p className="mt-2">
                      You can request full data deletion at any time by contacting{' '}
                      <a href="mailto:support@agentforge.ai" className="text-primary hover:underline">support@agentforge.ai</a>.
                    </p>
                  </div>
                </details>
              </div>
            </div>
          </Card>

          <Card className="bento-card p-6">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 shrink-0 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center justify-center">
                <Trash2 className="h-5 w-5 text-destructive" />
              </div>
              <div className="flex-1 space-y-2">
                <div>
                  <h3 className="font-display font-semibold">Clear local data</h3>
                  <p className="text-sm text-muted-foreground">
                    Clear all locally stored data including auth tokens and preferences. You will be signed out and need to log in again.
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
                  onClick={() => {
                    clearAllStoredData();
                    logout();
                    toast.success("Local data cleared");
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                  Clear local data
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      <Card className="bento-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-display font-semibold">Account</h3>
            <p className="text-sm text-muted-foreground mt-0.5">Sign out of your account.</p>
          </div>
          <Button variant="outline" className="gap-2 text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={() => logout()}>
            <LogOut className="h-4 w-4" /> Sign out
          </Button>
        </div>
      </Card>
    </div>
  );
}
