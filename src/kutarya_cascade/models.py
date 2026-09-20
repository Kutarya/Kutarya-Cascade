"""Shared immutable data models for inspection and compression."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ArtifactKind = Literal[
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
]


@dataclass(frozen=True)
class Artifact:
    kind: ArtifactKind
    value: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Inspection:
    language: Literal["tr", "en", "mixed", "unknown"]
    character_count: int
    word_count: int
    line_count: int
    artifacts: tuple[Artifact, ...]
    risk_score: float
    risk_level: Literal["low", "medium", "high", "critical"]
    reasons: tuple[str, ...]

    def count(self, kind: ArtifactKind) -> int:
        return sum(1 for item in self.artifacts if item.kind == kind)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["artifact_counts"] = {
            kind: self.count(kind)
            for kind in (
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
        }
        return result


@dataclass(frozen=True)
class IntegrityResult:
    passed: bool
    missing: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    reordered_kinds: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompressionResult:
    requested_mode: Literal["original", "lossless", "safe"]
    applied_mode: Literal["original", "lossless", "safe"]
    original: str
    compressed: str
    fallback: bool
    fallback_reason: str | None
    integrity: IntegrityResult
    inspection: Inspection
    changes: tuple[str, ...] = ()

    @property
    def character_ratio(self) -> float:
        if not self.original:
            return 1.0
        return len(self.compressed) / len(self.original)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["character_ratio"] = self.character_ratio
        return result
