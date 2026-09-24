# Kutarya Cascade v0.1

[![CI](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml/badge.svg)](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License: BSD-4-Clause](https://img.shields.io/badge/license-BSD--4--Clause-blue.svg)](LICENSE)

[Türkçe](README.md)

Kutarya Cascade is an experimental Python toolkit for inspecting LLM prompts, preserving critical information, and reducing prompt size when deterministic checks permit it. It provides a benchmark runner for comparing baseline, lossless, and safe paths on the same model with identical generation settings.

The project makes no unmeasured performance claims. If Integrity Guard cannot validate a transformed prompt, the original prompt is used.

## Status

- Python core and command-line interface are operational.
- Unit and model-independent integration tests: **44/44 passing**.
- Test dataset: **30 cases (15 Turkish, 15 English)**.
- The llama.cpp protocol integration has been tested.
- A real Qwen3-4B benchmark has not been run because the required local GGUF file is unavailable.

See [TEST_REPORT.md](TEST_REPORT.md) for the verification record.

## Installation

```bash
git clone https://github.com/Kutarya/Kutarya-Cascade.git
cd Kutarya-Cascade
python -m pip install -e ".[metrics,test]"
python -m unittest discover -s tests -v
```

Inspect a prompt:

```bash
kutarya-cascade inspect "Never change the 3 kg value" --mode safe
```

## Pipeline

```text
Prompt
  -> PromptInspector
  -> IntegrityGuard
  -> LosslessCompressor or SafeCompressor
  -> IntegrityGuard
  -> validated candidate or original prompt
  -> llama.cpp
  -> JSON and CSV measurements
```

The guard checks negation, numbers, dates, money, units, entities, quoted text, code, JSON, operators, and important instructions. The safe path is intentionally conservative and normally falls back for code, JSON, and high-risk prompts.

See [CASCADE_SPEC.md](CASCADE_SPEC.md) for the behavior contract.

## Benchmark

```powershell
python -m kutarya_cascade benchmark `
  --model "D:\path\to\model.gguf" `
  --llama-server "D:\path\to\llama-server.exe" `
  --warmups 2 --repeats 3
```

The runner can record input tokens, compression ratio, TTFT, total latency, output token rate, RAM/VRAM use, quality signals, critical-item retention, and fallback rate. Unavailable measurements remain `null` in JSON and `ölçülemedi` in CSV.

## Limitations

- Safe Compressor v0.1 is intentionally conservative.
- Code, JSON, and prompts with dense critical information usually fall back.
- Rule-based entity extraction is not a complete NER system.
- Character reduction does not guarantee fewer tokens or lower latency.
- Performance claims require real-model measurements.

## License

This project is distributed under the BSD-4-Clause license. Source and binary redistributions must preserve the required notices. Advertising material that mentions the software's features or use must include:

> This product includes software developed by Kutarya.

See [LICENSE](LICENSE) and [NOTICE](NOTICE).
