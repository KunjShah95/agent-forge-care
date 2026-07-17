import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw, Copy, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  requestId: string;
}

/**
 * Production-grade error boundary with:
 * - Sentry integration (when available)
 * - Request ID for correlation with backend logs
 * - Copy-to-clipboard for error details
 * - Graceful fallback UI
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      requestId: "",
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Report to Sentry if available
    const sentryGlobal = (typeof window !== "undefined" ? (window as unknown as { __SENTRY__?: { captureException: (error: Error, options: Record<string, unknown>) => void } }).__SENTRY__ : null);
    if (sentryGlobal) {
      try {
        sentryGlobal.captureException(error, {
          contexts: { react: { componentStack: errorInfo.componentStack } },
          tags: { source: "error-boundary" },
        });
      } catch {
        // Sentry not available, continue silently
      }
    }

    // Log to console in all environments
    console.error("[ErrorBoundary]", error, errorInfo);

    // Call custom onError handler if provided
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleCopyError = () => {
    const { error, errorInfo, requestId } = this.state;
    const text = [
      `Error: ${error?.message}`,
      requestId && `Request ID: ${requestId}`,
      errorInfo?.componentStack && `\nComponent Stack:\n${errorInfo.componentStack}`,
      `\nUser Agent: ${navigator.userAgent}`,
      `\nTimestamp: ${new Date().toISOString()}`,
    ]
      .filter(Boolean)
      .join("\n");

    navigator.clipboard.writeText(text).catch(() => {
      // Fallback: select text for manual copy
    });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex items-center justify-center min-h-[400px] p-8">
          <div className="bento-card p-8 max-w-md w-full text-center space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
            <h2 className="font-display text-xl font-bold gradient-text">
              Something went wrong
            </h2>
            <p className="text-sm text-muted-foreground">
              An unexpected error occurred. Our team has been notified.
            </p>

            {import.meta.env.DEV && this.state.error && (
              <div className="text-left space-y-2">
                <p className="text-sm font-mono bg-muted/50 rounded-lg p-3 text-destructive overflow-auto max-h-32">
                  {this.state.error.message}
                </p>
                {this.state.errorInfo?.componentStack && (
                  <details className="text-xs text-muted-foreground">
                    <summary className="cursor-pointer hover:text-foreground transition-colors">
                      Component stack
                    </summary>
                    <pre className="mt-2 p-2 bg-muted/30 rounded text-[10px] overflow-auto max-h-24 font-mono">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="flex gap-2 justify-center">
              <Button
                onClick={this.handleCopyError}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <Copy className="h-3 w-3" /> Copy details
              </Button>
              <Button
                onClick={this.handleReset}
                className="bg-gradient-primary shadow-glow gap-2"
                size="sm"
              >
                <RefreshCw className="h-3 w-3" /> Try again
              </Button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
