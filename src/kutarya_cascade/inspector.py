"""Deterministic prompt inspection. No model call is used here."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from .models import Artifact, Inspection


_TR_MARKERS = {
    "ve", "veya", "ama", "değil", "lütfen", "için", "ile", "şunu",
    "bunu", "çıktı", "tarih", "önce", "sonra", "olmadan", "asla",
}
_EN_MARKERS = {
    "and", "or", "but", "not", "please", "for", "with", "this",
    "that", "output", "date", "before", "after", "without", "never",
}

_NEGATION_RE = re.compile(
    r"(?<![\wÇĞİÖŞÜçğıöşü])(?:değil|yok|asla|hiçbir|hariç|olmadan|"
    r"not|no|never|none|without|except)(?![\wÇĞİÖŞÜçğıöşü])",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"(?<!\d)(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|"
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})(?!\d)"
)
_MONEY_RE = re.compile(
    r"(?:[$€£₺]\s?\d[\d.,]*|\d[\d.,]*\s?(?:TL|TRY|USD|EUR|GBP|dolar|euro|lira))",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)*(?:%|‰)?(?![\w])")
_UNIT_RE = re.compile(
    r"(?<![\w])\d+(?:[.,]\d+)?\s?(?:ms|s|sn|sec|dk|min|h|saat|"
    r"KB|MB|GB|TB|B|Hz|kHz|MHz|GHz|W|kW|V|A|mA|mm|cm|m|km|"
    r"mg|g|kg|ml|L|°C|°F|token/s)(?![\w])",
    re.IGNORECASE,
)
_QUOTE_RE = re.compile(r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|“[^”]*”|‘[^’]*’)", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_OPERATOR_RE = re.compile(r"===|!==|==|!=|<=|>=|=>|&&|\|\||\+\+|--|\*\*|:=|->|[+*/%<>]=?|(?<!\w)-(?!\w)")
_ENTITY_RE = re.compile(
    r"(?<![\wÇĞİÖŞÜçğıöşü])(?:[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü.-]+"
    r"(?:\s+[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü.-]+)+)(?![\wÇĞİÖŞÜçğıöşü])"
)
_SINGLE_ENTITY_RE = re.compile(
    r"(?<![\wÇĞİÖŞÜçğıöşü])(?:[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9_.-]{1,})(?![\wÇĞİÖŞÜçğıöşü])"
)
_INSTRUCTION_RE = re.compile(
    r"(?im)(?<![\wÇĞİÖŞÜçğıöşü])(?:lütfen\s+)?(?:mutlaka|kesinlikle|yalnızca|sadece|"
    r"asla|tam olarak|çıktıyı|yanıtı|cevabı|kullan|koru|yaz|ver|yap|etme|yapma|açıkla|listele|özetle|"
    r"must|shall|always|never|only|exactly|do not|don't|output|return|keep|use|write|"
    r"answer|respond|explain|state|list|summarize)\b[^\n.!?]*(?:[.!?]|$)",
)


def _overlaps(start: int, end: int, occupied: Iterable[tuple[int, int]]) -> bool:
    return any(start < right and end > left for left, right in occupied)


class PromptInspector:
    """Extracts critical literals and assigns an explainable risk score."""

    def inspect(self, text: str) -> Inspection:
        if not isinstance(text, str):
            raise TypeError("prompt metin olmalıdır")

        artifacts: list[Artifact] = []
        occupied: list[tuple[int, int]] = []

        def collect(kind: str, pattern: re.Pattern[str], protect: bool = False) -> None:
            for match in pattern.finditer(text):
                if _overlaps(match.start(), match.end(), occupied):
                    continue
                artifacts.append(Artifact(kind, match.group(0), match.start(), match.end()))
                if protect:
                    occupied.append((match.start(), match.end()))

        collect("code", _CODE_FENCE_RE, protect=True)
        collect("code", _INLINE_CODE_RE, protect=True)
        self._collect_json(text, artifacts, occupied)
        collect("quote", _QUOTE_RE, protect=True)
        collect("date", _DATE_RE)
        collect("money", _MONEY_RE)
        collect("unit", _UNIT_RE)
        collect("negation", _NEGATION_RE)
        collect("number", _NUMBER_RE)
        collect("operator", _OPERATOR_RE)
        collect("entity", _ENTITY_RE)
        self._collect_single_entities(text, artifacts, occupied)
        collect("instruction", _INSTRUCTION_RE)
        artifacts.sort(key=lambda item: (item.start, item.end, item.kind))

        language = self._language(text)
        counts: dict[str, int] = {}
        for item in artifacts:
            counts[item.kind] = counts.get(item.kind, 0) + 1

        weights = {
            "negation": 0.8,
            "number": 0.25,
            "date": 0.8,
            "money": 1.0,
            "unit": 0.7,
            "entity": 0.35,
            "quote": 0.8,
            "code": 2.2,
            "json": 2.4,
            "operator": 0.45,
            "instruction": 1.4,
        }
        score = sum(min(counts.get(kind, 0), 5) * weight for kind, weight in weights.items())
        if len(text) < 80:
            score += 0.6
        if counts.get("code") or counts.get("json"):
            score += 1.2
        if counts.get("instruction") and counts.get("negation"):
            score += 1.0
        score = round(min(score, 10.0), 2)
        if score >= 7.0:
            level = "critical"
        elif score >= 4.0:
            level = "high"
        elif score >= 2.0:
            level = "medium"
        else:
            level = "low"

        reasons = tuple(
            f"{kind}:{counts[kind]}" for kind in weights if counts.get(kind)
        )
        return Inspection(
            language=language,
            character_count=len(text),
            word_count=len(re.findall(r"\S+", text)),
            line_count=text.count("\n") + 1,
            artifacts=tuple(artifacts),
            risk_score=score,
            risk_level=level,
            reasons=reasons,
        )

    @staticmethod
    def _language(text: str) -> str:
        lowered = text.casefold()
        words = set(re.findall(r"[a-zçğıöşü]+", lowered))
        tr = len(words & _TR_MARKERS) + (2 if re.search(r"[çğıöşü]", lowered) else 0)
        en = len(words & _EN_MARKERS)
        if tr and en:
            return "mixed"
        if tr:
            return "tr"
        if en:
            return "en"
        return "unknown"

    @staticmethod
    def _collect_single_entities(
        text: str,
        artifacts: list[Artifact],
        occupied: list[tuple[int, int]],
    ) -> None:
        entity_ranges = [(item.start, item.end) for item in artifacts if item.kind == "entity"]
        for match in _SINGLE_ENTITY_RE.finditer(text):
            if _overlaps(match.start(), match.end(), occupied + entity_ranges):
                continue
            prefix = text[: match.start()].rstrip()
            if not prefix or prefix[-1] in ".!?\n":
                continue
            artifacts.append(Artifact("entity", match.group(0), match.start(), match.end()))

    @staticmethod
    def _collect_json(
        text: str,
        artifacts: list[Artifact],
        occupied: list[tuple[int, int]],
    ) -> None:
        decoder = json.JSONDecoder()
        index = 0
        while index < len(text):
            match = re.search(r"[\[{]", text[index:])
            if not match:
                return
            start = index + match.start()
            if _overlaps(start, start + 1, occupied):
                index = start + 1
                continue
            try:
                value, consumed = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                index = start + 1
                continue
            if not isinstance(value, (dict, list)):
                index = start + 1
                continue
            end = start + consumed
            artifacts.append(Artifact("json", text[start:end], start, end))
            occupied.append((start, end))
            index = end
