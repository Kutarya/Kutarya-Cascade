"""Fair three-path benchmark runner and evidence writer."""

from __future__ import annotations

import csv
import json
import random
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pipeline import CascadePipeline
from .quality import evaluate_output, output_similarity
from .runtime import GenerationSettings, LlamaCppRuntime
from .system_metrics import ResourceSampler


SYSTEM_PROMPT = (
    "You are Kutarya Us. Follow the user's request exactly. "
    "Respond in the user's language. Do not mention prompt compression."
)
MODES = ("baseline", "lossless", "safe")


@dataclass(frozen=True)
class BenchmarkConfig:
    warmups: int = 2
    repeats: int = 3
    random_seed: int = 20260920
    settings: GenerationSettings = GenerationSettings()


def load_dataset(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            required = {"id", "language", "category", "prompt"}
            missing = required - value.keys()
            if missing:
                raise ValueError(f"veri satırı {line_number} eksik: {sorted(missing)}")
            cases.append(value)
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("veri setinde yinelenen id var")
    return cases


class BenchmarkRunner:
    def __init__(
        self,
        runtime: LlamaCppRuntime,
        process_id: int | None,
        config: BenchmarkConfig | None = None,
    ) -> None:
        self.runtime = runtime
        self.process_id = process_id
        self.config = config or BenchmarkConfig()
        self.pipeline = CascadePipeline()

    def run(
        self,
        cases: list[dict[str, Any]],
        model_path: str,
        model_info: dict[str, Any],
    ) -> dict[str, Any]:
        if not cases:
            raise ValueError("benchmark veri seti boş")
        started_at = datetime.now(timezone.utc).isoformat()
        self._warm_up(cases[0]["prompt"])
        records: list[dict[str, Any]] = []
        rng = random.Random(self.config.random_seed)

        for case in cases:
            for repeat in range(1, self.config.repeats + 1):
                order = list(MODES)
                rng.shuffle(order)
                group: dict[str, dict[str, Any]] = {}
                for position, mode in enumerate(order, start=1):
                    record = self._measure(case, repeat, position, mode)
                    records.append(record)
                    group[mode] = record
                self._compare_group(group)

        summary = summarize(records)
        return {
            "schema_version": 1,
            "project_version": "0.1.0",
            "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_path": model_path,
            "model_info": model_info,
            "server_url": self.runtime.base_url,
            "process_id": self.process_id,
            "config": {
                "warmups": self.config.warmups,
                "repeats": self.config.repeats,
                "random_seed": self.config.random_seed,
                "generation": asdict(self.config.settings),
                "system_prompt": SYSTEM_PROMPT,
                "cache_prompt": False,
                "mode_order": "her tekrar için deterministik karıştırıldı",
            },
            "summary": summary,
            "records": records,
        }

    def _warm_up(self, prompt: str) -> None:
        for _ in range(self.config.warmups):
            for mode in MODES:
                cascade_mode = "original" if mode == "baseline" else mode
                processed = self.pipeline.process(prompt, cascade_mode)  # type: ignore[arg-type]
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": processed.compressed},
                ]
                self.runtime.generate(messages, self.config.settings)

    def _measure(
        self,
        case: dict[str, Any],
        repeat: int,
        order_position: int,
        mode: str,
    ) -> dict[str, Any]:
        cascade_mode = "original" if mode == "baseline" else mode
        processed = self.pipeline.process(case["prompt"], cascade_mode)  # type: ignore[arg-type]
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": processed.compressed},
        ]
        input_tokens = self.runtime.count_chat_tokens(messages)
        sampler = ResourceSampler(self.process_id)
        sampler.start()
        try:
            inference = self.runtime.generate(messages, self.config.settings)
        finally:
            resources = sampler.stop()
        quality = evaluate_output(case, inference.text)
        return {
            "case_id": case["id"],
            "language": case["language"],
            "category": case["category"],
            "repeat": repeat,
            "order_position": order_position,
            "mode": mode,
            "requested_mode": processed.requested_mode,
            "applied_mode": processed.applied_mode,
            "fallback": processed.fallback,
            "fallback_reason": processed.fallback_reason,
            "risk_level": processed.inspection.risk_level,
            "risk_score": processed.inspection.risk_score,
            "critical_retention": processed.integrity.passed,
            "prompt_original": processed.original,
            "prompt_sent": processed.compressed,
            "character_ratio": processed.character_ratio,
            "changes": list(processed.changes),
            "input_tokens": input_tokens,
            "ttft_ms": inference.ttft_ms,
            "prefill_ms": inference.prefill_ms,
            "total_latency_ms": inference.total_latency_ms,
            "output_tokens": inference.output_tokens,
            "output_tokens_per_second": inference.output_tokens_per_second,
            "process_ram_start_mb": resources.process_ram_start_mb,
            "process_ram_peak_mb": resources.process_ram_peak_mb,
            "process_ram_delta_mb": resources.process_ram_delta_mb,
            "system_ram_start_mb": resources.system_ram_start_mb,
            "system_ram_peak_mb": resources.system_ram_peak_mb,
            "gpu_vram_start_mb": resources.gpu_vram_start_mb,
            "gpu_vram_peak_mb": resources.gpu_vram_peak_mb,
            "gpu_vram_delta_mb": resources.gpu_vram_delta_mb,
            "gpu_scope": resources.gpu_scope,
            "output": inference.text,
            "quality": quality.to_dict(),
            "usage": inference.usage,
            "timings": inference.timings,
            "baseline_output_similarity": None,
            "quality_regression": None,
            "cascade_failure": not processed.integrity.passed,
        }

    @staticmethod
    def _compare_group(group: dict[str, dict[str, Any]]) -> None:
        baseline = group["baseline"]
        baseline_score = baseline["quality"]["overall_score"]
        baseline_tokens = baseline["input_tokens"]
        for mode in ("lossless", "safe"):
            candidate = group[mode]
            candidate["baseline_output_similarity"] = output_similarity(
                baseline["output"], candidate["output"]
            )
            candidate_score = candidate["quality"]["overall_score"]
            regression = (
                baseline_score is not None
                and candidate_score is not None
                and candidate_score < baseline_score
            )
            candidate["quality_regression"] = regression
            candidate["cascade_failure"] = bool(
                candidate["cascade_failure"] or regression
            )
            if isinstance(baseline_tokens, int) and baseline_tokens > 0 and isinstance(candidate["input_tokens"], int):
                candidate["input_token_ratio"] = candidate["input_tokens"] / baseline_tokens
                candidate["input_token_reduction_percent"] = (
                    1.0 - candidate["input_tokens"] / baseline_tokens
                ) * 100.0
            else:
                candidate["input_token_ratio"] = None
                candidate["input_token_reduction_percent"] = None
        baseline["input_token_ratio"] = 1.0
        baseline["input_token_reduction_percent"] = 0.0


