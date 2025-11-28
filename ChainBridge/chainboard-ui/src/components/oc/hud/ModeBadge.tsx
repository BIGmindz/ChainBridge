/**
 * ModeBadge - Transport mode indicator with icon for The OC
 * Maps canonical TransportMode enum to icons and styling
 */

import { Package, Plane, Ship, Train, Truck } from "lucide-react";

import { TransportMode } from "../../../types/chainbridge";
import { classNames } from "../../../utils/classNames";

export interface ModeBadgeProps {
  mode: TransportMode;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

const modeConfig = {
  TRUCK_FTL: {
    icon: Truck,
    label: "Truck FTL",
    color: "text-blue-400",
  },
  TRUCK_LTL: {
    icon: Truck,
    label: "Truck LTL",
    color: "text-blue-300",
  },
  OCEAN: {
    icon: Ship,
    label: "Ocean",
    color: "text-cyan-400",
  },
  AIR: {
    icon: Plane,
    label: "Air",
    color: "text-purple-400",
  },
  RAIL: {
    icon: Train,
    label: "Rail",
    color: "text-green-400",
  },
  INTERMODAL: {
    icon: Package,
    label: "Intermodal",
    color: "text-amber-400",
  },
} as const;

const sizeConfig = {
  sm: {
    icon: "h-3 w-3",
    text: "text-xs",
    gap: "gap-1",
  },
  md: {
    icon: "h-4 w-4",
    text: "text-sm",
    gap: "gap-1.5",
  },
  lg: {
    icon: "h-5 w-5",
    text: "text-base",
    gap: "gap-2",
  },
} as const;

export function ModeBadge({
  mode,
  size = "md",
  showLabel = false,
  className
}: ModeBadgeProps): JSX.Element {
  const config = modeConfig[mode];
  const sizeStyle = sizeConfig[size];
  const Icon = config.icon;

  return (
    <div
      className={classNames(
        "inline-flex items-center",
        sizeStyle.gap,
        className
      )}
    >
      <Icon
        className={classNames(
          sizeStyle.icon,
          config.color
        )}
      />
      {showLabel && (
        <span className={classNames(sizeStyle.text, "text-slate-300")}>
          {config.label}
        </span>
      )}
    </div>
  );
}
