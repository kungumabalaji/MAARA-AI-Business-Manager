from decimal import Decimal

import pytest

from calculations.errors import (
    CircularDependencyError,
    DivisionByZeroCalculationError,
    MalformedRuleError,
    MissingDependencyError,
    UnsupportedOperationError,
)
from calculations.evaluator import FieldSpec, RuleSpec, evaluate, validate_rules


def field(key: str, section: str, is_calculated: bool = False) -> FieldSpec:
    return FieldSpec(key=key, section_key=section, is_calculated=is_calculated)


def rule(key: str, operation: str, operands: dict) -> RuleSpec:
    return RuleSpec(key=key, operation=operation, operands=operands)


# ---------------------------------------------------------------------------
# A realistic end-to-end template, shaped like Dosa n Chutney's actual report:
# card/cash/uber_eats sales -> total_sales; rent/wages expenses -> total_expenses;
# operating_profit = total_sales - total_expenses; margin = profit% of sales,
# rounded. Exercises SUM_GROUP, SUBTRACT, PERCENTAGE, and nested ROUND together.
# ---------------------------------------------------------------------------

DOSA_FIELDS = [
    field("card_sales", "sales"),
    field("cash_sales", "sales"),
    field("uber_eats", "sales"),
    field("total_sales", "sales", is_calculated=True),
    field("rent", "expenses"),
    field("staff_wages", "expenses"),
    field("total_expenses", "expenses", is_calculated=True),
    field("operating_profit", "summary", is_calculated=True),
    field("profit_margin_pct", "summary", is_calculated=True),
]

DOSA_RULES = [
    rule("total_sales", "SUM_GROUP", {"group": "sales"}),
    rule("total_expenses", "SUM_GROUP", {"group": "expenses"}),
    rule(
        "operating_profit",
        "SUBTRACT",
        {"left": {"ref": "total_sales"}, "right": {"ref": "total_expenses"}},
    ),
    rule(
        "profit_margin_pct",
        "ROUND",
        {
            "value": {
                "ref": "profit_margin_raw",
            },
            "decimals": 1,
        },
    ),
]


def test_end_to_end_dosa_n_chutney_shaped_template():
    # profit_margin_pct rounds a PERCENTAGE rule's output — add that rule too,
    # proving nested calculated-rule-depends-on-calculated-rule chains work.
    rules = DOSA_RULES[:-1] + [
        rule(
            "profit_margin_raw",
            "PERCENTAGE",
            {"numerator": {"ref": "operating_profit"}, "denominator": {"ref": "total_sales"}},
        ),
        DOSA_RULES[-1],
    ]
    fields = DOSA_FIELDS + [field("profit_margin_raw", "summary", is_calculated=True)]

    ordered = validate_rules(fields, rules)
    raw_values = {
        "card_sales": Decimal("1842.50"),
        "cash_sales": Decimal("694.00"),
        "uber_eats": Decimal("450.25"),
        "rent": Decimal("138.87"),
        "staff_wages": Decimal("400.00"),
    }

    result = evaluate(fields, ordered, raw_values)

    assert result["total_sales"] == Decimal("2986.75")
    assert result["total_expenses"] == Decimal("538.87")
    assert result["operating_profit"] == Decimal("2447.88")
    # PERCENTAGE division precision, then ROUND to 1dp — proves the pipeline,
    # not just a single operation, is Decimal-exact.
    assert result["profit_margin_pct"] == Decimal("82.0")


# ---------------------------------------------------------------------------
# Each operation, individually
# ---------------------------------------------------------------------------


def test_sum():
    fields = [field("a", "g"), field("b", "g"), field("total", "g", True)]
    rules = [rule("total", "SUM", {"items": [{"ref": "a"}, {"ref": "b"}, {"const": 5}]})]
    ordered = validate_rules(fields, rules)
    result = evaluate(fields, ordered, {"a": Decimal("10"), "b": Decimal("2.5")})
    assert result["total"] == Decimal("17.5")


