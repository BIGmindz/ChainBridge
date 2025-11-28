/**
 * Toast Container
 *
 * Renders active notifications in a fixed bottom-right stack.
 * Auto-dismisses after configured duration.
 */

import { useNotifications } from "../core/notifications/NotificationContext";
import type { Notification } from "../core/notifications/NotificationContext";

export function ToastContainer() {
  const { notifications, dismiss } = useNotifications();

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="false"
    >
      {notifications.map((notification) => (
        <Toast key={notification.id} notification={notification} onDismiss={dismiss} />
      ))}
    </div>
  );
}

interface ToastProps {
  notification: Notification;
  onDismiss: (id: string) => void;
}

function Toast({ notification, onDismiss }: ToastProps) {
  const { id, type, message } = notification;

  const bgColor = {
    success: "bg-green-600",
    error: "bg-red-600",
    info: "bg-blue-600",
  }[type];

  const icon = {
    success: "✓",
    error: "✕",
    info: "ℹ",
  }[type];

  return (
    <div
      className={`${bgColor} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 min-w-[320px] max-w-md pointer-events-auto animate-slide-in`}
      role="alert"
    >
      <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-white bg-opacity-20 rounded-full font-bold">
        {icon}
      </div>
      <div className="flex-1 text-sm font-medium">{message}</div>
      <button
        onClick={() => onDismiss(id)}
        className="flex-shrink-0 text-white hover:text-gray-200 transition-colors"
        aria-label="Dismiss notification"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}