def _mean(records: list[dict[str, Any]], key: str) -> float | None:
    values = [float(record[key]) for record in records if isinstance(record.get(key), (int, float))]
    return None if not values else statistics.fmean(values)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    modes: dict[str, Any] = {}
    for mode in MODES:
        selected = [record for record in records if record["mode"] == mode]
        quality_values = [
            record["quality"]["overall_score"]
            for record in selected
            if isinstance(record["quality"].get("overall_score"), (int, float))
        ]
        modes[mode] = {
            "measurements": len(selected),
            "input_tokens_mean": _mean(selected, "input_tokens"),
            "input_token_reduction_percent_mean": _mean(selected, "input_token_reduction_percent"),
            "ttft_ms_mean": _mean(selected, "ttft_ms"),
            "prefill_ms_mean": _mean(selected, "prefill_ms"),
            "total_latency_ms_mean": _mean(selected, "total_latency_ms"),
            "output_tokens_per_second_mean": _mean(selected, "output_tokens_per_second"),
            "process_ram_peak_mb_mean": _mean(selected, "process_ram_peak_mb"),
            "gpu_vram_peak_mb_mean": _mean(selected, "gpu_vram_peak_mb"),
            "quality_mean": None if not quality_values else statistics.fmean(quality_values),
            "critical_retention_rate": (
                None if not selected else sum(record["critical_retention"] for record in selected) / len(selected)
            ),
            "fallback_rate": None if not selected else sum(record["fallback"] for record in selected) / len(selected),
            "cascade_failure_rate": (
                None if mode == "baseline" or not selected
                else sum(record["cascade_failure"] for record in selected) / len(selected)
            ),
        }
    cascade_records = [record for record in records if record["mode"] != "baseline"]
    categories: dict[str, Any] = {}
    for category in sorted({record.get("category", "unknown") for record in records}):
        categories[category] = {}
        baseline_records = [
            record for record in records
            if record.get("category", "unknown") == category and record["mode"] == "baseline"
        ]
        for mode in ("lossless", "safe"):
            selected = [
                record for record in records
                if record.get("category", "unknown") == category and record["mode"] == mode
            ]
            categories[category][mode] = {
                "input_token_reduction_percent_mean": _mean(selected, "input_token_reduction_percent"),
                "ttft_delta_ms_vs_baseline": _difference(
                    {"value": _mean(selected, "ttft_ms")},
                    {"value": _mean(baseline_records, "ttft_ms")},
                    "value",
                ),
                "latency_delta_ms_vs_baseline": _difference(
                    {"value": _mean(selected, "total_latency_ms")},
                    {"value": _mean(baseline_records, "total_latency_ms")},
                    "value",
                ),
                "fallback_rate": None if not selected else sum(record["fallback"] for record in selected) / len(selected),
                "failure_rate": None if not selected else sum(record["cascade_failure"] for record in selected) / len(selected),
            }
    advantages: list[str] = []
    no_advantage: list[str] = []
    for category, mode_values in categories.items():
        for mode, values in mode_values.items():
            reduction = values["input_token_reduction_percent_mean"]
            latency_delta = values["latency_delta_ms_vs_baseline"]
            if (
                reduction is not None and reduction > 0
                and latency_delta is not None and latency_delta < 0
                and values["failure_rate"] == 0
            ):
                advantages.append(f"{category}:{mode}")
            elif reduction is not None and (reduction <= 0 or values["fallback_rate"] == 1 or values["failure_rate"] not in {0, None}):
                no_advantage.append(f"{category}:{mode}")
    return {
        "total_measurements": len(records),
        "cascade_evaluations": len(cascade_records),
        "cascade_passed": sum(not record["cascade_failure"] for record in cascade_records),
        "cascade_failed": sum(record["cascade_failure"] for record in cascade_records),
        "modes": modes,
        "category_breakdown": categories,
        "advantage_observed": advantages,
        "no_advantage_observed": no_advantage,
    }


