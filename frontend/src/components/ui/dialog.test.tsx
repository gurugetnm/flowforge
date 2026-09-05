import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "@/components/ui/dialog";

beforeAll(() => {
  // jsdom does not implement the native modal dialog methods.
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function close() {
    this.open = false;
  };
});

describe("ConfirmDialog", () => {
  function renderDialog(open = true) {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    render(
      <ConfirmDialog
        open={open}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Delete workflow"
        description="This cannot be undone."
        confirmLabel="Delete workflow"
        destructive
      />,
    );
    return { onConfirm, onClose };
  }

  it("states what will happen", () => {
    renderDialog();

    expect(screen.getByRole("heading", { name: "Delete workflow" })).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
  });

  it("confirms only when the confirm button is pressed", async () => {
    const user = userEvent.setup();
    const { onConfirm, onClose } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledOnce();

    await user.click(screen.getByRole("button", { name: "Delete workflow" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
