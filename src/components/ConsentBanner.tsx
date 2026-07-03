import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Cookie, X, Shield, Info } from "lucide-react";
import {
  hasAnalyticsConsent,
  grantAnalyticsConsent,
  revokeAnalyticsConsent,
} from "@/lib/firebase";

export function ConsentBanner() {
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    // Show the banner only if consent has not yet been granted or denied
    const consentGiven = localStorage.getItem("analytics_consent_granted");
    const consentDeclined = localStorage.getItem("analytics_consent_declined");
    if (consentGiven === null && consentDeclined === null) {
      // Small delay so it doesn't pop up immediately on page load
      const timer = setTimeout(() => setVisible(true), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    grantAnalyticsConsent();
    localStorage.removeItem("analytics_consent_declined");
    setVisible(false);
  };

  const handleDecline = () => {
    revokeAnalyticsConsent();
    localStorage.setItem("analytics_consent_declined", "true");
    localStorage.removeItem("analytics_consent_granted");
    setVisible(false);
  };

  const handleDismiss = () => {
    // Dismiss without persisting choice — ask again next session
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[100] p-3 md:p-4">
      <div className="mx-auto max-w-3xl">
        <div className="relative rounded-xl border border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl p-4 md:p-5">
          {/* Close button */}
          <button
            onClick={handleDismiss}
            className="absolute right-3 top-3 rounded-full p-1 text-muted-foreground/60 hover:text-muted-foreground hover:bg-muted/50 transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>

          <div className="flex items-start gap-3">
            <div className="hidden sm:flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
              <Cookie className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0 space-y-2">
              <p className="text-sm font-semibold text-foreground pr-6">
                Your privacy matters
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                We use analytics cookies to understand how you use AgentForge and improve the experience.
                We never sell your data. You can change your preference anytime in Settings.
                {expanded && (
                  <span className="block mt-2 text-muted-foreground/80">
                    <strong>What we collect:</strong> Page views, feature usage, and session duration.
                    No personal data, resumes, or job applications are tracked.
                  </span>
                )}
              </p>
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-primary/80 hover:text-primary transition-colors"
              >
                <Info className="h-3 w-3" />
                {expanded ? "Show less" : "Learn more about what we collect"}
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 justify-end border-t border-border/40 pt-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDecline}
              className="text-xs h-8 px-3 text-muted-foreground hover:text-foreground"
            >
              Decline
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDismiss}
              className="text-xs h-8 px-3"
            >
              Ask later
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleAccept}
              className="text-xs h-8 px-4 bg-primary hover:bg-primary/90 shadow-sm"
            >
              Accept analytics
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
