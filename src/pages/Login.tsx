import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Loader2, Mail, Lock, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useAuthContext, getFirebaseErrorMessage } from "@/lib/auth-context";
import { firebaseConfigError, isFirebaseConfigured } from "@/lib/firebase";
import { apiConfigError } from "@/api/client";

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="currentColor" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="currentColor" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="currentColor" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="currentColor" />
  </svg>
);

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, signInWithGoogle, sendPasswordReset, isLoading } = useAuthContext();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleForgotPassword = async () => {
    if (!email) {
      toast.error("Please enter your email address first.");
      return;
    }
    try {
      await sendPasswordReset(email);
      toast.success("Password reset email sent!");
    } catch (err: unknown) {
      const message = getFirebaseErrorMessage(err);
      toast.error(message);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      navigate("/app");
    } catch (err: unknown) {
      const message = getFirebaseErrorMessage(err);
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError("");
    try {
      await signInWithGoogle();
      toast.success("Welcome back!");
      navigate("/app");
    } catch (err: unknown) {
      const message = getFirebaseErrorMessage(err);
      setError(message);
      toast.error(message);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 overflow-hidden">
      {/* Animated grid background */}
      <div className="absolute inset-0 animated-grid" />
      <div className="absolute inset-0 bg-beams opacity-30" />
      <div className="absolute inset-0 bg-gradient-to-b from-primary/[0.03] via-transparent to-accent/[0.02]" />
      
      {/* Floating orbs */}
      <div className="absolute top-1/4 right-1/3 w-72 h-72 rounded-full bg-gradient-1 opacity-[0.04] blur-3xl animate-float-slow" />
      <div className="absolute bottom-1/3 left-1/4 w-56 h-56 rounded-full bg-gradient-3 opacity-[0.04] blur-3xl animate-float" />

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 mb-8 justify-center group">
          <div className="h-9 w-9 rounded-xl bg-gradient-1 flex items-center justify-center shadow-glow transition-transform duration-300 group-hover:scale-110">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-lg tracking-tight">
            AgentForge Career OS
          </span>
        </Link>

        {/* Auth card */}
        <div className="bento-card rounded-2xl p-8 shadow-elevated">
          <h1 className="font-display text-2xl font-bold text-center mb-1 tracking-tight">
            Welcome back
          </h1>
          <p className="text-sm text-muted-foreground text-center mb-6">
            Sign in to your career OS
          </p>

          {!isFirebaseConfigured && firebaseConfigError && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2 mb-4 border border-destructive/20">{firebaseConfigError}</p>
          )}
          {apiConfigError && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2 mb-4 border border-destructive/20">{apiConfigError}</p>
          )}

          {/* Google sign in */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={isSubmitting || isLoading || !isFirebaseConfigured}
            className="flex items-center justify-center gap-3 w-full rounded-xl border border-border/60 bg-background/40 hover:bg-muted/50 active:scale-[0.98] transition-all duration-200 py-2.5 px-4 text-sm font-medium text-foreground group"
          >
            <GoogleIcon />
            Continue with Google
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-border/60" />
            <span className="text-xs text-muted-foreground uppercase tracking-widest font-medium">or</span>
            <div className="flex-1 h-px bg-border/60" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="email" className="text-sm font-medium">Email</Label>
              <div className="relative mt-1.5">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  className="pl-9"
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-medium">Password</Label>
                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="text-xs text-primary hover:underline font-medium transition-all"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative mt-1.5">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  className="pl-9"
                />
              </div>
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2 border border-destructive/20">{error}</p>
            )}

            <Button
              type="submit"
              className="w-full bg-gradient-1 shadow-glow hover:shadow-glow-lg transition-all duration-300 gap-2"
              disabled={isSubmitting || !isFirebaseConfigured}
            >
              {isSubmitting ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Signing in...</>
              ) : (
                <>
                  Sign in
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground text-center mt-6">
            Don't have an account?{" "}
            <Link to="/register" className="text-primary hover:underline font-medium">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
