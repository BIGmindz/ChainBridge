import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../utils/classNames";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "outline";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  variant?: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "border-slate-600/60 bg-slate-800/80 text-slate-200",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  warning: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  danger: "border-rose-500/40 bg-rose-500/10 text-rose-200",
  info: "border-sky-500/40 bg-sky-500/10 text-sky-200",
  outline: "border-slate-600/50 text-slate-300",
};

export function Badge({ variant = "default", className, children, ...rest }: BadgeProps): JSX.Element {
  return (
    <span
      className={classNames(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        variantClasses[variant],
        className
      )}
      {...rest}
    >
      {children}
    </span>
  );
}
