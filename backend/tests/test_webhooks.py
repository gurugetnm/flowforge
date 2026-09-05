"""Inbound webhook handling."""

import uuid

from fastapi.testclient import TestClient

from tests.test_graph_api import edge, new_workflow, node, save


def webhook_workflow(client: TestClient, *, active: bool = True, method: str = "POST") -> dict:
    """Create a workflow triggered by a webhook that logs the body."""
    workflow_id = new_workflow(client, "Webhook workflow")
    trigger = node("webhook_trigger", "On webhook", allowed_method=method)
    logger = node("log", "Log body", message="action={{ trigger.body.action }}")
    assert save(client, workflow_id, [trigger, logger], [edge(trigger, logger)]).status_code == 200

    if active:
        client.patch(f"/api/workflows/{workflow_id}", json={"status": "active"})

    return client.get(f"/api/workflows/{workflow_id}").json()


class TestWebhookDelivery:
    def test_a_valid_call_runs_the_workflow(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        response = client.post(workflow["webhook_path"], json={"action": "opened"})

        assert response.status_code == 202, response.text
        body = response.json()
        assert body["status"] == "succeeded"

        execution = client.get(f"/api/executions/{body['execution_id']}").json()
        assert execution["trigger"] == "webhook"
        assert execution["trigger_payload"]["body"] == {"action": "opened"}

    def test_the_body_is_available_to_the_workflow(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        response = client.post(workflow["webhook_path"], json={"action": "closed"})
        execution = client.get(f"/api/executions/{response.json()['execution_id']}").json()

        logged = next(r for r in execution["node_runs"] if r["node_label"] == "Log body")
        assert logged["output"]["message"] == "action=closed"

    def test_query_parameters_are_forwarded(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        response = client.post(f"{workflow['webhook_path']}?source=ci", json={"action": "opened"})
        execution = client.get(f"/api/executions/{response.json()['execution_id']}").json()

        assert execution["trigger_payload"]["query"] == {"source": "ci"}

    def test_a_non_json_body_is_passed_through_as_text(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        response = client.post(
            workflow["webhook_path"], content=b"plain text", headers={"Content-Type": "text/plain"}
        )
        execution = client.get(f"/api/executions/{response.json()['execution_id']}").json()

        assert execution["trigger_payload"]["body"] == "plain text"

    def test_a_failing_run_reports_a_gateway_error(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client, "Broken webhook")
        trigger = node("webhook_trigger", "On webhook")
        broken = node("log", "Broken", message="{{ trigger.body.missing }}")
        save(client, workflow_id, [trigger, broken], [edge(trigger, broken)])
        client.patch(f"/api/workflows/{workflow_id}", json={"status": "active"})
        detail = client.get(f"/api/workflows/{workflow_id}").json()

        response = client.post(detail["webhook_path"], json={})

        assert response.status_code == 502
        assert response.json()["status"] == "failed"


class TestWebhookSecurity:
    def test_a_wrong_token_is_rejected(self, client: TestClient, registered_user: dict) -> None:
        workflow = webhook_workflow(client)
        wrong = f"/api/webhooks/{workflow['id']}/{'x' * 43}"

        assert client.post(wrong, json={}).status_code == 404

    def test_an_unknown_workflow_is_rejected(
        self, client: TestClient, registered_user: dict
    ) -> None:
        response = client.post(f"/api/webhooks/{uuid.uuid4()}/{'x' * 43}", json={})

        assert response.status_code == 404

    def test_the_rejection_is_identical_for_a_bad_id_and_a_bad_token(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        bad_token = client.post(f"/api/webhooks/{workflow['id']}/{'x' * 43}", json={})
        bad_id = client.post(f"/api/webhooks/{uuid.uuid4()}/{'x' * 43}", json={})

        assert bad_token.status_code == bad_id.status_code
        assert bad_token.json() == bad_id.json()

    def test_a_draft_workflow_does_not_accept_webhooks(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client, active=False)

        response = client.post(workflow["webhook_path"], json={})

        assert response.status_code == 409
        assert "not active" in response.json()["detail"]["message"]

    def test_a_workflow_without_a_webhook_trigger_is_not_reachable(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client, "Manual only")
        save(client, workflow_id, [node("manual_trigger", "Start")], [])
        client.patch(f"/api/workflows/{workflow_id}", json={"status": "active"})
        detail = client.get(f"/api/workflows/{workflow_id}").json()

        assert client.post(detail["webhook_path"], json={}).status_code == 404

    def test_the_wrong_http_method_is_refused(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client, method="POST")

        response = client.get(workflow["webhook_path"])

        assert response.status_code == 409
        assert "POST" in response.json()["detail"]["message"]

    def test_no_authentication_is_needed(self, client: TestClient, registered_user: dict) -> None:
        workflow = webhook_workflow(client)
        client.post("/api/auth/logout")

        assert client.post(workflow["webhook_path"], json={"action": "opened"}).status_code == 202

    def test_the_response_reveals_nothing_about_the_workflow(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        body = client.post(workflow["webhook_path"], json={"action": "opened"}).json()

        assert set(body) == {"execution_id", "status"}

    def test_only_expected_headers_are_stored(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = webhook_workflow(client)

        response = client.post(
            workflow["webhook_path"],
            json={"action": "opened"},
            headers={"X-Github-Event": "push", "Authorization": "Bearer super-secret"},
        )
        execution = client.get(f"/api/executions/{response.json()['execution_id']}").json()

        headers = execution["trigger_payload"]["headers"]
        assert headers["x-github-event"] == "push"
        assert "authorization" not in headers
        assert "super-secret" not in str(execution["trigger_payload"])

    def test_an_oversized_body_is_refused(self, client: TestClient, registered_user: dict) -> None:
        workflow = webhook_workflow(client)

        response = client.post(
            workflow["webhook_path"],
            content=b"x" * (128 * 1024 + 1),
            headers={"Content-Type": "application/octet-stream"},
        )

        assert response.status_code == 409
        assert "too large" in response.json()["detail"]["message"]
