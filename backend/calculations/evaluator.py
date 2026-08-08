"""The two entry points everything else calls:

validate_rules() — run once, when a template version is published. Parses
every rule, checks every reference resolves, detects cycles, and returns the
rules in a safe evaluation order. A version that fails this can't be published.

evaluate() — run every time a report is submitted. Takes the order
validate_rules() already proved safe and actually computes the values. Never
re-derives the order itself, so a hot path (report submission) never re-pays
the cost of the checks a template author already passed once.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from calculations.graph import topological_order
from calculations.registry import apply_operation, parse_operands


@dataclass(frozen=True)
class FieldSpec:
    key: str
    section_key: str
    is_calculated: bool


@dataclass(frozen=True)
class RuleSpec:
    key: str
    operation: str
    operands: dict


@dataclass(frozen=True)
class OrderedRule:
    key: str
    operation: str
    operands: object  # a parsed model from calculations.registry


def _field_keys_by_section(fields: list[FieldSpec]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for field in fields:
        grouped.setdefault(field.section_key, set()).add(field.key)
    return grouped


def validate_rules(fields: list[FieldSpec], rules: list[RuleSpec]) -> list[OrderedRule]:
    all_field_keys = {f.key for f in fields}
    field_keys_by_section = _field_keys_by_section(fields)

    parsed = [(rule.key, rule.operation, parse_operands(rule.key, rule.operation, rule.operands)) for rule in rules]

    order = topological_order(parsed, all_field_keys, field_keys_by_section)

    parsed_by_key = {key: (operation, operands) for key, operation, operands in parsed}
    return [
        OrderedRule(key=key, operation=parsed_by_key[key][0], operands=parsed_by_key[key][1]) for key in order
    ]


def evaluate(
    fields: list[FieldSpec],
    ordered_rules: list[OrderedRule],
    raw_values: dict[str, Decimal],
) -> dict[str, Decimal]:
    """raw_values must contain an entry for every non-calculated field — default

    any the user left blank to Decimal("0") before calling this, don't omit them.
    """
    field_keys_by_section = {
        section: list(keys) for section, keys in _field_keys_by_section(fields).items()
    }

    values: dict[str, Decimal] = dict(raw_values)
    for rule in ordered_rules:
        values[rule.key] = apply_operation(rule.key, rule.operation, rule.operands, values, field_keys_by_section)

    return values