def test_sum_group_ignores_fields_outside_the_group():
    fields = [field("a", "sales"), field("b", "sales"), field("c", "expenses"), field("total", "sales", True)]
    rules = [rule("total", "SUM_GROUP", {"group": "sales"})]
    ordered = validate_rules(fields, rules)
    result = evaluate(fields, ordered, {"a": Decimal("1"), "b": Decimal("2"), "c": Decimal("999")})
    assert result["total"] == Decimal("3")


def test_sum_group_treats_missing_optional_field_as_zero():
    fields = [field("a", "sales"), field("b", "sales"), field("total", "sales", True)]
    rules = [rule("total", "SUM_GROUP", {"group": "sales"})]
    ordered = validate_rules(fields, rules)
    # "b" was left blank by the user and never made it into raw_values.
    result = evaluate(fields, ordered, {"a": Decimal("4")})
    assert result["total"] == Decimal("4")


def test_subtract_multiply_divide():
    fields = [field("a", "g"), field("b", "g"), field("x", "g", True), field("y", "g", True), field("z", "g", True)]
    rules = [
        rule("x", "SUBTRACT", {"left": {"ref": "a"}, "right": {"ref": "b"}}),
        rule("y", "MULTIPLY", {"left": {"ref": "a"}, "right": {"const": 2}}),
        rule("z", "DIVIDE", {"left": {"ref": "a"}, "right": {"ref": "b"}}),
    ]
    ordered = validate_rules(fields, rules)
    result = evaluate(fields, ordered, {"a": Decimal("10"), "b": Decimal("4")})
    assert result["x"] == Decimal("6")
    assert result["y"] == Decimal("20")
    assert result["z"] == Decimal("2.5")


def test_min_max():
    fields = [field("a", "g"), field("b", "g"), field("c", "g"), field("lo", "g", True), field("hi", "g", True)]
    rules = [
        rule("lo", "MIN", {"items": [{"ref": "a"}, {"ref": "b"}, {"ref": "c"}]}),
        rule("hi", "MAX", {"items": [{"ref": "a"}, {"ref": "b"}, {"ref": "c"}]}),
    ]
    ordered = validate_rules(fields, rules)
    result = evaluate(fields, ordered, {"a": Decimal("3"), "b": Decimal("9"), "c": Decimal("-1")})
    assert result["lo"] == Decimal("-1")
    assert result["hi"] == Decimal("9")


def test_round_half_up():
    fields = [field("a", "g"), field("rounded", "g", True)]
    rules = [rule("rounded", "ROUND", {"value": {"ref": "a"}, "decimals": 2})]
    ordered = validate_rules(fields, rules)
    result = evaluate(fields, ordered, {"a": Decimal("1.005")})
    assert result["rounded"] == Decimal("1.01")  # half-up, not banker's rounding


# ---------------------------------------------------------------------------
# Decimal precision — the whole reason this isn't float
# ---------------------------------------------------------------------------


def test_decimal_precision_avoids_float_drift():
    fields = [field("a", "g"), field("b", "g"), field("c", "g"), field("total", "g", True)]
    rules = [rule("total", "SUM", {"items": [{"ref": "a"}, {"ref": "b"}, {"ref": "c"}]})]
    ordered = validate_rules(fields, rules)
    # 0.1 + 0.2 + 0.3 != 0.6 in binary float; must be exact in Decimal.
    result = evaluate(fields, ordered, {"a": Decimal("0.1"), "b": Decimal("0.2"), "c": Decimal("0.3")})
    assert result["total"] == Decimal("0.6")


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_unsupported_operation_rejected():
    fields = [field("a", "g"), field("total", "g", True)]
    rules = [rule("total", "AVERAGE", {"items": [{"ref": "a"}]})]
    with pytest.raises(UnsupportedOperationError):
        validate_rules(fields, rules)


def test_malformed_operands_rejected():
    fields = [field("a", "g"), field("total", "g", True)]
    # SUBTRACT requires left/right, not "items".
    rules = [rule("total", "SUBTRACT", {"items": [{"ref": "a"}]})]
    with pytest.raises(MalformedRuleError):
        validate_rules(fields, rules)


