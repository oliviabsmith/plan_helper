import { ButtonHTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, children, variant = "primary", disabled, loading, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-400",
          variant === "primary" && "bg-primary-500 text-white hover:bg-primary-400",
          variant === "secondary" && "bg-slate-800 text-slate-100 hover:bg-slate-700",
          variant === "ghost" && "bg-transparent text-slate-200 hover:bg-slate-800/60",
          (disabled || loading) && "cursor-not-allowed opacity-60",
          className,
        )}
        disabled={disabled || loading}
        {...rest}
      >
        {loading && (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-transparent" />
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
