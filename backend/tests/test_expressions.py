"""The `{{ }}` expression resolver."""

import pytest

from app.nodes.expressions import (
    ExpressionError,
    contains_expression,
    render_string,
    render_value,
    resolve_path,
)

CONTEXT = {
    "input": {"user": {"id": 7, "email": "dev@example.com"}, "tags": ["alpha", "beta"]},
    "vars": {"token": "secret-value", "count": 3, "enabled": True},
    "trigger": {"body": {"action": "opened"}},
}


class TestResolvePath:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("input.user.id", 7),
            ("input.user.email", "dev@example.com"),
            ("input.tags[0]", "alpha"),
            ("vars.enabled", True),
            ("trigger.body.action", "opened"),
            ("input.user", {"id": 7, "email": "dev@example.com"}),
        ],
    )
    def test_resolves_supported_paths(self, path: str, expected: object) -> None:
        assert resolve_path(path, CONTEXT) == expected

    @pytest.mark.parametrize(
        "path",
        ["input.missing", "input.user.name", "input.tags[9]", "input.user.id.deeper"],
    )
    def test_reports_what_is_missing(self, path: str) -> None:
        with pytest.raises(ExpressionError, match="is not available"):
            resolve_path(path, CONTEXT)


class TestRenderString:
    def test_whole_value_expression_keeps_its_type(self) -> None:
        assert render_string("{{ input.user.id }}", CONTEXT) == 7
        assert render_string("  {{ vars.enabled }}  ", CONTEXT) is True
        assert render_string("{{ input.user }}", CONTEXT) == CONTEXT["input"]["user"]  # type: ignore[index]

    def test_embedded_expressions_interpolate_as_text(self) -> None:
        result = render_string("https://api.example.com/users/{{ input.user.id }}", CONTEXT)

        assert result == "https://api.example.com/users/7"

    def test_booleans_interpolate_as_json_literals(self) -> None:
        assert render_string("enabled={{ vars.enabled }}", CONTEXT) == "enabled=true"

    def test_text_without_expressions_is_returned_unchanged(self) -> None:
        assert render_string("plain text", CONTEXT) == "plain text"

    def test_does_not_evaluate_code(self) -> None:
        # The resolver only walks properties, so this is a missing path, not code.
        with pytest.raises(ExpressionError):
            render_string("{{ __import__ }}", CONTEXT)


class TestRenderValue:
    def test_walks_nested_structures(self) -> None:
        template = {
            "headers": {"Authorization": "Bearer {{ vars.token }}"},
            "ids": [1, "{{ input.user.id }}"],
            "flag": True,
        }

        assert render_value(template, CONTEXT) == {
            "headers": {"Authorization": "Bearer secret-value"},
            "ids": [1, 7],
            "flag": True,
        }

    def test_non_string_leaves_are_untouched(self) -> None:
        assert render_value({"n": 5, "b": False, "nothing": None}, CONTEXT) == {
            "n": 5,
            "b": False,
            "nothing": None,
        }


class TestContainsExpression:
    def test_detects_expressions_at_any_depth(self) -> None:
        assert contains_expression({"a": ["x", {"b": "{{ vars.token }}"}]})
        assert not contains_expression({"a": ["x", {"b": "plain"}]})
