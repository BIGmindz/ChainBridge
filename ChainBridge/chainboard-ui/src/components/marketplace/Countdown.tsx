/**
 * Countdown Timer Component
 *
 * Displays time remaining until auction end with real-time updates
 * Red/pulsing when less than 1 hour remaining
 */

import { Clock } from "lucide-react";
import { memo, useEffect, useState } from "react";

import { classNames } from "../../utils/classNames";

interface CountdownProps {
  endAt: string;          // ISO timestamp of countdown end
  onExpired?: () => void; // Callback when countdown reaches zero
}

/**
 * Format milliseconds into human-readable time remaining
 * Returns "2h 34m", "45m 12s", "3s", etc.
 */
function formatTimeRemaining(ms: number): string {
  if (ms <= 0) return "Ended";

  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
}

export function CountdownComponent({ endAt, onExpired }: CountdownProps) {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    // Calculate initial time remaining
    const calculateTimeRemaining = () => {
      const now = Date.now();
      const endTime = new Date(endAt).getTime();
      const remaining = Math.max(0, endTime - now);

      if (remaining === 0 && !isExpired) {
        setIsExpired(true);
        onExpired?.();
      }

      setTimeRemaining(remaining);
    };

    // Initial calculation
    calculateTimeRemaining();

    // Update every 100ms for smooth countdown
    const interval = setInterval(calculateTimeRemaining, 100);

    return () => clearInterval(interval);
  }, [endAt, isExpired, onExpired]);

  const isUrgent = timeRemaining < 3600000; // Less than 1 hour
  const isVeryUrgent = timeRemaining < 300000; // Less than 5 minutes

  return (
    <div className={classNames(
      "flex items-center gap-2 text-sm font-mono",
      isVeryUrgent
        ? "text-red-300 animate-pulse"
        : isUrgent
        ? "text-amber-300"
        : "text-cyan-300"
    )}>
      <Clock className={classNames(
        "w-4 h-4",
        isVeryUrgent ? "animate-spin" : ""
      )} />
      <span className="font-bold">
        {formatTimeRemaining(timeRemaining)}
      </span>
    </div>
  );
}

export const Countdown = memo(CountdownComponent);
