"""Database level behaviour of the core models."""

import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.models import (
    Base,
    Execution,
    ExecutionNode,
    ExecutionStatus,
    ExecutionTrigger,
    NodeRunStatus,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowStatus,
)
from tests.factories import make_user, make_workflow, unique_email


class TestUser:
    def test_defaults(self, session: Session) -> None:
        user = make_user(session)

        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_email_is_unique(self, session: Session) -> None:
        email = unique_email()
        make_user(session, email=email)

        with pytest.raises(IntegrityError):
            make_user(session, email=email)


class TestWorkflow:
    def test_defaults(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))

        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.description == ""
        assert workflow.nodes == []

    def test_webhook_token_is_unique(self, session: Session) -> None:
        user = make_user(session)
        token = uuid.uuid4().hex
        make_workflow(session, user, webhook_token=token)

        with pytest.raises(IntegrityError):
            make_workflow(session, user, webhook_token=token)

    def test_deleting_owner_cascades_to_workflows(self, session: Session) -> None:
        user = make_user(session)
        make_workflow(session, user)

        session.delete(user)
        session.flush()

        assert session.scalars(select(Workflow)).all() == []


class TestWorkflowGraph:
    def test_nodes_store_json_configuration(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))
        node = WorkflowNode(
            workflow_id=workflow.id,
            node_type="http_request",
            label="Fetch user",
            configuration={"method": "GET", "url": "https://api.example.com", "headers": {}},
            position_x=120.5,
            position_y=-40.0,
        )
        session.add(node)
        session.flush()
        session.expire(node)

        assert node.configuration["method"] == "GET"
        assert node.position_x == pytest.approx(120.5)

    def test_edges_connect_nodes_and_cascade(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))
        source = WorkflowNode(workflow_id=workflow.id, node_type="manual_trigger", label="Start")
        target = WorkflowNode(workflow_id=workflow.id, node_type="log", label="Log")
        session.add_all([source, target])
        session.flush()

        edge = WorkflowEdge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        session.add(edge)
        session.flush()

        assert edge.source_handle == "out"
        assert edge.target_handle == "in"

        session.delete(source)
        session.flush()
        assert session.scalars(select(WorkflowEdge)).all() == []

    def test_duplicate_connections_are_rejected(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))
        source = WorkflowNode(workflow_id=workflow.id, node_type="manual_trigger", label="Start")
        target = WorkflowNode(workflow_id=workflow.id, node_type="log", label="Log")
        session.add_all([source, target])
        session.flush()

        for _ in range(2):
            session.add(
                WorkflowEdge(
                    workflow_id=workflow.id,
                    source_node_id=source.id,
                    target_node_id=target.id,
                    source_handle="out",
                    target_handle="in",
                )
            )

        with pytest.raises(IntegrityError):
            session.flush()


class TestExecution:
    def test_records_node_runs_in_sequence(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))
        execution = Execution(
            workflow_id=workflow.id,
            status=ExecutionStatus.SUCCEEDED,
            trigger=ExecutionTrigger.MANUAL,
            trigger_payload={"source": "test"},
        )
        session.add(execution)
        session.flush()

        session.add_all(
            [
                ExecutionNode(
                    execution_id=execution.id,
                    node_type="log",
                    node_label="Second",
                    status=NodeRunStatus.SUCCEEDED,
                    sequence=1,
                ),
                ExecutionNode(
                    execution_id=execution.id,
                    node_type="manual_trigger",
                    node_label="First",
                    status=NodeRunStatus.SUCCEEDED,
                    sequence=0,
                    output={"payload": {"source": "test"}},
                ),
            ]
        )
        session.flush()
        session.expire(execution)

        assert [run.node_label for run in execution.node_runs] == ["First", "Second"]
        assert execution.node_runs[0].output == {"payload": {"source": "test"}}

    def test_retry_links_back_to_original(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))
        original = Execution(workflow_id=workflow.id, status=ExecutionStatus.FAILED, error="boom")
        session.add(original)
        session.flush()

        retry = Execution(
            workflow_id=workflow.id,
            status=ExecutionStatus.SUCCEEDED,
            trigger=ExecutionTrigger.RETRY,
            retry_of_id=original.id,
        )
        session.add(retry)
        session.flush()
        session.expire(retry)

        assert retry.retry_of is not None
        assert retry.retry_of.id == original.id
        # The original record is preserved exactly as it was.
        assert original.status == ExecutionStatus.FAILED
        assert original.error == "boom"

    def test_deleting_a_node_keeps_its_run_history(self, session: Session) -> None:
        workflow = make_workflow(session, make_user(session))
        node = WorkflowNode(workflow_id=workflow.id, node_type="log", label="Log")
        execution = Execution(workflow_id=workflow.id, status=ExecutionStatus.SUCCEEDED)
        session.add_all([node, execution])
        session.flush()

        run = ExecutionNode(
            execution_id=execution.id,
            node_id=node.id,
            node_type="log",
            node_label="Log",
            status=NodeRunStatus.SUCCEEDED,
        )
        session.add(run)
        session.flush()

        session.delete(node)
        session.flush()
        session.expire(run)

        assert run.node_id is None
        assert run.node_label == "Log"


class TestMigrations:
    def test_schema_matches_models(self, engine: Engine, alembic_config: Config) -> None:
        """The migration history must produce exactly the mapped schema."""
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            diff = compare_metadata(context, Base.metadata)

        assert diff == [], f"Models and migrations have drifted: {diff}"

    def test_downgrade_and_upgrade_round_trip(self, alembic_config: Config, engine: Engine) -> None:
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")

        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            assert compare_metadata(context, Base.metadata) == []
