"""Workflow validation: what blocks a run, and what only warns."""

import uuid

from fastapi.testclient import TestClient

from tests.test_graph_api import edge, new_workflow, node, save


def validate(client: TestClient, workflow_id: str) -> dict:
    response = client.get(f"/api/workflows/{workflow_id}/validate")
    assert response.status_code == 200, response.text
    return response.json()


def codes(result: dict, key: str = "errors") -> set[str]:
    return {issue["code"] for issue in result[key]}


def messages(result: dict, key: str = "errors") -> str:
    return " | ".join(issue["message"] for issue in result[key])


class TestStructure:
    def test_an_empty_workflow_cannot_run(self, client: TestClient, registered_user: dict) -> None:
        result = validate(client, new_workflow(client))

        assert result["is_valid"] is False
        assert codes(result) == {"empty_workflow"}
        assert "no nodes" in messages(result)

    def test_a_workflow_without_a_trigger_cannot_run(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        save(client, workflow_id, [node("log", "Just a log", message="hi")], [])

        result = validate(client, workflow_id)

        assert codes(result) == {"no_trigger"}
        assert "Manual Trigger" in messages(result)

    def test_two_triggers_are_rejected(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)
        save(
            client,
            workflow_id,
            [node("manual_trigger", "One"), node("manual_trigger", "Two")],
            [],
        )

        result = validate(client, workflow_id)

        assert "multiple_triggers" in codes(result)
        assert "exactly one starting point" in messages(result)

    def test_a_loop_is_reported_with_the_nodes_involved(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        first = node("log", "First", message="a")
        second = node("log", "Second", message="b")
        save(
            client,
            workflow_id,
            [trigger, first, second],
            [edge(trigger, first), edge(first, second), edge(second, first)],
        )

        result = validate(client, workflow_id)

        assert "cycle" in codes(result)
        assert "First" in messages(result)
        assert "Second" in messages(result)

    def test_nothing_may_connect_into_a_trigger(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Log", message="a")
        save(
            client,
            workflow_id,
            [trigger, logger],
            [edge(trigger, logger), edge(logger, trigger)],
        )

        result = validate(client, workflow_id)

        assert "trigger_has_input" in codes(result)


class TestNodeConfiguration:
    def test_a_missing_url_names_the_node_and_the_field(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        request = node("http_request", "Fetch user", method="GET")
        save(client, workflow_id, [trigger, request], [edge(trigger, request)])

        result = validate(client, workflow_id)

        assert result["is_valid"] is False
        issue = next(i for i in result["errors"] if i["code"] == "invalid_configuration")
        assert issue["message"] == "Fetch user: This field is required."
        assert issue["field"] == "url"
        assert issue["node_id"] == request["id"]

    def test_reports_every_bad_node_not_only_the_first(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        first = node("http_request", "First request", method="GET")
        second = node("set_variable", "Bad variable", name="not valid", value="x")
        save(
            client,
            workflow_id,
            [trigger, first, second],
            [edge(trigger, first), edge(first, second)],
        )

        result = validate(client, workflow_id)

        assert {i["node_label"] for i in result["errors"]} == {"First request", "Bad variable"}

    def test_an_unknown_node_type_is_reported(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        alien = node("quantum_flux", "From the future")
        save(client, workflow_id, [trigger, alien], [edge(trigger, alien)])

        result = validate(client, workflow_id)

        assert "unknown_node_type" in codes(result)
        assert "not installed" in messages(result)


class TestHandles:
    def test_an_edge_from_a_removed_branch_is_an_error(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        switch = node("switch", "Route", value="{{ input.x }}", cases=["a", "b"])
        logger = node("log", "Log", message="hi")
        save(
            client,
            workflow_id,
            [trigger, switch, logger],
            [edge(trigger, switch), edge(switch, logger, source_handle="case:1")],
        )
        # Removing a case leaves the edge attached to a handle that is gone.
        switch["configuration"]["cases"] = ["a"]
        save(
            client,
            workflow_id,
            [trigger, switch, logger],
            [edge(trigger, switch), edge(switch, logger, source_handle="case:1")],
        )

        result = validate(client, workflow_id)

        assert "unknown_handle" in codes(result)

    def test_an_unconnected_branch_only_warns(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        condition = node("condition", "Is ok", left="{{ input.x }}", operator="is_true")
        logger = node("log", "Log", message="hi")
        save(
            client,
            workflow_id,
            [trigger, condition, logger],
            [edge(trigger, condition), edge(condition, logger, source_handle="true")],
        )

        result = validate(client, workflow_id)

        assert result["is_valid"] is True
        assert "dead_end_branch" in codes(result, "warnings")
        assert "False" in messages(result, "warnings")


class TestReachability:
    def test_a_disconnected_node_only_warns(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        orphan = node("log", "Forgotten", message="hi")
        save(client, workflow_id, [trigger, orphan], [])

        result = validate(client, workflow_id)

        assert result["is_valid"] is True
        assert "unreachable_node" in codes(result, "warnings")
        assert "Forgotten" in messages(result, "warnings")


class TestValidWorkflow:
    def test_a_complete_workflow_validates_cleanly(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        request = node("http_request", "Fetch", method="GET", url="https://api.example.com/status")
        logger = node("log", "Log it", message="Got {{ input.status_code }}")
        save(
            client,
            workflow_id,
            [trigger, request, logger],
            [edge(trigger, request), edge(request, logger)],
        )

        result = validate(client, workflow_id)

        assert result["is_valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []

    def test_validation_requires_ownership(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "name": "Other", "password": "another-password"},
        )

        assert client.get(f"/api/workflows/{workflow_id}/validate").status_code == 404

    def test_unknown_workflow_is_a_404(self, client: TestClient, registered_user: dict) -> None:
        missing = uuid.uuid4()

        assert client.get(f"/api/workflows/{missing}/validate").status_code == 404
