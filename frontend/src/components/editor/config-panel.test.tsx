import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfigPanel } from "@/components/editor/config-panel";
import type { NodeField, NodeType, ValidationIssue } from "@/lib/types";

function field(overrides: Partial<NodeField> & Pick<NodeField, "key" | "label">): NodeField {
  return {
    control: "text",
    required: false,
    default: null,
    help_text: "",
    placeholder: "",
    options: [],
    supports_expressions: false,
    depends_on: null,
    depends_on_values: [],
    ...overrides,
  };
}

const httpRequest: NodeType = {
  type: "http_request",
  name: "HTTP Request",
  category: "action",
  description: "Calls an HTTP API.",
  accepts_input: true,
  is_trigger: false,
  outputs: [{ key: "out", label: "Output", description: "" }],
  default_configuration: { method: "GET", timeout_seconds: 10 },
  fields: [
    field({
      key: "method",
      label: "Method",
      control: "select",
      default: "GET",
      options: [
        { value: "GET", label: "GET" },
        { value: "POST", label: "POST" },
      ],
    }),
    field({ key: "url", label: "URL", required: true, supports_expressions: true }),
    field({ key: "headers", label: "Headers", control: "key_value" }),
    field({
      key: "body",
      label: "Request body",
      control: "json",
      depends_on: "method",
      depends_on_values: ["POST"],
    }),
    field({ key: "timeout_seconds", label: "Timeout (seconds)", control: "number", default: 10 }),
  ],
};

function renderPanel(
  overrides: {
    configuration?: Record<string, unknown>;
    issues?: ValidationIssue[];
    definition?: NodeType | undefined;
  } = {},
) {
  const onConfigurationChange = vi.fn();
  const onLabelChange = vi.fn();
  const onDelete = vi.fn();

  render(
    <ConfigPanel
      nodeId="node-1"
      label="Fetch user"
      configuration={overrides.configuration ?? { method: "GET", url: "" }}
      definition={"definition" in overrides ? overrides.definition : httpRequest}
      issues={overrides.issues ?? []}
      onLabelChange={onLabelChange}
      onConfigurationChange={onConfigurationChange}
      onDelete={onDelete}
    />,
  );

  return { onConfigurationChange, onLabelChange, onDelete };
}

describe("ConfigPanel", () => {
  it("renders a control for every declared field", () => {
    renderPanel();

    expect(screen.getByLabelText(/^Label/)).toHaveValue("Fetch user");
    expect(screen.getByLabelText(/^Method/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^URL/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Timeout/)).toHaveValue(10);
  });

  it("hides a field whose condition is not met", () => {
    renderPanel({ configuration: { method: "GET" } });

    expect(screen.queryByLabelText(/Request body/)).not.toBeInTheDocument();
  });

  it("shows a conditional field once the condition is met", () => {
    renderPanel({ configuration: { method: "POST" } });

    expect(screen.getByLabelText(/Request body/)).toBeInTheDocument();
  });

  it("reports edits to the caller", async () => {
    const user = userEvent.setup();
    const { onConfigurationChange } = renderPanel({ configuration: { method: "GET", url: "" } });

    await user.type(screen.getByLabelText(/^URL/), "h");

    expect(onConfigurationChange).toHaveBeenCalledWith({
      method: "GET",
      url: "h",
    });
  });

  it("keeps numbers as numbers rather than strings", async () => {
    const user = userEvent.setup();
    const { onConfigurationChange } = renderPanel({
      configuration: { method: "GET", timeout_seconds: 1 },
    });

    await user.type(screen.getByLabelText(/^Timeout/), "5");

    expect(onConfigurationChange).toHaveBeenCalledWith(
      expect.objectContaining({ timeout_seconds: 15 }),
    );
  });

  it("marks a required field and shows its validation error", () => {
    renderPanel({
      issues: [
        {
          code: "invalid_configuration",
          severity: "error",
          message: "Fetch user: This field is required.",
          node_id: "node-1",
          node_label: "Fetch user",
          field: "url",
        },
      ],
    });

    // The node name is stripped, because the panel already shows it.
    expect(screen.getByRole("alert")).toHaveTextContent("This field is required.");
  });

  it("mentions expression support in the hint", () => {
    renderPanel();

    expect(screen.getByText(/Supports \{\{ expressions \}\}/)).toBeInTheDocument();
  });

  it("explains when the node type is not installed", () => {
    renderPanel({ definition: undefined });

    expect(screen.getByRole("alert")).toHaveTextContent("not installed on the server");
  });

  it("deletes the node when asked", async () => {
    const user = userEvent.setup();
    const { onDelete } = renderPanel();

    await user.click(screen.getByRole("button", { name: /delete node/i }));

    expect(onDelete).toHaveBeenCalledOnce();
  });
});
