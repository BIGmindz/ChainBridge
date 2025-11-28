/**
 * Notification Context
 *
 * Global notification system for non-blocking user feedback.
 * Supports success, error, and info toast messages.
 */

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export type NotificationType = "success" | "error" | "info";

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  duration?: number; // milliseconds until auto-dismiss
}

interface NotificationContextValue {
  notifications: Notification[];
  notifySuccess: (message: string, duration?: number) => void;
  notifyError: (message: string, duration?: number) => void;
  notifyInfo: (message: string, duration?: number) => void;
  dismiss: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextValue | undefined>(undefined);

interface NotificationProviderProps {
  children: ReactNode;
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((type: NotificationType, message: string, duration = 5000) => {
    const id = `notification-${Date.now()}-${Math.random()}`;
    const notification: Notification = { id, type, message, duration };

    setNotifications((prev) => [...prev, notification]);

    // Auto-dismiss after duration
    if (duration > 0) {
      setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const notifySuccess = useCallback(
    (message: string, duration?: number) => addNotification("success", message, duration),
    [addNotification],
  );

  const notifyError = useCallback(
    (message: string, duration?: number) => addNotification("error", message, duration),
    [addNotification],
  );

  const notifyInfo = useCallback(
    (message: string, duration?: number) => addNotification("info", message, duration),
    [addNotification],
  );

  const dismiss = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const value: NotificationContextValue = {
    notifications,
    notifySuccess,
    notifyError,
    notifyInfo,
    dismiss,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

/**
 * Hook to access notification system.
 * Must be used within NotificationProvider.
 */
export function useNotifications(): NotificationContextValue {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}
