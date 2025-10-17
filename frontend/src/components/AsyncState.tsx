import { ReactNode } from "react";

interface AsyncStateProps {
  isLoading?: boolean;
  isError?: boolean;
  errorMessage?: string;
  children: ReactNode;
  loading?: ReactNode;
  error?: ReactNode;
}

export function AsyncState({
  isLoading,
  isError,
  errorMessage,
  children,
  loading,
  error,
}: AsyncStateProps) {
  if (isLoading) {
    return (
      loading ?? (
        <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/60 p-6 text-sm text-slate-400">
          Loading…
        </div>
      )
    );
  }

  if (isError) {
    return (
      error ?? (
        <div className="rounded-lg border border-rose-800 bg-rose-900/30 p-6 text-sm text-rose-100">
          {errorMessage ?? "Unable to load data."}
        </div>
      )
    );
  }

  return <>{children}</>;
}
