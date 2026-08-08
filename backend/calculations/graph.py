"""Dependency ordering for a template version's calculation rules.

A rule can depend on another rule two ways: directly (its operands `ref` the
other rule's key) or indirectly (it SUM_GROUPs a section that another rule's
output field belongs to). Both count for ordering purposes; only the direct
kind counts as a "reference" for missing-dependency checking, since a
SUM_GROUP is valid even over a section with zero calculated fields in it.
"""

from __future__ import annotations

from calculations.errors import CircularDependencyError, MissingDependencyError
from calculations.registry import SumGroupOperands, refs_in


def _dependencies_of(
    rule_key: str,
    operation: str,
    parsed_operands: object,
    rule_keys: set[str],
    field_keys_by_section: dict[str, set[str]],
) -> set[str]:
    if operation == "SUM_GROUP":
        assert isinstance(parsed_operands, SumGroupOperands)
        members = field_keys_by_section.get(parsed_operands.group, set())
        # A rule's own output commonly lives in the same section it sums (e.g.
        # "Total Sales" is conceptually part of the sales section) — that's not
        # a real dependency, it's just where the field is grouped for display.
        return (members & rule_keys) - {rule_key}
    return refs_in(parsed_operands) & rule_keys


def topological_order(
    parsed_rules: list[tuple[str, str, object]],
    all_field_keys: set[str],
    field_keys_by_section: dict[str, set[str]],
) -> list[str]:
    """parsed_rules: (key, operation, parsed_operands) triples, already validated

    by registry.parse_operands(). Returns rule keys in a safe evaluation order.

    Raises MissingDependencyError if a rule references a key nothing defines,
    or a SUM_GROUP references a section that doesn't exist. Raises
    CircularDependencyError if the rules can't be linearly ordered.
    """
    rule_keys = {key for key, _, _ in parsed_rules}

    for key, operation, parsed in parsed_rules:
        if operation == "SUM_GROUP":
            assert isinstance(parsed, SumGroupOperands)
            if parsed.group not in field_keys_by_section:
                raise MissingDependencyError(key, parsed.group)
            continue
        for ref in refs_in(parsed):
            if ref not in all_field_keys:
                raise MissingDependencyError(key, ref)

    dependencies = {
        key: _dependencies_of(key, operation, parsed, rule_keys, field_keys_by_section)
        for key, operation, parsed in parsed_rules
    }

    ordered: list[str] = []
    state: dict[str, str] = {}  # key -> "visiting" | "done"
    path: list[str] = []

    def visit(key: str) -> None:
        current = state.get(key)
        if current == "done":
            return
        if current == "visiting":
            cycle_start = path.index(key)
            raise CircularDependencyError(path[cycle_start:] + [key])

        state[key] = "visiting"
        path.append(key)
        for dependency in dependencies[key]:
            visit(dependency)
        path.pop()
        state[key] = "done"
        ordered.append(key)

    for key in dependencies:
        visit(key)

    return ordered
