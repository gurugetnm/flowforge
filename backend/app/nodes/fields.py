"""Helpers for declaring a node's configuration fields.

`config_field` attaches editor metadata to a Pydantic field so the model stays
the single source of truth: it validates the value *and* describes the input
the editor should render for it.
"""

from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from app.nodes.base import Control, FieldSpec, Option

UI_KEY = "ui"


def config_field(
    *,
    label: str,
    control: Control,
    default: Any = ...,
    help_text: str = "",
    placeholder: str = "",
    options: tuple[Option, ...] = (),
    supports_expressions: bool = False,
    depends_on: str | None = None,
    depends_on_values: tuple[str, ...] = (),
    **field_kwargs: Any,
) -> Any:
    """Declare a configuration field together with how it is edited."""
    from pydantic import Field

    return Field(
        default,
        json_schema_extra={
            UI_KEY: {
                "label": label,
                "control": control.value,
                "help_text": help_text,
                "placeholder": placeholder,
                "options": [{"value": o.value, "label": o.label} for o in options],
                "supports_expressions": supports_expressions,
                "depends_on": depends_on,
                "depends_on_values": list(depends_on_values),
            }
        },
        **field_kwargs,
    )


def describe(model: type[BaseModel]) -> tuple[FieldSpec, ...]:
    """Build the editor field specs declared on a configuration model."""
    specs: list[FieldSpec] = []

    for key, info in model.model_fields.items():
        ui = _ui_metadata(info)
        if ui is None:
            continue
        specs.append(
            FieldSpec(
                key=key,
                label=str(ui["label"]),
                control=Control(ui["control"]),
                required=info.is_required(),
                default=None if info.is_required() else info.get_default(call_default_factory=True),
                help_text=str(ui.get("help_text", "")),
                placeholder=str(ui.get("placeholder", "")),
                options=tuple(
                    Option(value=str(o["value"]), label=str(o["label"]))
                    for o in ui.get("options", [])
                ),
                supports_expressions=bool(ui.get("supports_expressions", False)),
                depends_on=ui.get("depends_on"),
                depends_on_values=tuple(ui.get("depends_on_values", [])),
            )
        )

    return tuple(specs)


def _ui_metadata(info: FieldInfo) -> dict[str, Any] | None:
    extra = info.json_schema_extra
    if isinstance(extra, dict) and isinstance(extra.get(UI_KEY), dict):
        return extra[UI_KEY]  # type: ignore[return-value]
    return None
