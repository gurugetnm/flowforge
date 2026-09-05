"""Starter templates."""

from fastapi.testclient import TestClient

from app.templates import TEMPLATES


class TestTemplateCatalog:
    def test_lists_every_template(self, client: TestClient, registered_user: dict) -> None:
        response = client.get("/api/templates")

        assert response.status_code == 200
        assert {item["id"] for item in response.json()} == {t.id for t in TEMPLATES}

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get("/api/templates").status_code == 401


class TestCreateFromTemplate:
    def test_creates_a_workflow_with_the_template_graph(
        self, client: TestClient, registered_user: dict
    ) -> None:
        response = client.post("/api/templates/json-transform-pipeline/create", json={})

        assert response.status_code == 201, response.text
        workflow = response.json()
        assert workflow["name"] == "Transform and log JSON"
        assert workflow["status"] == "draft"
        assert workflow["node_count"] == 4

        graph = client.get(f"/api/workflows/{workflow['id']}/graph").json()
        assert len(graph["nodes"]) == 4
        assert len(graph["edges"]) == 3

    def test_the_name_can_be_overridden(self, client: TestClient, registered_user: dict) -> None:
        response = client.post(
            "/api/templates/json-transform-pipeline/create", json={"name": "My pipeline"}
        )

        assert response.json()["name"] == "My pipeline"

    def test_two_workflows_from_one_template_share_no_nodes(
        self, client: TestClient, registered_user: dict
    ) -> None:
        first = client.post("/api/templates/webhook-to-api/create", json={}).json()
        second = client.post("/api/templates/webhook-to-api/create", json={}).json()

        first_ids = {
            n["id"] for n in client.get(f"/api/workflows/{first['id']}/graph").json()["nodes"]
        }
        second_ids = {
            n["id"] for n in client.get(f"/api/workflows/{second['id']}/graph").json()["nodes"]
        }

        assert first_ids.isdisjoint(second_ids)

    def test_an_unknown_template_is_a_404(self, client: TestClient, registered_user: dict) -> None:
        assert client.post("/api/templates/nope/create", json={}).status_code == 404


class TestTemplatesAreRunnable:
    def test_every_template_validates_without_errors(
        self, client: TestClient, registered_user: dict
    ) -> None:
        for template in TEMPLATES:
            workflow = client.post(f"/api/templates/{template.id}/create", json={}).json()

            result = client.get(f"/api/workflows/{workflow['id']}/validate").json()

            assert result["is_valid"] is True, f"{template.id}: {result['errors']}"
            assert result["warnings"] == [], f"{template.id}: {result['warnings']}"

    def test_the_json_pipeline_template_runs_end_to_end(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = client.post("/api/templates/json-transform-pipeline/create", json={}).json()

        execution = client.post(f"/api/workflows/{workflow['id']}/run", json={"payload": {}}).json()

        assert execution["status"] == "succeeded"
        logged = next(r for r in execution["node_runs"] if r["node_label"] == "Log the result")
        assert logged["output"]["message"] == "Contact for 42 is ada@example.com"
