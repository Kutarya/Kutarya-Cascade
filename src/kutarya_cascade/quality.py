"""Transparent task-specific quality signals; no LLM judge is used."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any


@dataclass(frozen=True)
class QualityResult:
    expected_contains_score: float | None
    expected_regex_pass: bool | None
    forbidden_absent_score: float | None
    exact_match: bool | None
    overall_score: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_output(case: dict[str, Any], output: str) -> QualityResult:
    normalized = " ".join(output.casefold().split())
    expected = [str(item).casefold() for item in case.get("expected_contains", [])]
    forbidden = [str(item).casefold() for item in case.get("forbidden_contains", [])]
    contains_score = None
    if expected:
        contains_score = sum(item in normalized for item in expected) / len(expected)
    forbidden_score = None
    if forbidden:
        forbidden_score = sum(item not in normalized for item in forbidden) / len(forbidden)
    regex = case.get("expected_regex")
    regex_pass = None if not regex else bool(re.search(str(regex), output, re.IGNORECASE | re.DOTALL))
    exact = case.get("expected_exact")
    exact_match = None if exact is None else normalized == " ".join(str(exact).casefold().split())
    signals = [
        float(value)
        for value in (contains_score, forbidden_score, regex_pass, exact_match)
        if value is not None
    ]
    overall = None if not signals else sum(signals) / len(signals)
    return QualityResult(contains_score, regex_pass, forbidden_score, exact_match, overall)


def output_similarity(baseline: str, candidate: str) -> float:
    left = " ".join(baseline.casefold().split())
    right = " ".join(candidate.casefold().split())
    return SequenceMatcher(None, left, right).ratio()
