import { useEffect, useState } from "react";
import { clsx } from "clsx";
import toast from "react-hot-toast";

interface SubtaskIdChipProps {
  value: string;
  className?: string;
  "data-testid"?: string;
}

function formatValue(value: string) {
  if (value.length <= 12) {
    return value;
  }
  const start = value.slice(0, 4);
  const end = value.slice(-4);
  return `${start}…${end}`;
}

export function SubtaskIdChip({ value, className, ...rest }: SubtaskIdChipProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timeout = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timeout);
  }, [copied]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success("Subtask ID copied to clipboard");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to copy subtask ID";
      toast.error(message);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={clsx(
        "group inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1",
        "text-xs font-medium text-slate-200 transition hover:border-primary-400 hover:bg-slate-800",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-400",
        className,
      )}
      title={`${value} — click to copy`}
      {...rest}
    >
      <span className="font-mono text-[11px] tracking-tight text-primary-200">{formatValue(value)}</span>
      <span
        className={clsx(
          "text-[10px] uppercase tracking-wide",
          copied ? "text-primary-300" : "text-slate-500 group-hover:text-slate-300",
        )}
      >
        {copied ? "Copied" : "Copy"}
      </span>
    </button>
  );
}

export default SubtaskIdChip;
