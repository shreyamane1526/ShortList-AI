"""Validation pipeline for trained ranking models.

IMPORTANT:
- This module is a strict refactor container.
- It must preserve existing validation semantics (thresholds/conditions)
  currently implemented in `agents/ranking_agent/retrain.py`.

No ML behavior changes are introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    issues: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
        }


def build_validation_result(metrics: Dict[str, Any]) -> ValidationResult:
    """Preserve existing retrain.py semantics.

    Existing thresholds/logic in retrain.py:
    - accuracy below 0.50 (only if evaluation_size >= 5)
    - fairness_score below 0.70
    - drift_score below 0.60
    """
    issues: list[str] = []

    evaluation_size = int(metrics.get("evaluation_size") or 0)

    if float(metrics.get("accuracy") or 0.0) < 0.5 and evaluation_size >= 5:
        issues.append("accuracy below 0.50")

    if float(metrics.get("fairness_score") or 0.0) < 0.7:
        issues.append("fairness score below 0.70")

    if float(metrics.get("drift_score") or 0.0) < 0.6:
        issues.append("feature drift score below 0.60")

    return ValidationResult(passed=not issues, issues=issues)


def should_promote(validation: ValidationResult) -> bool:
    return validation.passed

