import { clsx } from "clsx";

interface StatusBadgeProps {
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  todo: "bg-slate-800 text-slate-200",
  in_progress: "bg-amber-500/20 text-amber-200",
  done: "bg-emerald-500/20 text-emerald-200",
  blocked: "bg-rose-500/20 text-rose-200",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const key = status.toLowerCase();
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide",
        STATUS_COLORS[key] ?? "bg-slate-700 text-slate-200",
      )}
    >
      {label}
    </span>
  );
}
