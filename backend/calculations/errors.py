"""Every failure mode the calculation engine can hit, each as its own type so

callers (the template publish endpoint, the report submit endpoint) can tell
them apart and return the right HTTP status and message instead of a generic 500.
"""


class CalculationError(Exception):
    """Base class for every calculation-engine failure."""


class UnsupportedOperationError(CalculationError):
    def __init__(self, rule_key: str, operation: str) -> None:
        self.rule_key = rule_key
        self.operation = operation
        super().__init__(f"Rule '{rule_key}' uses unsupported operation '{operation}'.")


class MalformedRuleError(CalculationError):
    def __init__(self, rule_key: str, reason: str) -> None:
        self.rule_key = rule_key
        self.reason = reason
        super().__init__(f"Rule '{rule_key}' is malformed: {reason}")


class MissingDependencyError(CalculationError):
    def __init__(self, rule_key: str, missing_ref: str) -> None:
        self.rule_key = rule_key
        self.missing_ref = missing_ref
        super().__init__(f"Rule '{rule_key}' references unknown field or rule '{missing_ref}'.")


class CircularDependencyError(CalculationError):
    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__("Circular dependency in calculation rules: " + " -> ".join(cycle))


class DivisionByZeroCalculationError(CalculationError):
    def __init__(self, rule_key: str) -> None:
        self.rule_key = rule_key
        super().__init__(f"Rule '{rule_key}' divided by zero.")
