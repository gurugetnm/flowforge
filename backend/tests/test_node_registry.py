"""The node registry and the catalog it exposes."""

import pytest
from fastapi.testclient import TestClient

import app.nodes as nodes
from app.nodes import NodeConfigError, UnknownNodeTypeError, get_executor

EXPECTED_TYPES = {
    "manual_trigger",
    "webhook_trigger",
    "http_request",
    "json_transform",
    "delay",
    "log",
    "condition",
    "switch",
    "set_variable",
    "json_input",
}


class TestRegistry:
    def test_every_planned_node_type_is_registered(self) -> None:
        assert {executor.node_type for executor in nodes.all_executors()} == EXPECTED_TYPES

    def test_unknown_type_raises_a_descriptive_error(self) -> None:
        with pytest.raises(UnknownNodeTypeError, match="Unknown node type 'nope'"):
            get_executor("nope")

    def test_triggers_do_not_accept_input(self) -> None:
        for node_type in nodes.trigger_types():
            assert get_executor(node_type).accepts_input is False

    def test_every_executor_declares_at_least_one_output(self) -> None:
        for executor in nodes.all_executors():
            assert executor.outputs, f"{executor.node_type} declares no outputs"

    def test_output_keys_are_unique_per_node(self) -> None:
        for executor in nodes.all_executors():
            keys = [output.key for output in executor.outputs]
            assert len(keys) == len(set(keys))


class TestConfigValidation:
    def test_missing_required_field_names_the_field(self) -> None:
        with pytest.raises(NodeConfigError) as raised:
            get_executor("http_request").validate_config({"method": "GET"})

        assert "url" in raised.value.field_errors
        assert raised.value.field_errors["url"] == ["This field is required."]

    def test_defaults_are_applied(self) -> None:
        config = get_executor("http_request").validate_config({"url": "https://example.com"})

        assert config.method == "GET"
        assert config.timeout_seconds == 10.0

    def test_rejects_a_non_http_url(self) -> None:
        with pytest.raises(NodeConfigError, match="http"):
            get_executor("http_request").validate_config({"url": "file:///etc/passwd"})

    def test_accepts_a_url_built_from_an_expression(self) -> None:
        config = get_executor("http_request").validate_config({"url": "{{ vars.endpoint }}"})

        assert config.url == "{{ vars.endpoint }}"

    def test_rejects_invalid_json_in_a_transform(self) -> None:
        with pytest.raises(NodeConfigError, match="not valid JSON"):
            get_executor("json_transform").validate_config({"template": "{oops}"})

    def test_rejects_a_variable_name_that_is_not_an_identifier(self) -> None:
        with pytest.raises(NodeConfigError):
            get_executor("set_variable").validate_config({"name": "not a name", "value": "x"})

    def test_rejects_duplicate_switch_cases(self) -> None:
        with pytest.raises(NodeConfigError, match="distinct"):
            get_executor("switch").validate_config({"value": "{{ input.x }}", "cases": ["a", "a"]})


class TestSwitchOutputs:
    def test_one_handle_per_case_plus_a_default(self) -> None:
        outputs = get_executor("switch").outputs_for({"cases": ["opened", "closed"]})

        assert [output.key for output in outputs] == ["case:0", "case:1", "default"]

    def test_a_switch_with_no_cases_still_has_a_default(self) -> None:
        assert [o.key for o in get_executor("switch").outputs_for({})] == ["default"]


class TestCatalogEndpoint:
    def test_describes_every_node_type(self, client: TestClient, registered_user: dict) -> None:
        response = client.get("/api/node-types")

        assert response.status_code == 200
        assert {item["type"] for item in response.json()} == EXPECTED_TYPES

    def test_describes_the_fields_the_editor_must_render(
        self, client: TestClient, registered_user: dict
    ) -> None:
        catalog = {item["type"]: item for item in client.get("/api/node-types").json()}
        http_fields = {field["key"]: field for field in catalog["http_request"]["fields"]}

        assert http_fields["url"]["required"] is True
        assert http_fields["url"]["supports_expressions"] is True
        assert http_fields["method"]["control"] == "select"
        assert {o["value"] for o in http_fields["method"]["options"]} == {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }
        # The body only applies to methods that carry one.
        assert http_fields["body"]["depends_on"] == "method"
        assert "GET" not in http_fields["body"]["depends_on_values"]

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get("/api/node-types").status_code == 401
