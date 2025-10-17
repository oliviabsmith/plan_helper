import { forwardRef, InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import { clsx } from "clsx";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export const TextInput = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, className, ...rest }, ref) => {
    return (
      <label className="flex w-full flex-col gap-1 text-sm">
        {label && <span className="text-slate-300">{label}</span>}
        <input
          ref={ref}
          className={clsx(
            "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-500",
            "focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400",
            error && "border-red-400 focus:border-red-400 focus:ring-red-400",
            className,
          )}
          {...rest}
        />
        {(hint || error) && (
          <span className={clsx("text-xs", error ? "text-red-300" : "text-slate-400")}>{error ?? hint}</span>
        )}
      </label>
    );
  },
);

TextInput.displayName = "TextInput";

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ label, hint, error, className, ...rest }, ref) => {
    return (
      <label className="flex w-full flex-col gap-1 text-sm">
        {label && <span className="text-slate-300">{label}</span>}
        <textarea
          ref={ref}
          className={clsx(
            "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-500",
            "focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400",
            error && "border-red-400 focus:border-red-400 focus:ring-red-400",
            className,
          )}
          {...rest}
        />
        {(hint || error) && (
          <span className={clsx("text-xs", error ? "text-red-300" : "text-slate-400")}>{error ?? hint}</span>
        )}
      </label>
    );
  },
);

TextArea.displayName = "TextArea";
