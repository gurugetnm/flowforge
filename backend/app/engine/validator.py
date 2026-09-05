"""Workflow validation.

Every problem is reported against the node it belongs to, with a message that
says what to fix. The editor shows these inline, so "HTTP Request is missing a
URL" is the bar, not "invalid workflow".
"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.engine.graph import CycleError, WorkflowGraph
from app.models import Workflow
from app.nodes import NodeConfigError, UnknownNodeTypeError, get_executor
from app.nodes.registry import AnyExecutor


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class Code(StrEnum):
    """Stable identifiers so the client can react to a specific problem."""

    EMPTY_WORKFLOW = "empty_workflow"
    NO_TRIGGER = "no_trigger"
    MULTIPLE_TRIGGERS = "multiple_triggers"
    UNKNOWN_NODE_TYPE = "unknown_node_type"
    INVALID_CONFIGURATION = "invalid_configuration"
    TRIGGER_HAS_INPUT = "trigger_has_input"
    UNKNOWN_HANDLE = "unknown_handle"
    CYCLE = "cycle"
    UNREACHABLE_NODE = "unreachable_node"
    DEAD_END_BRANCH = "dead_end_branch"


@dataclass(frozen=True, slots=True)
class Issue:
    """One validation finding."""

    code: Code
    severity: Severity
    message: str
    node_id: uuid.UUID | None = None
    node_label: str | None = None
    #: The configuration key at fault, when the problem is a single field.
    field: str | None = None


@dataclass(slots=True)
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity is Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        """A workflow runs when it has no errors. Warnings do not block it."""
        return not self.errors

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)


def validate_workflow(workflow: Workflow) -> ValidationReport:
    """Check that ``workflow`` can be executed, collecting every problem."""
    report = ValidationReport()

    if not workflow.nodes:
        report.add(
            Issue(
                code=Code.EMPTY_WORKFLOW,
                severity=Severity.ERROR,
                message="This workflow has no nodes. Add a trigger to get started.",
            )
        )
        return report

    graph = WorkflowGraph.from_workflow(workflow)
    triggers = _validate_nodes(workflow, graph, report)
    _validate_trigger_count(triggers, report)
    _validate_structure(graph, triggers, report)

    return report


def _validate_nodes(
    workflow: Workflow, graph: WorkflowGraph, report: ValidationReport
) -> list[uuid.UUID]:
    """Check each node in isolation and return the ids of the trigger nodes."""
    triggers: list[uuid.UUID] = []

    for node in workflow.nodes:
        try:
            executor = get_executor(node.node_type)
        except UnknownNodeTypeError:
            report.add(
                Issue(
                    code=Code.UNKNOWN_NODE_TYPE,
                    severity=Severity.ERROR,
                    message=(
                        f"{node.label} uses the node type '{node.node_type}', "
                        "which is not installed."
                    ),
                    node_id=node.id,
                    node_label=node.label,
                )
            )
            continue

        if executor.is_trigger:
            triggers.append(node.id)

        try:
            executor.validate_config(node.configuration)
        except NodeConfigError as error:
            for field_name, messages in error.field_errors.items():
                report.add(
                    Issue(
                        code=Code.INVALID_CONFIGURATION,
                        severity=Severity.ERROR,
                        message=f"{node.label}: {messages[0]}",
                        node_id=node.id,
                        node_label=node.label,
                        field=None if field_name == "_" else field_name,
                    )
                )

        if not executor.accepts_input and graph.has_incoming(node.id):
            report.add(
                Issue(
                    code=Code.TRIGGER_HAS_INPUT,
                    severity=Severity.ERROR,
                    message=f"{node.label} is a trigger, so nothing can connect into it.",
                    node_id=node.id,
                    node_label=node.label,
                )
            )

        _validate_handles(node.id, node.label, executor, node.configuration, graph, report)

    return triggers


def _validate_handles(
    node_id: uuid.UUID,
    label: str,
    executor: AnyExecutor,
    configuration: dict[str, Any],
    graph: WorkflowGraph,
    report: ValidationReport,
) -> None:
    """Every edge must leave from an output the node actually has."""
    outputs = executor.outputs_for(configuration)
    declared = {output.key for output in outputs}
    used = graph.used_source_handles(node_id)

    for handle in sorted(used - declared):
        report.add(
            Issue(
                code=Code.UNKNOWN_HANDLE,
                severity=Severity.ERROR,
                message=(
                    f"{label} has a connection from an output ('{handle}') "
                    "that no longer exists. Reconnect or remove it."
                ),
                node_id=node_id,
                node_label=label,
            )
        )

    # A branching node with an unconnected branch silently drops those runs.
    if len(declared) > 1:
        for handle in sorted(declared - used):
            output_label = next(o.label for o in outputs if o.key == handle)
            report.add(
                Issue(
                    code=Code.DEAD_END_BRANCH,
                    severity=Severity.WARNING,
                    message=(
                        f"Nothing is connected to the '{output_label}' output of {label}. "
                        "Runs taking that branch will stop there."
                    ),
                    node_id=node_id,
                    node_label=label,
                )
            )


def _validate_trigger_count(triggers: list[uuid.UUID], report: ValidationReport) -> None:
    if not triggers:
        report.add(
            Issue(
                code=Code.NO_TRIGGER,
                severity=Severity.ERROR,
                message=(
                    "This workflow has no trigger. Add a Manual Trigger or a "
                    "Webhook Trigger to say where a run starts."
                ),
            )
        )
    elif len(triggers) > 1:
        report.add(
            Issue(
                code=Code.MULTIPLE_TRIGGERS,
                severity=Severity.ERROR,
                message=(
                    f"This workflow has {len(triggers)} triggers. A run needs exactly one "
                    "starting point, so keep one and remove the others."
                ),
            )
        )


def _validate_structure(
    graph: WorkflowGraph, triggers: list[uuid.UUID], report: ValidationReport
) -> None:
    try:
        graph.topological_order()
    except CycleError as error:
        labels = ", ".join(sorted(graph.label_of(node_id) for node_id in error.node_ids))
        report.add(
            Issue(
                code=Code.CYCLE,
                severity=Severity.ERROR,
                message=(
                    f"These nodes form a loop, so there is no order to run them in: {labels}."
                ),
            )
        )
        return

    if len(triggers) != 1:
        return

    reachable = graph.reachable_from(triggers[0])
    for node_id in graph.nodes:
        if node_id not in reachable:
            label = graph.label_of(node_id)
            report.add(
                Issue(
                    code=Code.UNREACHABLE_NODE,
                    severity=Severity.WARNING,
                    message=f"{label} is not connected to the trigger, so it will never run.",
                    node_id=node_id,
                    node_label=label,
                )
            )
