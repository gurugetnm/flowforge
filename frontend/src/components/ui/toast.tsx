"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

import { cn } from "@/lib/cn";

type ToastTone = "success" | "error" | "info";

interface Toast {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastContextValue {
  notify: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DISMISS_AFTER_MS = 5000;

const TONE_STYLES: Record<ToastTone, string> = {
  success: "border-success/30 bg-success-soft text-success",
  error: "border-danger/30 bg-danger-soft text-danger",
  info: "border-border-base bg-surface-raised text-text",
};

const TONE_ICONS = { success: CheckCircle2, error: AlertCircle, info: Info } as const;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, tone: ToastTone = "info") => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current, { id, tone, message }]);
      // Errors stay until dismissed; they usually need to be read carefully.
      if (tone !== "error") {
        window.setTimeout(() => dismiss(id), DISMISS_AFTER_MS);
      }
    },
    [dismiss],
  );

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
      >
        {toasts.map((toast) => {
          const Icon = TONE_ICONS[toast.tone];
          return (
            <div
              key={toast.id}
              role={toast.tone === "error" ? "alert" : "status"}
              className={cn(
                "pointer-events-auto flex items-start gap-2 rounded-md border px-3 py-2.5 text-sm shadow-sm",
                TONE_STYLES[toast.tone],
              )}
            >
              <Icon aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
              <p className="text-text flex-1 break-words">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss notification"
                className="text-text-muted hover:text-text rounded p-0.5 transition-colors"
              >
                <X aria-hidden className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside a ToastProvider");
  return context;
}
