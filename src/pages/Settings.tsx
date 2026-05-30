import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useProfile, useUpdateProfile, useMemory, useCreateMemory } from "@/api/hooks";

type ProfileFormValues = {
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

const agentNames = ["Planner", "Internship", "Job", "Research", "Resume", "Interview", "Networking", "Opportunity Monitor"];

export default function Settings() {
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const [agentToggles, setAgentToggles] = useState<Record<string, boolean>>(
    Object.fromEntries(agentNames.map((a) => [a, true]))
  );
  const queryClient = useQueryClient();
  const { data: memoryData } = useMemory();
  const createMemory = useCreateMemory();

  const { register, handleSubmit, reset, formState: { isDirty } } = useForm<ProfileFormValues>({
    defaultValues: {
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
    if (memoryData?.items) {
      const entry = memoryData.items.find((m) => m.key === "agent_toggles");
      if (entry && entry.value && typeof entry.value === "object") {
        setAgentToggles(entry.value as Record<string, boolean>);
      }
    }
  }, [memoryData]);

  const onSubmit = (data: ProfileFormValues) => {
    updateProfile.mutate(
      {
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
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4 space-y-4">
          <Card className="glass p-6 space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 border-2 border-primary/30">
                <AvatarFallback className="bg-gradient-primary text-primary-foreground text-lg font-display">
                  {isLoading ? "..." : "U"}
                </AvatarFallback>
              </Avatar>
              <Button variant="outline" size="sm">Upload photo</Button>
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
                  <div><Label>School</Label><Input {...register("school")} className="mt-1.5" /></div>
                  <div><Label>Graduation Date</Label><Input {...register("graduation_date")} className="mt-1.5" placeholder="e.g., June 2026" /></div>
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
                  className="bg-gradient-primary shadow-glow mt-4"
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
            <Card key={a} className="glass p-4 flex items-center gap-4">
              <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                {a[0]}
              </div>
              <div className="flex-1">
                <div className="font-medium">{a} Agent</div>
                <div className="text-xs text-muted-foreground">Active · Last run 12 min ago</div>
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
          <Card className="glass p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="font-display font-semibold text-lg">Pro Plan</div>
                <div className="text-xs text-muted-foreground">$19/mo · Renews Jan 14</div>
              </div>
              <Badge className="bg-gradient-primary border-0 text-primary-foreground">Active</Badge>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Agent runs this month</span><span>1,247</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">AI tokens used</span><span>2.4M / 5M</span></div>
            </div>
            <Button variant="outline" className="w-full mt-4">Manage subscription</Button>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
