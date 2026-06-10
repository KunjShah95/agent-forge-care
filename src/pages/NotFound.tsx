import { useLocation } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen items-center justify-center mesh-bg p-4">
      <div className="text-center">
        <div className="text-center glass-strong p-10 rounded-2xl max-w-md">
            <div className="h-16 w-16 rounded-2xl bg-gradient-1 flex items-center justify-center mx-auto mb-6 shadow-glow">
              <span className="text-2xl font-bold text-primary-foreground">!</span>
            </div>
            <h1 className="text-6xl font-display font-bold gradient-text-1 mb-2">404</h1>
            <p className="text-muted-foreground mb-6">Page not found</p>
            <a href="/" className="inline-flex items-center gap-2 bg-gradient-1 text-primary-foreground px-5 py-2.5 rounded-xl font-medium hover:shadow-glow-lg transition-all duration-300">
              Return to Home
            </a>
          </div>
      </div>
    </div>
  );
};

export default NotFound;
