"""The workflow execution engine.

Execution is synchronous and single pass, which keeps it small enough to read
in one sitting:

1. validate the workflow, refusing to start if it cannot run;
2. resolve a topological order for the nodes;
3. walk that order, running the nodes the active branches reached;
4. record the input, output, timing and outcome of every node as it happens;
5. stop at the first failure, marking whatever is left as skipped.

Because a node only ever reads the output of nodes earlier in the order, one
pass is enough, and there is no scheduler, queue or broker to reason about.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import WorkflowInvalidError
from app.engine.graph import WorkflowGraph
from app.engine.validator import validate_workflow
from app.models import (
    Execution,
    ExecutionNode,
    ExecutionStatus,
    ExecutionTrigger,
    NodeRunStatus,
    Workflow,
    WorkflowNode,
)
from app.nodes import (
    NodeConfigError,
    NodeContext,
    NodeExecutionError,
    UnknownNodeTypeError,
    get_executor,
)

#: Node output is stored in JSONB and shown in the UI, so it is capped.
MAX_STORED_LOGS = 100


@dataclass(slots=True)
class _RunState:
    """Bookkeeping for one pass over the graph."""

    variables: dict[str, Any]
    trigger_payload: dict[str, Any]
    #: Outputs of nodes that have run, keyed by node id.
    outputs: dict[uuid.UUID, dict[str, Any]] = field(default_factory=dict)
    #: Outputs keyed by node label, for `{{ nodes.<label> }}` lookups.
    outputs_by_label: dict[str, Any] = field(default_factory=dict)
    #: Nodes an active branch has reached.
    activated: set[uuid.UUID] = field(default_factory=set)


async def execute_workflow(
    session: Session,
    workflow: Workflow,
    *,
    trigger: ExecutionTrigger = ExecutionTrigger.MANUAL,
    trigger_payload: dict[str, Any] | None = None,
    retry_of: Execution | None = None,
) -> Execution:
    """Run ``workflow`` once and return the persisted execution record.

    Raises `WorkflowInvalidError` when the workflow cannot run at all; a node
    failing during the run is recorded on the execution instead, because that
    is a result worth keeping rather than a bad request.
    """
    report = validate_workflow(workflow)
    if not report.is_valid:
        raise WorkflowInvalidError(
            "This workflow cannot run yet.",
            details=[
                {
                    "code": issue.code.value,
                    "message": issue.message,
                    "node_id": str(issue.node_id) if issue.node_id else None,
                    "node_label": issue.node_label,
                    "field": issue.field,
                }
                for issue in report.errors
            ],
        )

    execution = Execution(
        workflow_id=workflow.id,
        status=ExecutionStatus.RUNNING,
        trigger=trigger,
        trigger_payload=trigger_payload or {},
        variables={},
        started_at=datetime.now(UTC),
        retry_of_id=retry_of.id if retry_of else None,
    )
    session.add(execution)
    session.flush()

    graph = WorkflowGraph.from_workflow(workflow)
    order = graph.topological_order()
    state = _RunState(variables={}, trigger_payload=trigger_payload or {})

    trigger_node = _find_trigger(graph, order)
    state.activated.add(trigger_node)

    failure: str | None = None

    for sequence, node_id in enumerate(order):
        node = graph.nodes[node_id]

        if failure is not None or node_id not in state.activated:
            session.add(_record(execution, node, sequence, NodeRunStatus.SKIPPED))
            continue

        node_input = _merge_inputs(graph, state, node_id)
        record = _record(execution, node, sequence, NodeRunStatus.RUNNING, input=node_input)
        record.started_at = datetime.now(UTC)
        session.add(record)

        try:
            output, branches, logs = await _run_node(node, node_input, state)
        except (NodeExecutionError, NodeConfigError, UnknownNodeTypeError) as error:
            _finish(record, NodeRunStatus.FAILED, error=_error_message(error))
            failure = f"{node.label}: {_error_message(error)}"
            continue

        _finish(record, NodeRunStatus.SUCCEEDED, output=output, logs=logs)
        state.outputs[node_id] = output
        state.outputs_by_label[node.label] = output
        _activate_successors(graph, state, node_id, branches)

    _complete(execution, failure, state)
    session.flush()
    return execution


async def _run_node(
    node: WorkflowNode, node_input: dict[str, Any], state: _RunState
) -> tuple[dict[str, Any], tuple[str, ...] | None, list[str]]:
    """Validate and run one node, returning its output and chosen branches."""
    executor = get_executor(node.node_type)
    config = executor.validate_config(node.configuration)

    context = NodeContext(
        input=node_input,
        variables=state.variables,
        trigger=state.trigger_payload,
        nodes=dict(state.outputs_by_label),
    )
    result = await executor.execute(config, context)

    logs = [*context.logs, *result.logs][:MAX_STORED_LOGS]
    return result.output, result.branches, logs


def _find_trigger(graph: WorkflowGraph, order: list[uuid.UUID]) -> uuid.UUID:
    """The single trigger node. Validation has already guaranteed one exists."""
    for node_id in order:
        if get_executor(graph.nodes[node_id].node_type).is_trigger:
            return node_id
    raise WorkflowInvalidError("This workflow has no trigger.")


def _merge_inputs(graph: WorkflowGraph, state: _RunState, node_id: uuid.UUID) -> dict[str, Any]:
    """Combine the outputs of every upstream node that actually ran.

    When several branches converge on one node, later outputs win on a key
    collision, matching the order the upstream nodes ran in.
    """
    merged: dict[str, Any] = {}
    for connection in graph.incoming[node_id]:
        upstream = state.outputs.get(connection.source)
        if upstream is not None:
            merged.update(upstream)
    return merged


def _activate_successors(
    graph: WorkflowGraph,
    state: _RunState,
    node_id: uuid.UUID,
    branches: tuple[str, ...] | None,
) -> None:
    """Mark the nodes the taken branches lead to as reachable."""
    if branches is None:
        state.activated.update(graph.successors(node_id))
        return

    for handle in branches:
        state.activated.update(graph.successors(node_id, handle))


def _record(
    execution: Execution,
    node: WorkflowNode,
    sequence: int,
    status: NodeRunStatus,
    *,
    input: dict[str, Any] | None = None,
) -> ExecutionNode:
    return ExecutionNode(
        execution_id=execution.id,
        node_id=node.id,
        node_type=node.node_type,
        node_label=node.label,
        status=status,
        sequence=sequence,
        input=input or {},
    )


def _finish(
    record: ExecutionNode,
    status: NodeRunStatus,
    *,
    output: dict[str, Any] | None = None,
    logs: list[str] | None = None,
    error: str | None = None,
) -> None:
    record.status = status
    record.output = output or {}
    record.logs = {"messages": logs or []}
    record.error = error
    record.completed_at = datetime.now(UTC)
    if record.started_at is not None:
        record.duration_ms = _elapsed_ms(record.started_at, record.completed_at)


def _complete(execution: Execution, failure: str | None, state: _RunState) -> None:
    execution.status = ExecutionStatus.FAILED if failure else ExecutionStatus.SUCCEEDED
    execution.error = failure
    execution.variables = state.variables
    execution.completed_at = datetime.now(UTC)
    if execution.started_at is not None:
        execution.duration_ms = _elapsed_ms(execution.started_at, execution.completed_at)


def _elapsed_ms(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() * 1000))


def _error_message(error: Exception) -> str:
    message = getattr(error, "message", None)
    return str(message or error)
