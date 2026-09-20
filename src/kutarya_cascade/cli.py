"""Command-line interface for inspection and real benchmarking."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .benchmark import (
    BenchmarkConfig,
    BenchmarkRunner,
    load_dataset,
    render_terminal_report,
    write_results,
)
from .pipeline import CascadePipeline
from .runtime import GenerationSettings, LlamaCppRuntime, LlamaServerProcess


DEFAULT_MODEL = Path(r"D:\Kutarya\KutaryaModelLab\models\Qwen3-4B-Q6_K.gguf")
DEFAULT_SERVER = Path(os.environ.get("APPDATA", "")) / "kutarya-studio" / "yerel" / "motor" / "b10549" / "llama-server.exe"
DEFAULT_DATASET = Path(__file__).resolve().parent / "data" / "benchmarks_tr_en.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kutarya-cascade")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_parser = sub.add_parser("inspect", help="promptu analiz et ve sıkıştır")
    inspect_parser.add_argument("prompt")
    inspect_parser.add_argument("--mode", choices=("original", "lossless", "safe"), default="safe")

    doctor = sub.add_parser("doctor", help="model/runtime durumunu doğrula")
    doctor.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    doctor.add_argument("--llama-server", type=Path, default=DEFAULT_SERVER)

    bench = sub.add_parser("benchmark", help="baseline/lossless/safe gerçek inference benchmarkı")
    bench.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    bench.add_argument("--output", type=Path, default=Path("results"))
    bench.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    bench.add_argument("--llama-server", type=Path, default=DEFAULT_SERVER)
    bench.add_argument("--server-url", help="hazır llama-server kullan; verilirse süreç başlatılmaz")
    bench.add_argument("--server-pid", type=int)
    bench.add_argument("--port", type=int, default=18912)
    bench.add_argument("--warmups", type=int, default=2)
    bench.add_argument("--repeats", type=int, default=3)
    bench.add_argument("--max-tokens", type=int, default=128)
    bench.add_argument("--gpu-layers", type=int, default=20)
    bench.add_argument("--threads", type=int, default=8)
    bench.add_argument("--context", type=int, default=4096)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        result = CascadePipeline().process(args.prompt, args.mode)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "doctor":
        status = {
            "model": str(args.model.resolve()),
            "model_exists": args.model.is_file(),
            "model_size_bytes": args.model.stat().st_size if args.model.is_file() else None,
            "llama_server": str(args.llama_server.resolve()),
            "llama_server_exists": args.llama_server.is_file(),
        }
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["model_exists"] and status["llama_server_exists"] else 2
    if args.command == "benchmark":
        return _benchmark(args)
    return 2


def _benchmark(args: argparse.Namespace) -> int:
    if args.warmups < 1 or args.repeats < 2:
        print("Hata: warmups >= 1 ve repeats >= 2 olmalıdır.", file=sys.stderr)
        return 2
    cases = load_dataset(args.dataset)
    config = BenchmarkConfig(
        warmups=args.warmups,
        repeats=args.repeats,
        settings=GenerationSettings(max_tokens=args.max_tokens),
    )
    if args.server_url:
        runtime = LlamaCppRuntime(args.server_url)
        if not runtime.health():
            print(f"Hata: sunucu hazır değil: {args.server_url}", file=sys.stderr)
            return 3
        result = BenchmarkRunner(runtime, args.server_pid, config).run(
            cases, str(args.model.resolve()), runtime.props()
        )
    else:
        if not args.model.is_file():
            print(f"Hata: model dosyası bulunamadı: {args.model.resolve()}", file=sys.stderr)
            return 4
        server = LlamaServerProcess(
            executable=args.llama_server,
            model=args.model,
            port=args.port,
            context_size=args.context,
            threads=args.threads,
            gpu_layers=args.gpu_layers,
            log_path=args.output / "llama-server.log",
        )
        with server:
            runtime = LlamaCppRuntime(server.base_url)
            result = BenchmarkRunner(runtime, server.pid, config).run(
                cases, str(args.model.resolve()), runtime.props()
            )
    json_path, csv_path = write_results(result, args.output)
    print(render_terminal_report(result))
    print(f"Ham JSON: {json_path.resolve()}")
    print(f"Ham CSV: {csv_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
