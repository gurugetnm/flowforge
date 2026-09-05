"use client";

import { useEffect } from "react";

interface Shortcuts {
  onSave: () => void;
  onRun: () => void;
  onDelete: () => void;
}

/** True when the event came from somewhere the user is typing. */
function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
    target.closest("dialog") !== null
  );
}

/**
 * Editor keyboard shortcuts. Nothing fires while the user is typing, so
 * pressing Delete inside a text field never removes a node.
 */
export function useEditorShortcuts({ onSave, onRun, onDelete }: Shortcuts) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (isTyping(event.target)) return;

      const modifier = event.metaKey || event.ctrlKey;

      if (modifier && event.key.toLowerCase() === "s") {
        event.preventDefault();
        onSave();
        return;
      }
      if (modifier && event.key === "Enter") {
        event.preventDefault();
        onRun();
        return;
      }
      if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        onDelete();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onSave, onRun, onDelete]);
}
