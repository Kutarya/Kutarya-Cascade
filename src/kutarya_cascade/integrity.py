"""Integrity checks that reject compression when critical values change."""

from __future__ import annotations

from collections import Counter

from .inspector import PromptInspector
from .models import IntegrityResult


_KINDS = (
    "negation",
    "number",
    "date",
    "money",
    "unit",
    "entity",
    "quote",
    "code",
    "json",
    "operator",
    "instruction",
)


def _signature(value: str) -> str:
    return " ".join(value.split()).casefold()


class IntegrityGuard:
    """Compares ordered, normalized multisets of protected artifacts."""

    def __init__(self, inspector: PromptInspector | None = None) -> None:
        self.inspector = inspector or PromptInspector()

    def validate(self, original: str, candidate: str) -> IntegrityResult:
        source = self.inspector.inspect(original)
        target = self.inspector.inspect(candidate)
        missing: list[str] = []
        added: list[str] = []
        reordered: list[str] = []
        details: dict[str, object] = {}

        for kind in _KINDS:
            before = [_signature(a.value) for a in source.artifacts if a.kind == kind]
            after = [_signature(a.value) for a in target.artifacts if a.kind == kind]
            before_count = Counter(before)
            after_count = Counter(after)
            for value, count in (before_count - after_count).items():
                missing.extend(f"{kind}:{value}" for _ in range(count))
            for value, count in (after_count - before_count).items():
                added.extend(f"{kind}:{value}" for _ in range(count))
            if before_count == after_count and before != after:
                reordered.append(kind)
            details[kind] = {"before": len(before), "after": len(after)}

        passed = not missing and not added and not reordered
        return IntegrityResult(
            passed=passed,
            missing=tuple(missing),
            added=tuple(added),
            reordered_kinds=tuple(reordered),
            details=details,
        )