def test_operand_with_both_ref_and_const_rejected():
    fields = [field("a", "g"), field("total", "g", True)]
    rules = [rule("total", "SUM", {"items": [{"ref": "a", "const": 1}]})]
    with pytest.raises(MalformedRuleError):
        validate_rules(fields, rules)


def test_missing_field_reference_rejected():
    fields = [field("a", "g"), field("total", "g", True)]
    rules = [rule("total", "SUM", {"items": [{"ref": "does_not_exist"}]})]
    with pytest.raises(MissingDependencyError):
        validate_rules(fields, rules)


def test_missing_sum_group_section_rejected():
    fields = [field("a", "g"), field("total", "g", True)]
    rules = [rule("total", "SUM_GROUP", {"group": "no_such_section"})]
    with pytest.raises(MissingDependencyError):
        validate_rules(fields, rules)


def test_direct_circular_dependency_rejected():
    fields = [field("x", "g", True), field("y", "g", True)]
    rules = [
        rule("x", "SUBTRACT", {"left": {"ref": "y"}, "right": {"const": 1}}),
        rule("y", "SUBTRACT", {"left": {"ref": "x"}, "right": {"const": 1}}),
    ]
    with pytest.raises(CircularDependencyError):
        validate_rules(fields, rules)


def test_self_reference_is_a_circular_dependency():
    fields = [field("x", "g", True)]
    rules = [rule("x", "SUBTRACT", {"left": {"ref": "x"}, "right": {"const": 1}})]
    with pytest.raises(CircularDependencyError):
        validate_rules(fields, rules)


def test_calculated_field_summing_its_own_section_is_not_a_false_cycle():
    # "total" lives in "sales" (the section it sums) — the normal shape for a
    # section subtotal. Must NOT be treated as depending on itself.
    fields = [field("a", "sales"), field("total", "sales", True)]
    rules = [rule("total", "SUM_GROUP", {"group": "sales"})]
    ordered = validate_rules(fields, rules)
    result = evaluate(fields, ordered, {"a": Decimal("5")})
    assert result["total"] == Decimal("5")


def test_group_membership_across_two_rules_can_create_a_real_cycle():
    # total_x (section "x") SUM_GROUPs "y", which contains total_y (section "y").
    # total_y SUM_GROUPs "x", which contains total_x. Two distinct rules, each
    # depending on the other purely via where their output field is grouped.
    fields = [
        field("a", "y"),
        field("total_x", "x", True),
        field("total_y", "y", True),
    ]
    rules = [
        rule("total_x", "SUM_GROUP", {"group": "y"}),
        rule("total_y", "SUM_GROUP", {"group": "x"}),
    ]
    with pytest.raises(CircularDependencyError):
        validate_rules(fields, rules)


def test_divide_by_zero_rejected_at_evaluate_time():
    fields = [field("a", "g"), field("b", "g"), field("result", "g", True)]
    rules = [rule("result", "DIVIDE", {"left": {"ref": "a"}, "right": {"ref": "b"}})]
    ordered = validate_rules(fields, rules)
    with pytest.raises(DivisionByZeroCalculationError):
        evaluate(fields, ordered, {"a": Decimal("10"), "b": Decimal("0")})


def test_percentage_by_zero_rejected():
    fields = [field("a", "g"), field("b", "g"), field("result", "g", True)]
    rules = [rule("result", "PERCENTAGE", {"numerator": {"ref": "a"}, "denominator": {"ref": "b"}})]
    ordered = validate_rules(fields, rules)
    with pytest.raises(DivisionByZeroCalculationError):
        evaluate(fields, ordered, {"a": Decimal("10"), "b": Decimal("0")})


def test_missing_raw_value_at_evaluate_time_raises_not_keyerror():
    # Contract: caller must default every non-calculated field before calling
    # evaluate(). If they don't, we still want a typed error, not a bare KeyError.
    fields = [field("a", "g"), field("result", "g", True)]
    rules = [rule("result", "SUM", {"items": [{"ref": "a"}]})]
    ordered = validate_rules(fields, rules)
    with pytest.raises(MissingDependencyError):
        evaluate(fields, ordered, {})
