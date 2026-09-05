"""Logic nodes: nodes that choose which branch the run continues down."""

from typing import Any, Literal

from pydantic import BaseModel, field_validator

from app.nodes.base import (
    Control,
    NodeCategory,
    NodeContext,
    NodeExecutor,
    NodeResult,
    Option,
    Output,
)
from app.nodes.fields import config_field, describe
from app.nodes.registry import register

MAX_SWITCH_CASES = 10

Operator = Literal[
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "less_than",
    "is_empty",
    "is_not_empty",
    "is_true",
]

OPERATOR_LABELS: tuple[tuple[str, str], ...] = (
    ("equals", "equals"),
    ("not_equals", "does not equal"),
    ("contains", "contains"),
    ("greater_than", "is greater than"),
    ("less_than", "is less than"),
    ("is_empty", "is empty"),
    ("is_not_empty", "is not empty"),
    ("is_true", "is true"),
)

#: Operators that compare against a second value.
BINARY_OPERATORS = frozenset({"equals", "not_equals", "contains", "greater_than", "less_than"})


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def evaluate(operator: str, left: Any, right: Any) -> bool:
    """Apply ``operator`` to the two operands.

    Comparisons prefer numbers when both sides look numeric, and otherwise
    fall back to comparing their string forms, which is what a workflow author
    expects when a value arrives from JSON as `"42"`.
    """
    if operator == "is_empty":
        return left in (None, "", [], {}) or left is False
    if operator == "is_not_empty":
        return not (left in (None, "", [], {}) or left is False)
    if operator == "is_true":
        return left is True or str(left).strip().lower() in {"true", "1", "yes"}

    left_number, right_number = _coerce_number(left), _coerce_number(right)
    both_numeric = left_number is not None and right_number is not None

    if operator == "equals":
        if both_numeric:
            return left_number == right_number
        return left == right or str(left) == str(right)
    if operator == "not_equals":
        return not evaluate("equals", left, right)
    if operator == "contains":
        if isinstance(left, list | tuple | dict):
            return right in left or str(right) in [str(item) for item in left]
        return str(right) in str(left)
    if operator == "greater_than":
        if both_numeric:
            return left_number > right_number  # type: ignore[operator]
        return str(left) > str(right)
    if operator == "less_than":
        if both_numeric:
            return left_number < right_number  # type: ignore[operator]
        return str(left) < str(right)

    raise ValueError(f"Unsupported operator {operator!r}.")


class ConditionConfig(BaseModel):
    left: str = config_field(
        label="Value",
        control=Control.TEXT,
        help_text="Usually an expression, for example {{ input.status_code }}.",
        placeholder="{{ input.status_code }}",
        supports_expressions=True,
        min_length=1,
    )
    operator: Operator = config_field(
        label="Condition",
        control=Control.SELECT,
        default="equals",
        options=tuple(Option(value, label) for value, label in OPERATOR_LABELS),
    )
    right: str = config_field(
        label="Compare with",
        control=Control.TEXT,
        default="",
        supports_expressions=True,
        depends_on="operator",
        depends_on_values=tuple(sorted(BINARY_OPERATORS)),
    )


@register
class ConditionExecutor(NodeExecutor[ConditionConfig]):
    """Routes the run down the true or the false branch."""

    node_type = "condition"
    name = "Condition"
    category = NodeCategory.LOGIC
    description = "Sends the run down one of two branches based on a comparison."
    config_model = ConditionConfig
    fields = describe(ConditionConfig)
    outputs = (
        Output("true", "True", "Taken when the condition holds."),
        Output("false", "False", "Taken when it does not."),
    )

    async def execute(self, config: ConditionConfig, context: NodeContext) -> NodeResult:
        left = context.render(config.left)
        right = context.render(config.right) if config.operator in BINARY_OPERATORS else None
        matched = evaluate(config.operator, left, right)

        context.log(f"Condition evaluated to {matched}")
        return NodeResult(
            output={**context.input, "matched": matched},
            branches=("true",) if matched else ("false",),
        )


class SwitchConfig(BaseModel):
    value: str = config_field(
        label="Value",
        control=Control.TEXT,
        help_text="The value each case is compared against.",
        placeholder="{{ input.status }}",
        supports_expressions=True,
        min_length=1,
    )
    cases: list[str] = config_field(
        label="Cases",
        control=Control.CODE,
        default_factory=list,
        help_text=(
            "One value per line. The run continues down the branch of the "
            "first match, or down Default if nothing matches."
        ),
    )

    @field_validator("cases")
    @classmethod
    def _limit_cases(cls, value: list[str]) -> list[str]:
        cases = [case.strip() for case in value if case.strip()]
        if len(cases) > MAX_SWITCH_CASES:
            raise ValueError(f"A switch supports at most {MAX_SWITCH_CASES} cases.")
        if len(set(cases)) != len(cases):
            raise ValueError("Each case must be distinct.")
        return cases


@register
class SwitchExecutor(NodeExecutor[SwitchConfig]):
    """Routes the run down the branch matching the first equal case."""

    node_type = "switch"
    name = "Switch"
    category = NodeCategory.LOGIC
    description = "Routes the run down the branch matching a value."
    config_model = SwitchConfig
    fields = describe(SwitchConfig)
    outputs = (Output("default", "Default", "Taken when no case matches."),)

    def outputs_for(self, configuration: dict[str, Any]) -> tuple[Output, ...]:
        """The handles this node exposes, which depend on its cases."""
        cases = configuration.get("cases") or []
        case_outputs = tuple(
            Output(f"case:{index}", str(case))
            for index, case in enumerate(cases)
            if str(case).strip()
        )
        return (*case_outputs, *self.outputs)

    async def execute(self, config: SwitchConfig, context: NodeContext) -> NodeResult:
        value = context.render(config.value)

        for index, case in enumerate(config.cases):
            if evaluate("equals", value, case):
                context.log(f"Matched case {case!r}")
                return NodeResult(
                    output={**context.input, "matched_case": case},
                    branches=(f"case:{index}",),
                )

        context.log("No case matched, taking the default branch")
        return NodeResult(
            output={**context.input, "matched_case": None},
            branches=("default",),
        )
