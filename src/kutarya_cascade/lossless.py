"""Reversible structural whitespace compression outside protected literals."""

from __future__ import annotations

from dataclasses import dataclass

from .inspector import PromptInspector


@dataclass(frozen=True)
class RestorationPatch:
    index: int
    removed: str


@dataclass(frozen=True)
class LosslessTransform:
    text: str
    patches: tuple[RestorationPatch, ...]
    changes: tuple[str, ...]

    def restore(self) -> str:
        result = self.text
        for patch in reversed(self.patches):
            result = result[: patch.index] + patch.removed + result[patch.index :]
        return result


class LosslessCompressor:
    """Compresses redundant whitespace while preserving an exact restoration plan.

    Code fences, inline code, JSON and quotes are copied byte-for-byte. Outside
    those spans, only redundant horizontal whitespace and excessive empty lines
    are removed. The transform can reconstruct the exact source string.
    """

    def __init__(self, inspector: PromptInspector | None = None) -> None:
        self.inspector = inspector or PromptInspector()

    def compress(self, text: str) -> LosslessTransform:
        inspection = self.inspector.inspect(text)
        protected = sorted(
            (a.start, a.end)
            for a in inspection.artifacts
            if a.kind in {"code", "json", "quote"}
        )
        out: list[str] = []
        patches: list[RestorationPatch] = []
        changes: list[str] = []
        cursor = 0

        for start, end in protected:
            if start < cursor:
                continue
            self._compress_plain(text[cursor:start], out, patches, changes)
            out.append(text[start:end])
            cursor = end
        self._compress_plain(text[cursor:], out, patches, changes)

        transform = LosslessTransform(
            text="".join(out),
            patches=tuple(patches),
            changes=tuple(dict.fromkeys(changes)),
        )
        if transform.restore() != text:
            raise RuntimeError("lossless restorasyon doğrulaması başarısız")
        return transform

    @staticmethod
    def _remove(
        removed: str,
        out: list[str],
        patches: list[RestorationPatch],
    ) -> None:
        if removed:
            patches.append(RestorationPatch(sum(map(len, out)), removed))

    def _compress_plain(
        self,
        value: str,
        out: list[str],
        patches: list[RestorationPatch],
        changes: list[str],
    ) -> None:
        index = 0
        while index < len(value):
            char = value[index]
            if char in " \t":
                end = index + 1
                while end < len(value) and value[end] in " \t":
                    end += 1
                run = value[index:end]
                next_char = value[end] if end < len(value) else ""
                prev_char = out[-1][-1] if out and out[-1] else ""
                if next_char in "\r\n" or not prev_char or prev_char in "\r\n":
                    self._remove(run, out, patches)
                    changes.append("satır kenarı boşlukları kaldırıldı")
                else:
                    out.append(run[0])
                    self._remove(run[1:], out, patches)
                    if len(run) > 1:
                        changes.append("yinelenen yatay boşluklar birleştirildi")
                index = end
                continue
            if char in "\r\n":
                end = index
                newline_units: list[str] = []
                while end < len(value):
                    if value.startswith("\r\n", end):
                        newline_units.append("\r\n")
                        end += 2
                    elif value[end] in "\r\n":
                        newline_units.append(value[end])
                        end += 1
                    else:
                        break
                kept = newline_units[:2]
                removed = "".join(newline_units[2:])
                out.extend(kept)
                self._remove(removed, out, patches)
                if removed:
                    changes.append("aşırı boş satırlar iki satıra indirildi")
                index = end
                continue
            out.append(char)
            index += 1
