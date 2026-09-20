"""Public Cascade orchestration with mandatory fail-closed fallback."""

from __future__ import annotations

from typing import Literal

from .integrity import IntegrityGuard
from .inspector import PromptInspector
from .lossless import LosslessCompressor
from .models import CompressionResult
from .safe import SafeCompressor


class CascadePipeline:
    def __init__(self) -> None:
        self.inspector = PromptInspector()
        self.guard = IntegrityGuard(self.inspector)
        self.lossless = LosslessCompressor(self.inspector)
        self.safe = SafeCompressor(self.inspector, self.guard, self.lossless)

    def process(
        self,
        prompt: str,
        mode: Literal["original", "lossless", "safe"] = "safe",
    ) -> CompressionResult:
        if mode not in {"original", "lossless", "safe"}:
            raise ValueError(f"bilinmeyen mod: {mode}")
        inspection = self.inspector.inspect(prompt)
        if mode == "original":
            integrity = self.guard.validate(prompt, prompt)
            return CompressionResult(
                requested_mode=mode,
                applied_mode="original",
                original=prompt,
                compressed=prompt,
                fallback=False,
                fallback_reason=None,
                integrity=integrity,
                inspection=inspection,
            )

        if mode == "lossless":
            transform = self.lossless.compress(prompt)
            candidate = transform.text
            integrity = self.guard.validate(prompt, candidate)
            if not integrity.passed or transform.restore() != prompt:
                return CompressionResult(
                    requested_mode=mode,
                    applied_mode="original",
                    original=prompt,
                    compressed=prompt,
                    fallback=True,
                    fallback_reason="integrity_guard" if not integrity.passed else "restore_failed",
                    integrity=integrity,
                    inspection=inspection,
                )
            return CompressionResult(
                requested_mode=mode,
                applied_mode="lossless",
                original=prompt,
                compressed=candidate,
                fallback=False,
                fallback_reason=None,
                integrity=integrity,
                inspection=inspection,
                changes=transform.changes,
            )

        candidate, changes, reason = self.safe.compress(prompt)
        integrity = self.guard.validate(prompt, candidate)
        fallback = reason is not None
        return CompressionResult(
            requested_mode=mode,
            applied_mode="original" if fallback else "safe",
            original=prompt,
            compressed=prompt if fallback else candidate,
            fallback=fallback,
            fallback_reason=reason,
            integrity=integrity,
            inspection=inspection,
            changes=changes,
        )
