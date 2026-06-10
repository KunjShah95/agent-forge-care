import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[400px] p-8">
          <div className="bento-card p-8 max-w-md w-full text-center space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
            <h2 className="font-display text-xl font-bold gradient-text">Something went wrong</h2>
            {import.meta.env.DEV && this.state.error && (
              <p className="text-sm text-muted-foreground font-mono bg-muted/50 rounded-lg p-3 text-left overflow-auto">
                {this.state.error.message}
              </p>
            )}
            <Button onClick={this.handleReset} className="bg-gradient-primary shadow-glow gap-2">
              <RefreshCw className="h-4 w-4" /> Try again
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