def write_results(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"benchmark-{stamp}.json"
    csv_path = output_dir / f"benchmark-{stamp}.csv"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    records = result["records"]
    rows = [_flatten(record) for record in records]
    columns = sorted({key for row in rows for key in row})
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "ölçülemedi" if row.get(key) is None else row.get(key) for key in columns})
    return json_path, csv_path


def _flatten(value: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            for child_key, child in item.items():
                output[f"{key}.{child_key}"] = json.dumps(child, ensure_ascii=False) if isinstance(child, (dict, list)) else child
        elif isinstance(item, list):
            output[key] = json.dumps(item, ensure_ascii=False)
        else:
            output[key] = item
    return output


def render_terminal_report(result: dict[str, Any]) -> str:
    modes = result["summary"]["modes"]

    def show(value: Any, suffix: str = "") -> str:
        return "ölçülemedi" if value is None else f"{value:.2f}{suffix}" if isinstance(value, float) else f"{value}{suffix}"

    baseline = modes["baseline"]
    lossless = modes["lossless"]
    safe = modes["safe"]
    return "\n".join(
        [
            "KUTARYA CASCADE v0.1 — FINAL RAPOR",
            f"Model: {result['model_path']}",
            f"Model bilgisi: {json.dumps(result['model_info'], ensure_ascii=False)}",
            f"Test sayısı / başarılı / başarısız: {result['summary']['cascade_evaluations']} / {result['summary']['cascade_passed']} / {result['summary']['cascade_failed']}",
            f"Baseline: token={show(baseline['input_tokens_mean'])}, TTFT={show(baseline['ttft_ms_mean'], ' ms')}, latency={show(baseline['total_latency_ms_mean'], ' ms')}, çıkış={show(baseline['output_tokens_per_second_mean'], ' token/s')}, RAM={show(baseline['process_ram_peak_mb_mean'], ' MB')}, VRAM={show(baseline['gpu_vram_peak_mb_mean'], ' MB')}",
            f"Lossless: token azalması={show(lossless['input_token_reduction_percent_mean'], '%')}, TTFT farkı={show(_difference(lossless, baseline, 'ttft_ms_mean'), ' ms')}, latency farkı={show(_difference(lossless, baseline, 'total_latency_ms_mean'), ' ms')}",
            f"Safe: token azalması={show(safe['input_token_reduction_percent_mean'], '%')}, TTFT farkı={show(_difference(safe, baseline, 'ttft_ms_mean'), ' ms')}, latency farkı={show(_difference(safe, baseline, 'total_latency_ms_mean'), ' ms')}",
            f"RAM farkı (lossless/safe peak-baseline): {show(_difference(lossless, baseline, 'process_ram_peak_mb_mean'), ' MB')} / {show(_difference(safe, baseline, 'process_ram_peak_mb_mean'), ' MB')}",
            f"VRAM farkı (lossless/safe peak-baseline): {show(_difference(lossless, baseline, 'gpu_vram_peak_mb_mean'), ' MB')} / {show(_difference(safe, baseline, 'gpu_vram_peak_mb_mean'), ' MB')}",
            f"Kalite (baseline/lossless/safe): {show(baseline['quality_mean'])} / {show(lossless['quality_mean'])} / {show(safe['quality_mean'])}",
            f"Critical retention (lossless/safe): {show(lossless['critical_retention_rate'])} / {show(safe['critical_retention_rate'])}",
            f"Fallback oranı (lossless/safe): {show(lossless['fallback_rate'])} / {show(safe['fallback_rate'])}",
            f"Avantaj gözlenenler: {', '.join(result['summary']['advantage_observed']) or 'yok'}",
            f"Avantaj gözlenmeyenler: {', '.join(result['summary']['no_advantage_observed']) or 'yok'}",
            "Sonraki teknik nokta: daha geniş veri seti, süreç-özel VRAM telemetrisi ve sunucunun prefill zamanını sağlamadığı build'lerde yerel enstrümantasyon.",
        ]
    )


def _difference(left: dict[str, Any], right: dict[str, Any], key: str) -> float | None:
    if left.get(key) is None or right.get(key) is None:
        return None
    return float(left[key]) - float(right[key])
