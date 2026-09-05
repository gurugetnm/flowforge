"""Reading and replacing a workflow's graph."""

import uuid
from typing import Any

from fastapi.testclient import TestClient


def new_workflow(client: TestClient, name: str = "Graph test") -> str:
    response = client.post("/api/workflows", json={"name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def node(node_type: str, label: str, node_id: str | None = None, **config: Any) -> dict[str, Any]:
    return {
        "id": node_id or str(uuid.uuid4()),
        "type": node_type,
        "label": label,
        "configuration": config,
        "position": {"x": 0, "y": 0},
    }


def edge(source: dict, target: dict, source_handle: str = "out") -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        "source_handle": source_handle,
        "target_handle": "in",
    }


def save(client: TestClient, workflow_id: str, nodes: list, edges: list) -> Any:
    return client.put(f"/api/workflows/{workflow_id}/graph", json={"nodes": nodes, "edges": edges})


class TestReadGraph:
    def test_a_new_workflow_has_an_empty_graph(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)

        body = client.get(f"/api/workflows/{workflow_id}/graph").json()

        assert body == {"nodes": [], "edges": []}


class TestReplaceGraph:
    def test_saves_nodes_and_connections(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Write log", message="hello")

        response = save(client, workflow_id, [trigger, logger], [edge(trigger, logger)])

        assert response.status_code == 200, response.text
        body = response.json()
        assert [n["label"] for n in body["nodes"]] == ["Start", "Write log"]
        assert body["edges"][0]["source"] == trigger["id"]
        assert body["nodes"][1]["configuration"] == {"message": "hello"}

    def test_positions_round_trip(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        trigger["position"] = {"x": 120.5, "y": -64.25}

        save(client, workflow_id, [trigger], [])
        body = client.get(f"/api/workflows/{workflow_id}/graph").json()

        assert body["nodes"][0]["position"] == {"x": 120.5, "y": -64.25}

    def test_replacing_the_graph_removes_deleted_nodes(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Write log")
        save(client, workflow_id, [trigger, logger], [edge(trigger, logger)])

        save(client, workflow_id, [trigger], [])
        body = client.get(f"/api/workflows/{workflow_id}/graph").json()

        assert [n["id"] for n in body["nodes"]] == [trigger["id"]]
        assert body["edges"] == []

    def test_surviving_nodes_keep_their_identity(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        save(client, workflow_id, [trigger], [])

        renamed = {**trigger, "label": "Renamed start"}
        body = save(client, workflow_id, [renamed], []).json()

        assert body["nodes"][0]["id"] == trigger["id"]
        assert body["nodes"][0]["label"] == "Renamed start"

    def test_an_edge_can_be_repointed_in_one_save(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        first = node("log", "First")
        second = node("log", "Second")
        save(client, workflow_id, [trigger, first, second], [edge(trigger, first)])

        response = save(client, workflow_id, [trigger, first, second], [edge(trigger, second)])

        assert response.status_code == 200
        assert response.json()["edges"][0]["target"] == second["id"]

    def test_saving_updates_the_workflow_timestamp(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        before = client.get(f"/api/workflows/{workflow_id}").json()["updated_at"]

        save(client, workflow_id, [node("manual_trigger", "Start")], [])
        after = client.get(f"/api/workflows/{workflow_id}").json()["updated_at"]

        assert after >= before


class TestGraphValidation:
    def test_rejects_an_edge_referencing_a_missing_node(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        orphan = node("log", "Never sent")

        response = save(client, workflow_id, [trigger], [edge(trigger, orphan)])

        assert response.status_code == 422
        assert "not in the graph" in response.text

    def test_rejects_a_self_connection(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")

        response = save(client, workflow_id, [trigger], [edge(trigger, trigger)])

        assert response.status_code == 422
        assert "connected to itself" in response.text

    def test_rejects_duplicate_node_ids(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)
        shared_id = str(uuid.uuid4())

        response = save(
            client,
            workflow_id,
            [node("manual_trigger", "Start", shared_id), node("log", "Log", shared_id)],
            [],
        )

        assert response.status_code == 422
        assert "same id" in response.text

    def test_rejects_a_blank_label(self, client: TestClient, registered_user: dict) -> None:
        workflow_id = new_workflow(client)

        response = save(client, workflow_id, [node("manual_trigger", "   ")], [])

        assert response.status_code == 422

    def test_another_users_workflow_cannot_be_edited(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "name": "Other", "password": "another-password"},
        )

        assert save(client, workflow_id, [], []).status_code == 404
        assert client.get(f"/api/workflows/{workflow_id}/graph").status_code == 404


class TestDuplicateCopiesGraph:
    def test_the_copy_has_its_own_nodes_and_edges(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)
        trigger = node("manual_trigger", "Start")
        logger = node("log", "Write log", message="hello")
        save(client, workflow_id, [trigger, logger], [edge(trigger, logger)])

        copy_id = client.post(f"/api/workflows/{workflow_id}/duplicate").json()["id"]
        copy_graph = client.get(f"/api/workflows/{copy_id}/graph").json()

        assert [n["label"] for n in copy_graph["nodes"]] == ["Start", "Write log"]
        assert {n["id"] for n in copy_graph["nodes"]}.isdisjoint({trigger["id"], logger["id"]})
        assert len(copy_graph["edges"]) == 1


class TestWorkflowDetail:
    def test_includes_the_webhook_endpoint_for_the_owner(
        self, client: TestClient, registered_user: dict
    ) -> None:
        workflow_id = new_workflow(client)

        detail = client.get(f"/api/workflows/{workflow_id}").json()

        assert detail["webhook_path"].startswith(f"/api/webhooks/{workflow_id}/")
        assert len(detail["webhook_token"]) >= 32

    def test_the_token_is_absent_from_the_list_view(
        self, client: TestClient, registered_user: dict
    ) -> None:
        new_workflow(client)

        item = client.get("/api/workflows").json()["items"][0]

        assert "webhook_token" not in item
