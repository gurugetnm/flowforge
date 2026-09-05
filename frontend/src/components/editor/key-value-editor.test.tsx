import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { KeyValueEditor } from "@/components/editor/key-value-editor";

describe("KeyValueEditor", () => {
  it("renders a row per entry", () => {
    render(
      <KeyValueEditor
        label="Headers"
        value={{ Authorization: "Bearer x", Accept: "application/json" }}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Headers name 1")).toHaveValue("Authorization");
    expect(screen.getByLabelText("Headers value 2")).toHaveValue("application/json");
  });

  it("adds an empty row", async () => {
    const user = userEvent.setup();
    render(<KeyValueEditor label="Headers" value={{}} onChange={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /add headers/i }));

    expect(screen.getByLabelText("Headers name 1")).toBeInTheDocument();
  });

  it("reports an edited value", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<KeyValueEditor label="Headers" value={{ Accept: "" }} onChange={onChange} />);

    await user.type(screen.getByLabelText("Headers value 1"), "j");

    expect(onChange).toHaveBeenCalledWith({ Accept: "j" });
  });

  it("removes a row", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <KeyValueEditor label="Headers" value={{ Accept: "json", Other: "x" }} onChange={onChange} />,
    );

    await user.click(screen.getByRole("button", { name: /remove Accept/i }));

    expect(onChange).toHaveBeenCalledWith({ Other: "x" });
  });

  it("keeps a new row visible while its name is still blank", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<KeyValueEditor label="Headers" value={{ Accept: "json" }} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: /add headers/i }));

    // The row is on screen, but a nameless entry is not reported upwards.
    expect(screen.getByLabelText("Headers name 2")).toBeInTheDocument();
    expect(onChange).toHaveBeenCalledWith({ Accept: "json" });
  });

  it("reports the entry once the new row has a name", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<KeyValueEditor label="Headers" value={{}} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: /add headers/i }));
    await user.type(screen.getByLabelText("Headers name 1"), "Accept");

    expect(onChange).toHaveBeenLastCalledWith({ Accept: "" });
  });
});
