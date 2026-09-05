"use client";

import { useCallback, useEffect, useRef } from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/**
 * Built on the native `<dialog>` element, which gives focus trapping, Escape
 * handling and inert background content without any extra JavaScript.
 */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const handleCancel = useCallback(
    (event: React.SyntheticEvent) => {
      // Escape fires `cancel`; close through React so state stays in sync.
      event.preventDefault();
      onClose();
    },
    [onClose],
  );

  return (
    <dialog
      ref={ref}
      onCancel={handleCancel}
      onClose={onClose}
      onClick={(event) => {
        // A click on the backdrop lands on the dialog element itself.
        if (event.target === ref.current) onClose();
      }}
      className={cn(
        "border-border-base bg-surface-raised text-text m-auto w-[min(32rem,calc(100vw-2rem))] rounded-lg border p-0",
        "backdrop:bg-black/40 open:animate-none",
        className,
      )}
    >
      <div className="border-border-base flex items-start justify-between gap-4 border-b px-5 py-3.5">
        <div>
          <h2 className="text-text text-sm font-semibold">{title}</h2>
          {description && <p className="text-text-muted mt-1 text-sm">{description}</p>}
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close dialog">
          <X aria-hidden className="h-4 w-4" />
        </Button>
      </div>
      {children && <div className="px-5 py-4">{children}</div>}
      {footer && (
        <div className="border-border-base flex justify-end gap-2 border-t px-5 py-3.5">
          {footer}
        </div>
      )}
    </dialog>
  );
}

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  destructive?: boolean;
  loading?: boolean;
}

/** A dialog for actions that cannot be undone. */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  destructive = false,
  loading = false,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <>
          <Button onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant={destructive ? "danger" : "primary"}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    />
  );
}
