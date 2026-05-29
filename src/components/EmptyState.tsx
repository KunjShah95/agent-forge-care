export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: React.ElementType;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      {Icon && <Icon className="h-12 w-12 text-muted-foreground/30 mb-4" />}
      <h3 className="font-display text-lg font-semibold text-foreground/80">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1 max-w-md">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message = "Something went wrong",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      <div className="h-12 w-12 rounded-2xl bg-destructive/10 border border-destructive/20 flex items-center justify-center mb-4">
        <svg className="h-6 w-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      </div>
      <h3 className="font-display text-lg font-semibold">Error</h3>
      <p className="text-sm text-muted-foreground mt-1 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 text-sm text-primary hover:underline font-medium"
        >
          Try again
        </button>
      )}
    </div>
  );
}
