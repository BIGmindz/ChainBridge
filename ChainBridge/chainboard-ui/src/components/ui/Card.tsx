import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../utils/classNames";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function Card({ className, children, ...rest }: CardProps): JSX.Element {
  return (
    <div
      className={classNames(
        "rounded-xl border border-slate-800/70 bg-slate-950/50 shadow-lg shadow-black/30",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

interface CardSectionProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function CardHeader({ className, children, ...rest }: CardSectionProps): JSX.Element {
  return (
    <div className={classNames("px-4 py-3", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardContent({ className, children, ...rest }: CardSectionProps): JSX.Element {
  return (
    <div className={classNames("px-4 py-4", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...rest }: CardSectionProps): JSX.Element {
  return (
    <div className={classNames("px-4 py-3 border-t border-slate-800/50", className)} {...rest}>
      {children}
    </div>
  );
}

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  children: ReactNode;
}

export function CardTitle({ className, children, ...rest }: CardTitleProps): JSX.Element {
  return (
    <h3
      className={classNames("text-sm font-semibold uppercase tracking-wider text-slate-300", className)}
      {...rest}
    >
      {children}
    </h3>
  );
}

interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {
  children: ReactNode;
}

export function CardDescription({ className, children, ...rest }: CardDescriptionProps): JSX.Element {
  return (
    <p className={classNames("text-xs text-slate-500", className)} {...rest}>
      {children}
    </p>
  );
}
