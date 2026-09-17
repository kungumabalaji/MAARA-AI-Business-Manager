"""The closed grammar calculation rules are allowed to use, and the pure

functions that execute each operation. Nothing here ever calls eval/exec, and
nothing here touches a database — it's a self-contained library over plain
Decimal values, deliberately kept that way so it's trivial to unit test.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field, ValidationError, model_validator

from calculations.errors import (
    DivisionByZeroCalculationError,
    MalformedRuleError,
    MissingDependencyError,
    UnsupportedOperationError,
)

SUPPORTED_OPERATIONS = (
    "SUM",
    "SUM_GROUP",
    "SUBTRACT",
    "MULTIPLY",
    "DIVIDE",
    "PERCENTAGE",
    "MIN",
    "MAX",
    "ROUND",
)


class Operand(BaseModel):
    """A leaf value: either a reference to a field/rule key, or a literal constant."""

    ref: str | None = None
    const: Decimal | None = None

    @model_validator(mode="after")
    def _exactly_one_of_ref_or_const(self) -> Operand:
        if (self.ref is None) == (self.const is None):
            raise ValueError("an operand must set exactly one of 'ref' or 'const'")
        return self


class SumOperands(BaseModel):
    items: list[Operand] = Field(min_length=1)


class SumGroupOperands(BaseModel):
    group: str


class BinaryOperands(BaseModel):
    left: Operand
    right: Operand


class PercentageOperands(BaseModel):
    numerator: Operand
    denominator: Operand


class MinMaxOperands(BaseModel):
    items: list[Operand] = Field(min_length=1)


class RoundOperands(BaseModel):
    value: Operand
    decimals: int = Field(ge=0, le=6)


OPERAND_SCHEMAS: dict[str, type[BaseModel]] = {
    "SUM": SumOperands,
    "SUM_GROUP": SumGroupOperands,
    "SUBTRACT": BinaryOperands,
    "MULTIPLY": BinaryOperands,
    "DIVIDE": BinaryOperands,
    "PERCENTAGE": PercentageOperands,
    "MIN": MinMaxOperands,
    "MAX": MinMaxOperands,
    "ROUND": RoundOperands,
}


def parse_operands(rule_key: str, operation: str, raw_operands: dict) -> BaseModel:
    """Validates raw_operands against the schema for `operation`.

    Raises UnsupportedOperationError for an operation outside the closed set,
    MalformedRuleError for operands that don't match that operation's shape.
    """
    if operation not in OPERAND_SCHEMAS:
        raise UnsupportedOperationError(rule_key, operation)

    try:
        return OPERAND_SCHEMAS[operation].model_validate(raw_operands)
    except ValidationError as exc:
        raise MalformedRuleError(rule_key, str(exc)) from exc


def refs_in(operands: BaseModel) -> set[str]:
    """Every field/rule key an already-parsed operand structure points at via 'ref'.

    SUM_GROUP's 'group' is deliberately excluded — group membership is resolved
    by the caller (calculations/evaluator.py), which knows the field→section map.
    """
    if isinstance(operands, SumGroupOperands):
        return set()
    if isinstance(operands, (SumOperands, MinMaxOperands)):
        return {o.ref for o in operands.items if o.ref is not None}
    if isinstance(operands, BinaryOperands):
        return {o.ref for o in (operands.left, operands.right) if o.ref is not None}
    if isinstance(operands, PercentageOperands):
        return {o.ref for o in (operands.numerator, operands.denominator) if o.ref is not None}
    if isinstance(operands, RoundOperands):
        return {operands.value.ref} if operands.value.ref is not None else set()
    raise TypeError(f"Unrecognized operand type: {type(operands)!r}")  # pragma: no cover


def _resolve(rule_key: str, operand: Operand, values: dict[str, Decimal]) -> Decimal:
    if operand.const is not None:
        return operand.const
    try:
        return values[operand.ref]  # type: ignore[index]
    except KeyError as exc:
        # validate_rules() already proved every ref resolves to a known field —
        # reaching here means the caller's raw_values dict was incomplete, not
        # that the template is broken. Callers must default every non-calculated
        # field (including ones the user left blank) to Decimal("0") beforehand.
        raise MissingDependencyError(rule_key, operand.ref) from exc  # type: ignore[arg-type]


def apply_operation(
    rule_key: str,
    operation: str,
    operands: BaseModel,
    values: dict[str, Decimal],
    group_members: dict[str, list[str]],
) -> Decimal:
    """Executes one already-validated rule against the current value pool.

    `values` holds every raw field value plus every calculated value produced
    so far, keyed by field/rule key. `group_members` maps a section key to the
    field keys it contains, for SUM_GROUP.
    """
    if operation == "SUM":
        return sum((_resolve(rule_key, o, values) for o in operands.items), Decimal("0"))

    if operation == "SUM_GROUP":
        member_keys = group_members.get(operands.group, [])
        return sum((values.get(key, Decimal("0")) for key in member_keys), Decimal("0"))

    if operation == "SUBTRACT":
        return _resolve(rule_key, operands.left, values) - _resolve(rule_key, operands.right, values)

    if operation == "MULTIPLY":
        return _resolve(rule_key, operands.left, values) * _resolve(rule_key, operands.right, values)

    if operation == "DIVIDE":
        divisor = _resolve(rule_key, operands.right, values)
        if divisor == 0:
            raise DivisionByZeroCalculationError(rule_key)
        return _resolve(rule_key, operands.left, values) / divisor

    if operation == "PERCENTAGE":
        denominator = _resolve(rule_key, operands.denominator, values)
        if denominator == 0:
            raise DivisionByZeroCalculationError(rule_key)
        return (_resolve(rule_key, operands.numerator, values) / denominator) * Decimal("100")

    if operation == "MIN":
        return min(_resolve(rule_key, o, values) for o in operands.items)

    if operation == "MAX":
        return max(_resolve(rule_key, o, values) for o in operands.items)

    if operation == "ROUND":
        value = _resolve(rule_key, operands.value, values)
        quantum = Decimal("1").scaleb(-operands.decimals)
        return value.quantize(quantum, rounding=ROUND_HALF_UP)

    raise UnsupportedOperationError(rule_key, operation)  # pragma: no cover — parse_operands already gated this
