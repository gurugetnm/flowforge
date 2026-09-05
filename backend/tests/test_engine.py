"""The execution engine: ordering, branching, data flow and failure handling."""

import uuid
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from tests.test_graph_api import edge, new_workflow, node, save


def run(client: TestClient, workflow_id: str, payload: dict | None = None) -> dict[str, Any]:
    response = client.post(f"/api/workflows/{workflow_id}/run", json={"payload": payload or {}})
    assert response.status_code in (201, 422), response.text
    return response.json()


def runs_by_label(execution: dict) -> dict[str, dict]:
    return {item["node_label"]: item for item in execution["node_runs"]}


def build(client: TestClient, nodes: list, edges: list, name: str = "Engine test") -> str:
    workflow_id = new_workflow(client, name)
    response = save(client, workflow_id, nodes, edges)
    assert response.status_code == 200, response.text
    return workflow_id


class TestBasicRun:
    def test_runs_nodes_in_dependency_order(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        first = node("log", "First", message="one")
        second = node("log", "Second", message="two")
        workflow_id = build(
            client, [trigger, first, second], [edge(trigger, first), edge(first, second)]
        )

        execution = run(client, workflow_id)

        assert execution["status"] == "succeeded"
        assert [item["node_label"] for item in execution["node_runs"]] == [
            "Start",
            "First",
            "Second",
        ]
        assert all(item["status"] == "succeeded" for item in execution["node_runs"])

    def test_records_timing_for_the_run_and_each_node(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        workflow_id = build(client, [trigger], [])

        execution = run(client, workflow_id)

        assert execution["started_at"] is not None
        assert execution["completed_at"] is not None
        assert execution["duration_ms"] >= 0
        assert execution["node_runs"][0]["duration_ms"] >= 0

    def test_trigger_payload_reaches_the_first_node(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Echo", message="user={{ trigger.user }}")
        workflow_id = build(client, [trigger, logger], [edge(trigger, logger)])

        execution = run(client, workflow_id, {"user": "ada"})

        assert runs_by_label(execution)["Echo"]["output"]["message"] == "user=ada"

    def test_an_invalid_workflow_is_refused_before_it_starts(
        self, client: TestClient, registered_user: dict
    ) -> None:
        request = node("http_request", "No URL", method="GET")
        workflow_id = build(client, [node("manual_trigger", "Start"), request], [])

        response = client.post(f"/api/workflows/{workflow_id}/run", json={"payload": {}})

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == "workflow_invalid"
        assert any("required" in issue["message"] for issue in detail["details"])
        # Nothing was recorded, because the run never began.
        assert client.get("/api/executions").json()["total"] == 0


class TestDataFlow:
    def test_output_of_one_node_is_the_input_of_the_next(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        source = node("json_input", "Seed", payload='{"user": {"id": 42, "name": "Ada"}}')
        transform = node(
            "json_transform", "Reshape", template='{"greeting": "Hi {{ input.user.name }}"}'
        )
        workflow_id = build(
            client, [trigger, source, transform], [edge(trigger, source), edge(source, transform)]
        )

        execution = run(client, workflow_id)

        assert runs_by_label(execution)["Reshape"]["input"]["user"] == {"id": 42, "name": "Ada"}
        assert runs_by_label(execution)["Reshape"]["output"] == {"greeting": "Hi Ada"}

    def test_variables_are_visible_to_later_nodes(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        setter = node("set_variable", "Set token", name="token", value="abc-123")
        logger = node("log", "Use token", message="token is {{ vars.token }}")
        workflow_id = build(
            client, [trigger, setter, logger], [edge(trigger, setter), edge(setter, logger)]
        )

        execution = run(client, workflow_id)

        assert runs_by_label(execution)["Use token"]["output"]["message"] == "token is abc-123"
        assert execution["variables"] == {"token": "abc-123"}

    def test_a_missing_expression_fails_the_node_with_a_clear_message(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Broken", message="{{ input.nope.deeper }}")
        workflow_id = build(client, [trigger, logger], [edge(trigger, logger)])

        execution = run(client, workflow_id)

        assert execution["status"] == "failed"
        assert "is not available" in runs_by_label(execution)["Broken"]["error"]
        assert execution["error"].startswith("Broken:")


class TestBranching:
    def _condition_workflow(self, client: TestClient, operator: str, right: str) -> str:
        trigger = node("manual_trigger", "Start")
        condition = node(
            "condition", "Check", left="{{ trigger.status }}", operator=operator, right=right
        )
        yes = node("log", "Taken", message="yes")
        no = node("log", "Not taken", message="no")
        return build(
            client,
            [trigger, condition, yes, no],
            [
                edge(trigger, condition),
                edge(condition, yes, source_handle="true"),
                edge(condition, no, source_handle="false"),
            ],
        )

    def test_the_true_branch_runs_and_the_false_branch_is_skipped(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = self._condition_workflow(client, "equals", "ok")

        execution = run(client, workflow_id, {"status": "ok"})

        runs = runs_by_label(execution)
        assert runs["Taken"]["status"] == "succeeded"
        assert runs["Not taken"]["status"] == "skipped"
        assert execution["status"] == "succeeded"

    def test_the_false_branch_runs_when_the_condition_fails(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = self._condition_workflow(client, "equals", "ok")

        execution = run(client, workflow_id, {"status": "broken"})

        runs = runs_by_label(execution)
        assert runs["Taken"]["status"] == "skipped"
        assert runs["Not taken"]["status"] == "succeeded"

    @pytest.mark.parametrize(
        ("operator", "right", "value", "expected"),
        [
            ("equals", "200", 200, True),
            ("equals", "200", 404, False),
            ("not_equals", "200", 404, True),
            ("greater_than", "100", 200, True),
            ("less_than", "100", 200, False),
            ("contains", "ok", "not ok", True),
            ("is_empty", "", "", True),
            ("is_not_empty", "", "value", True),
            ("is_true", "", True, True),
        ],
    )
    def test_operators(
        self,
        client: TestClient,
        registered_user: dict,
        operator: str,
        right: str,
        value: Any,
        expected: bool,
    ) -> None:
        workflow_id = self._condition_workflow(client, operator, right)

        execution = run(client, workflow_id, {"status": value})

        runs = runs_by_label(execution)
        assert (runs["Taken"]["status"] == "succeeded") is expected

    def test_a_switch_takes_the_matching_case(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        switch = node("switch", "Route", value="{{ trigger.action }}", cases=["opened", "closed"])
        opened = node("log", "On opened", message="opened")
        closed = node("log", "On closed", message="closed")
        fallback = node("log", "Fallback", message="other")
        workflow_id = build(
            client,
            [trigger, switch, opened, closed, fallback],
            [
                edge(trigger, switch),
                edge(switch, opened, source_handle="case:0"),
                edge(switch, closed, source_handle="case:1"),
                edge(switch, fallback, source_handle="default"),
            ],
        )

        execution = run(client, workflow_id, {"action": "closed"})

        runs = runs_by_label(execution)
        assert runs["On closed"]["status"] == "succeeded"
        assert runs["On opened"]["status"] == "skipped"
        assert runs["Fallback"]["status"] == "skipped"

    def test_a_switch_falls_through_to_default(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        switch = node("switch", "Route", value="{{ trigger.action }}", cases=["opened"])
        fallback = node("log", "Fallback", message="other")
        workflow_id = build(
            client,
            [trigger, switch, fallback],
            [edge(trigger, switch), edge(switch, fallback, source_handle="default")],
        )

        execution = run(client, workflow_id, {"action": "deleted"})

        assert runs_by_label(execution)["Fallback"]["status"] == "succeeded"


class TestFailureHandling:
    def test_a_failed_node_stops_the_run_and_skips_the_rest(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        broken = node("log", "Broken", message="{{ input.missing }}")
        after = node("log", "After", message="never")
        workflow_id = build(
            client, [trigger, broken, after], [edge(trigger, broken), edge(broken, after)]
        )

        execution = run(client, workflow_id)

        runs = runs_by_label(execution)
        assert execution["status"] == "failed"
        assert runs["Broken"]["status"] == "failed"
        assert runs["After"]["status"] == "skipped"

    def test_the_failure_is_recorded_on_the_execution(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        broken = node("log", "Broken", message="{{ nope.value }}")
        workflow_id = build(client, [trigger, broken], [edge(trigger, broken)])

        execution = run(client, workflow_id)

        assert execution["error"] is not None
        assert "Broken" in execution["error"]


class TestHttpRequestNode:
    def _workflow(self, client: TestClient, **config: Any) -> str:
        trigger = node("manual_trigger", "Start")
        request = node("http_request", "Call API", **config)
        return build(client, [trigger, request], [edge(trigger, request)])

    @respx.mock
    def test_successful_json_response_is_passed_downstream(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        respx.get("https://api.example.com/users/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "name": "Ada"})
        )
        workflow_id = self._workflow(client, method="GET", url="https://api.example.com/users/1")

        execution = run(client, workflow_id)

        output = runs_by_label(execution)["Call API"]["output"]
        assert output["status_code"] == 200
        assert output["body"] == {"id": 1, "name": "Ada"}

    @respx.mock
    def test_url_and_headers_resolve_expressions(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        route = respx.get("https://api.example.com/users/42").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        workflow_id = self._workflow(
            client,
            method="GET",
            url="https://api.example.com/users/{{ trigger.id }}",
            headers={"Authorization": "Bearer {{ trigger.token }}"},
        )

        run(client, workflow_id, {"id": 42, "token": "abc"})

        assert route.called
        assert route.calls.last.request.headers["authorization"] == "Bearer abc"

    @respx.mock
    def test_a_post_body_is_sent_as_json(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        route = respx.post("https://api.example.com/users").mock(
            return_value=httpx.Response(201, json={"id": 9})
        )
        workflow_id = self._workflow(
            client,
            method="POST",
            url="https://api.example.com/users",
            body='{"name": "{{ trigger.name }}"}',
        )

        run(client, workflow_id, {"name": "Ada"})

        assert route.calls.last.request.content == b'{"name": "Ada"}'

    @respx.mock
    def test_an_error_status_fails_the_node(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        respx.get("https://api.example.com/missing").mock(
            return_value=httpx.Response(404, json={"detail": "gone"})
        )
        workflow_id = self._workflow(client, method="GET", url="https://api.example.com/missing")

        execution = run(client, workflow_id)

        assert execution["status"] == "failed"
        assert "status 404" in runs_by_label(execution)["Call API"]["error"]

    @respx.mock
    def test_a_timeout_is_reported_as_such(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        respx.get("https://api.example.com/slow").mock(side_effect=httpx.ConnectTimeout)
        workflow_id = self._workflow(
            client, method="GET", url="https://api.example.com/slow", timeout_seconds=1
        )

        execution = run(client, workflow_id)

        assert "timed out" in runs_by_label(execution)["Call API"]["error"]

    def test_a_private_address_is_blocked(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = self._workflow(client, method="GET", url="http://127.0.0.1:9/secret")

        execution = run(client, workflow_id)

        assert execution["status"] == "failed"
        assert "blocked" in runs_by_label(execution)["Call API"]["error"]

    def test_the_metadata_endpoint_is_blocked(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = self._workflow(
            client, method="GET", url="http://169.254.169.254/latest/meta-data/"
        )

        execution = run(client, workflow_id)

        assert "blocked" in runs_by_label(execution)["Call API"]["error"]

    @respx.mock
    def test_a_redirect_into_a_private_address_is_blocked(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        respx.get("https://api.example.com/redirect").mock(
            return_value=httpx.Response(302, headers={"Location": "http://169.254.169.254/"})
        )
        workflow_id = self._workflow(client, method="GET", url="https://api.example.com/redirect")

        execution = run(client, workflow_id)

        assert execution["status"] == "failed"
        assert "blocked" in runs_by_label(execution)["Call API"]["error"]

    @respx.mock
    def test_secrets_are_not_written_into_the_run_log(
        self, client: TestClient, registered_user: dict, public_dns: None
    ) -> None:
        respx.get("https://api.example.com/data").mock(return_value=httpx.Response(200, json={}))
        workflow_id = self._workflow(
            client,
            method="GET",
            url="https://api.example.com/data?token=super-secret",
            headers={"Authorization": "Bearer super-secret"},
        )

        execution = run(client, workflow_id)

        serialised = str(execution)
        assert "super-secret" not in runs_by_label(execution)["Call API"]["logs"]["messages"][0]
        assert "***" in runs_by_label(execution)["Call API"]["logs"]["messages"][0]
        # The configured header is not echoed back into the stored output either.
        assert "super-secret" not in str(runs_by_label(execution)["Call API"]["output"])
        assert serialised is not None


class TestExecutionHistory:
    def test_runs_are_listed_newest_first(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = build(client, [node("manual_trigger", "Start")], [])
        run(client, workflow_id)
        run(client, workflow_id)

        body = client.get("/api/executions").json()

        assert body["total"] == 2
        assert body["items"][0]["workflow_name"] == "Engine test"

    def test_filters_by_status_and_workflow(
        self, client: TestClient, registered_user: dict
    ) -> None:
        ok_id = build(client, [node("manual_trigger", "Start")], [], name="Fine")
        trigger = node("manual_trigger", "Start")
        broken = node("log", "Broken", message="{{ nope }}")
        bad_id = build(client, [trigger, broken], [edge(trigger, broken)], name="Broken")
        run(client, ok_id)
        run(client, bad_id)

        failed = client.get("/api/executions", params={"status": "failed"}).json()
        by_workflow = client.get("/api/executions", params={"workflow_id": ok_id}).json()

        assert failed["total"] == 1
        assert failed["items"][0]["workflow_name"] == "Broken"
        assert by_workflow["total"] == 1

    def test_detail_includes_every_node_result(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Log it", message="hi")
        workflow_id = build(client, [trigger, logger], [edge(trigger, logger)])
        execution_id = run(client, workflow_id)["id"]

        detail = client.get(f"/api/executions/{execution_id}").json()

        assert len(detail["node_runs"]) == 2
        assert detail["node_runs"][1]["logs"]["messages"] == ["[info] hi"]

    def test_another_users_execution_is_not_visible(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = build(client, [node("manual_trigger", "Start")], [])
        execution_id = run(client, workflow_id)["id"]
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "name": "Other", "password": "another-password"},
        )

        assert client.get(f"/api/executions/{execution_id}").status_code == 404
        assert client.get("/api/executions").json()["total"] == 0

    def test_unknown_execution_is_a_404(self, client: TestClient, registered_user: dict) -> None:
        assert client.get(f"/api/executions/{uuid.uuid4()}").status_code == 404


class TestRetry:
    def test_retry_reruns_with_the_original_trigger_data(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Echo", message="value={{ trigger.value }}")
        workflow_id = build(client, [trigger, logger], [edge(trigger, logger)])
        original = run(client, workflow_id, {"value": "kept"})

        response = client.post(f"/api/executions/{original['id']}/retry")

        assert response.status_code == 201
        retry = response.json()
        assert retry["trigger"] == "retry"
        assert retry["retry_of_id"] == original["id"]
        assert runs_by_label(retry)["Echo"]["output"]["message"] == "value=kept"

    def test_the_original_run_is_preserved(self, client: TestClient, registered_user: dict) -> None:
        trigger = node("manual_trigger", "Start")
        broken = node("log", "Broken", message="{{ nope }}")
        workflow_id = build(client, [trigger, broken], [edge(trigger, broken)])
        original = run(client, workflow_id)
        assert original["status"] == "failed"

        client.post(f"/api/executions/{original['id']}/retry")
        reloaded = client.get(f"/api/executions/{original['id']}").json()

        assert reloaded["status"] == "failed"
        assert reloaded["error"] == original["error"]
        assert client.get("/api/executions").json()["total"] == 2

    def test_a_retry_of_a_fixed_workflow_succeeds(
        self, client: TestClient, registered_user: dict
    ) -> None:
        trigger = node("manual_trigger", "Start")
        broken = node("log", "Maybe", message="{{ trigger.value }}")
        workflow_id = build(client, [trigger, broken], [edge(trigger, broken)])
        original = run(client, workflow_id)
        assert original["status"] == "failed"

        retry = client.post(f"/api/executions/{original['id']}/retry").json()

        # Same empty payload, so it fails again; the link is what matters here.
        assert retry["status"] == "failed"
        assert retry["retry_of_id"] == original["id"]
