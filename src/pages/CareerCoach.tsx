import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Lightbulb, Target, TrendingUp, BookOpen, ArrowRight, Sparkles, MessageSquare } from "lucide-react";
import { useCareerGuidance } from "@/api/hooks";
import { toast } from "sonner";

export default function CareerCoach() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<{ guidance: Record<string, unknown>; message: string } | null>(null);
  const careerGuidance = useCareerGuidance();

  const handleGetGuidance = async () => {
    if (!query.trim()) {
      toast.error("Please describe what you need help with");
      return;
    }
    try {
      const res = await careerGuidance.mutateAsync({ query });
      setResult(res);
      toast.success("Career guidance generated");
    } catch {
      toast.error("Failed to generate guidance");
    }
  };

  const g = result?.guidance;
  const profileSummary = g?.profile_summary as Record<string, unknown> | undefined;
  const nextSteps = g?.next_steps as string[] | undefined;
  const tips = g?.tips as string[] | undefined;

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="font-display text-3xl font-bold">Career Coach</h1>
        <p className="text-muted-foreground mt-1">Personalized career guidance powered by AI.</p>
      </div>

      <Card className="glass p-6">
        <div className="flex gap-3">
          <Textarea
            placeholder="Ask for career advice... e.g., 'What skills should I focus on for AI internships?' or 'How can I improve my application strategy?'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="min-h-[80px] flex-1"
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleGetGuidance())}
          />
          <Button
            className="bg-gradient-primary shadow-glow gap-2 self-end"
            onClick={handleGetGuidance}
            disabled={careerGuidance.isPending}
          >
            {careerGuidance.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Get Advice
          </Button>
        </div>
      </Card>

      {careerGuidance.isPending && (
        <Card className="glass p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
          <p className="text-muted-foreground">Analyzing your profile and generating guidance...</p>
        </Card>
      )}

      {result && !careerGuidance.isPending && (
        <div className="space-y-4">
          {profileSummary && (
            <Card className="glass p-5 border-primary/20">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="h-5 w-5 text-primary" />
                <h3 className="font-display font-semibold">Profile Summary</h3>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {Object.entries(profileSummary).map(([key, val]) => (
                  <div key={key} className="p-3 rounded-lg bg-muted/30">
                    <div className="text-xs text-muted-foreground capitalize mb-1">{key.replace(/_/g, " ")}</div>
                    <div className="text-sm font-medium">
                      {Array.isArray(val) ? val.join(", ") : String(val)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {nextSteps && nextSteps.length > 0 && (
            <Card className="glass p-5 border-success/20">
              <div className="flex items-center gap-2 mb-3">
                <Target className="h-5 w-5 text-success" />
                <h3 className="font-display font-semibold">Next Steps</h3>
              </div>
              <div className="space-y-2">
                {nextSteps.map((step, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 text-sm">
                    <span className="h-5 w-5 rounded-full bg-success/10 text-success flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span className="text-muted-foreground">{step}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {tips && tips.length > 0 && (
            <Card className="glass p-5 border-warning/20">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-5 w-5 text-warning" />
                <h3 className="font-display font-semibold">Tips & Recommendations</h3>
              </div>
              <div className="space-y-2">
                {tips.map((tip, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 text-sm">
                    <Lightbulb className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
                    <span className="text-muted-foreground">{tip}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {!result && !careerGuidance.isPending && (
        <div className="text-center py-16">
          <MessageSquare className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
          <h3 className="font-display font-semibold text-lg mb-2">What would you like advice on?</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Ask about career strategy, skill development, application tactics, interview preparation, or anything else.
          </p>
        </div>
      )}
    </div>
  );
}
