"""Workflow CRUD, search and ownership behaviour."""

from typing import Any

from fastapi.testclient import TestClient


def create_workflow(client: TestClient, **payload: Any) -> dict[str, Any]:
    body = {"name": "Nightly sync", "description": "", **payload}
    response = client.post("/api/workflows", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def register_second_account(client: TestClient) -> None:
    """Sign the client in as a different account."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "other@example.com",
            "name": "Other Developer",
            "password": "another-good-password",
        },
    )
    assert response.status_code == 201, response.text


class TestCreate:
    def test_creates_a_draft_workflow(self, client: TestClient, registered_user: dict) -> None:
        workflow = create_workflow(client, name="  Nightly   sync  ")

        assert workflow["name"] == "Nightly sync"  # whitespace is normalised
        assert workflow["status"] == "draft"
        assert workflow["node_count"] == 0

    def test_does_not_expose_the_webhook_token(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = create_workflow(client)

        assert "webhook_token" not in workflow
        assert "owner_id" not in workflow

    def test_rejects_a_blank_name(self, client: TestClient, registered_user: dict) -> None:
        assert client.post("/api/workflows", json={"name": "   "}).status_code == 422

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.post("/api/workflows", json={"name": "Nightly sync"}).status_code == 401


class TestList:
    def test_returns_newest_activity_first(self, client: TestClient, registered_user: dict) -> None:
        create_workflow(client, name="First")
        second = create_workflow(client, name="Second")
        client.patch(f"/api/workflows/{second['id']}", json={"description": "touched"})

        body = client.get("/api/workflows").json()

        assert [item["name"] for item in body["items"]] == ["Second", "First"]
        assert body["total"] == 2

    def test_search_matches_name_and_description(
        self, client: TestClient, registered_user: dict
    ) -> None:
        create_workflow(client, name="Deploy pipeline")
        create_workflow(client, name="Nightly sync", description="Deploy the staging build")
        create_workflow(client, name="Unrelated")

        body = client.get("/api/workflows", params={"search": "deploy"}).json()

        assert body["total"] == 2
        assert {item["name"] for item in body["items"]} == {"Deploy pipeline", "Nightly sync"}

    def test_search_treats_wildcards_literally(
        self, client: TestClient, registered_user: dict
    ) -> None:
        create_workflow(client, name="Nightly sync")

        body = client.get("/api/workflows", params={"search": "' OR 1=1 --"}).json()

        assert body["total"] == 0

    def test_filters_by_status(self, client: TestClient, registered_user: dict) -> None:
        active = create_workflow(client, name="Active one")
        create_workflow(client, name="Draft one")
        client.patch(f"/api/workflows/{active['id']}", json={"status": "active"})

        body = client.get("/api/workflows", params={"status": "active"}).json()

        assert [item["name"] for item in body["items"]] == ["Active one"]

    def test_paginates(self, client: TestClient, registered_user: dict) -> None:
        for index in range(5):
            create_workflow(client, name=f"Workflow {index}")

        body = client.get("/api/workflows", params={"limit": 2, "offset": 2}).json()

        assert body["total"] == 5
        assert len(body["items"]) == 2

    def test_only_lists_workflows_owned_by_the_caller(
        self, client: TestClient, registered_user: dict
    ) -> None:
        create_workflow(client, name="Private")
        register_second_account(client)

        assert client.get("/api/workflows").json()["total"] == 0


class TestUpdate:
    def test_renames_and_changes_status(self, client: TestClient, registered_user: dict) -> None:
        workflow = create_workflow(client)

        response = client.patch(
            f"/api/workflows/{workflow['id']}",
            json={"name": "Renamed", "status": "active"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Renamed"
        assert response.json()["status"] == "active"

    def test_omitted_fields_are_left_alone(self, client: TestClient, registered_user: dict) -> None:
        workflow = create_workflow(client, description="Keep me")

        response = client.patch(f"/api/workflows/{workflow['id']}", json={"name": "Renamed"})

        assert response.json()["description"] == "Keep me"

    def test_rejects_an_unknown_status(self, client: TestClient, registered_user: dict) -> None:
        workflow = create_workflow(client)

        response = client.patch(f"/api/workflows/{workflow['id']}", json={"status": "nonsense"})

        assert response.status_code == 422


class TestDelete:
    def test_removes_the_workflow(self, client: TestClient, registered_user: dict) -> None:
        workflow = create_workflow(client)

        assert client.delete(f"/api/workflows/{workflow['id']}").status_code == 204
        assert client.get(f"/api/workflows/{workflow['id']}").status_code == 404


class TestDuplicate:
    def test_creates_an_independent_draft_copy(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = create_workflow(client, name="Nightly sync", description="Runs at 2am")
        client.patch(f"/api/workflows/{workflow['id']}", json={"status": "active"})

        response = client.post(f"/api/workflows/{workflow['id']}/duplicate")

        assert response.status_code == 201
        copy = response.json()
        assert copy["name"] == "Nightly sync (copy)"
        assert copy["description"] == "Runs at 2am"
        assert copy["status"] == "draft"
        assert copy["id"] != workflow["id"]

    def test_long_names_stay_within_the_limit(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = create_workflow(client, name="w" * 120)

        copy = client.post(f"/api/workflows/{workflow['id']}/duplicate").json()

        assert len(copy["name"]) <= 120
        assert copy["name"].endswith(" (copy)")


class TestOwnership:
    def test_another_users_workflow_reports_as_missing(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow = create_workflow(client)
        register_second_account(client)

        for request in (
            client.get(f"/api/workflows/{workflow['id']}"),
            client.patch(f"/api/workflows/{workflow['id']}", json={"name": "Hijacked"}),
            client.delete(f"/api/workflows/{workflow['id']}"),
            client.post(f"/api/workflows/{workflow['id']}/duplicate"),
        ):
            assert request.status_code == 404, request.text

    def test_unknown_id_is_a_clean_404(self, client: TestClient, registered_user: dict) -> None:
        response = client.get("/api/workflows/00000000-0000-4000-8000-000000000000")

        assert response.status_code == 404
        assert response.json()["detail"]["message"] == "Workflow not found."

    def test_malformed_id_is_rejected(self, client: TestClient, registered_user: dict) -> None:
        assert client.get("/api/workflows/not-a-uuid").status_code == 422


class TestSearchEscaping:
    def test_wildcards_in_the_search_term_are_literal(
        self, client: TestClient, registered_user: dict
    ) -> None:
        create_workflow(client, name="Discount 50% off")
        create_workflow(client, name="Unrelated workflow")

        body = client.get("/api/workflows", params={"search": "50%"}).json()

        assert [item["name"] for item in body["items"]] == ["Discount 50% off"]

    def test_underscore_is_not_a_single_character_wildcard(
        self, client: TestClient, registered_user: dict
    ) -> None:
        create_workflow(client, name="deploy staging")

        assert (
            client.get("/api/workflows", params={"search": "deploy_staging"}).json()["total"] == 0
        )
