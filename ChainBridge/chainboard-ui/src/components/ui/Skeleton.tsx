import type { HTMLAttributes } from "react";

import { classNames } from "../../utils/classNames";

type SkeletonProps = HTMLAttributes<HTMLDivElement>;

export function Skeleton({ className, ...rest }: SkeletonProps): JSX.Element {
  return (
    <div
      className={classNames("animate-pulse rounded-md bg-slate-800/60", className)}
      {...rest}
    />
  );
}
