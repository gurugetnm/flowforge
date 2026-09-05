"""A deliberately small expression language for node configuration.

Configuration values may reference run-time data with ``{{ path }}``:

    https://api.example.com/users/{{ input.user.id }}
    {{ vars.api_token }}
    {{ trigger.body.email }}

Only property and index lookups are supported. There is no arithmetic, no
function calls and no ``eval`` anywhere in this module, so a workflow author
cannot execute arbitrary code on the server.
"""

import json
import re
from typing import Any

#: Matches ``{{ some.path[0] }}`` and captures the path.
EXPRESSION_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][\w.\[\]\-]*)\s*\}\}")
#: A whole value that is exactly one expression keeps its original type.
WHOLE_VALUE_PATTERN = re.compile(r"^\s*\{\{\s*([A-Za-z_][\w.\[\]\-]*)\s*\}\}\s*$")

_SEGMENT_PATTERN = re.compile(r"[^.\[\]]+")

MISSING = object()


class ExpressionError(ValueError):
    """Raised when an expression refers to something that does not exist."""


def resolve_path(path: str, context: dict[str, Any]) -> Any:
    """Look up a dotted path such as ``input.items[0].name`` in ``context``."""
    current: Any = context

    for segment in _SEGMENT_PATTERN.findall(path):
        if isinstance(current, dict):
            if segment not in current:
                raise ExpressionError(f"{path!r} is not available: no value named {segment!r}.")
            current = current[segment]
        elif isinstance(current, list | tuple):
            try:
                current = current[int(segment)]
            except ValueError:
                raise ExpressionError(
                    f"{path!r} is not available: {segment!r} is not a list index."
                ) from None
            except IndexError:
                raise ExpressionError(
                    f"{path!r} is not available: index {segment} is out of range."
                ) from None
        else:
            raise ExpressionError(f"{path!r} is not available: {segment!r} has no properties.")

    return current


def render_string(template: str, context: dict[str, Any]) -> Any:
    """Resolve every expression in ``template``.

    A string that is exactly one expression evaluates to the referenced value
    with its type intact; otherwise each expression is interpolated as text.
    """
    whole = WHOLE_VALUE_PATTERN.match(template)
    if whole:
        return resolve_path(whole.group(1), context)

    def substitute(match: re.Match[str]) -> str:
        value = resolve_path(match.group(1), context)
        return value if isinstance(value, str) else _to_text(value)

    return EXPRESSION_PATTERN.sub(substitute, template)


def render_value(value: Any, context: dict[str, Any]) -> Any:
    """Recursively resolve expressions inside strings, lists and dicts."""
    if isinstance(value, str):
        return render_string(value, context)
    if isinstance(value, list):
        return [render_value(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render_value(item, context) for key, item in value.items()}
    return value


def contains_expression(value: Any) -> bool:
    """True when ``value`` references run-time data anywhere inside it."""
    if isinstance(value, str):
        return bool(EXPRESSION_PATTERN.search(value))
    if isinstance(value, list):
        return any(contains_expression(item) for item in value)
    if isinstance(value, dict):
        return any(contains_expression(item) for item in value.values())
    return False


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, separators=(",", ":"), default=str)
