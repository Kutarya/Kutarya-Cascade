"""Risk-gated conservative semantic compression."""

from __future__ import annotations

import re

from .integrity import IntegrityGuard
from .inspector import PromptInspector
from .lossless import LosslessCompressor


_POLITENESS_RE = re.compile(
    r"(?i)(?<![\wÇĞİÖŞÜçğıöşü])(?:could you please|would you please|"
    r"lütfen|rica etsem|please)(?:\s+)",
)
_SENTENCE_RE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)|\n+")


class SafeCompressor:
    """Compresses only low/medium risk prose and lets the guard decide."""

    def __init__(
        self,
        inspector: PromptInspector | None = None,
        guard: IntegrityGuard | None = None,
        lossless: LosslessCompressor | None = None,
    ) -> None:
        self.inspector = inspector or PromptInspector()
        self.guard = guard or IntegrityGuard(self.inspector)
        self.lossless = lossless or LosslessCompressor(self.inspector)

    def compress(self, text: str) -> tuple[str, tuple[str, ...], str | None]:
        inspection = self.inspector.inspect(text)
        if inspection.risk_level in {"high", "critical"}:
            return text, (), f"risk_gate:{inspection.risk_level}"

        base = self.lossless.compress(text)
        candidate = _POLITENESS_RE.sub("", base.text)
        changes = list(base.changes)
        if candidate != base.text:
            changes.append("nezaket dolgusu kaldırıldı")

        candidate, deduplicated = self._deduplicate_adjacent(candidate)
        if deduplicated:
            changes.append("bitişik tam tekrar kaldırıldı")

        candidate = candidate.strip()
        if not candidate:
            return text, (), "empty_candidate"
        integrity = self.guard.validate(text, candidate)
        if not integrity.passed:
            return text, (), "integrity_guard"
        if len(candidate) >= len(text):
            return text, (), "no_gain"
        return candidate, tuple(dict.fromkeys(changes)), None

    @staticmethod
    def _deduplicate_adjacent(text: str) -> tuple[str, bool]:
        parts = [m.group(0) for m in _SENTENCE_RE.finditer(text)]
        result: list[str] = []
        previous: str | None = None
        changed = False
        for part in parts:
            normalized = " ".join(part.split()).casefold().strip(".!? ")
            if normalized and normalized == previous:
                changed = True
                continue
            result.append(part)
            if normalized:
                previous = normalized
        return "".join(result), changed
