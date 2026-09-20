# Kutarya Cascade v0.1

[![CI](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml/badge.svg)](https://github.com/Kutarya/Kutarya-Cascade/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![License: BSD-4-Clause](https://img.shields.io/badge/license-BSD--4--Clause-blue.svg)](LICENSE)

[Türkçe README](README.md)

Kutarya Cascade is a deterministic prompt inspection, integrity protection,
conservative compression, and real-inference benchmarking toolkit for LLMs.
It compares original, lossless, and risk-aware safe paths on the same model
with identical generation settings.

It does not claim a performance gain without raw measurements. If a candidate
cannot be proven safe by the Integrity Guard, Cascade sends the original prompt.

## Current status

- Core and CLI: operational.
- Unit and model-independent integration tests: **44/44 passing**.
- Dataset: 30 cases, evenly split between Turkish and English.
- llama.cpp runtime integration: implemented and protocol-tested.
- Real Qwen3-4B benchmark: unavailable because the previously used local GGUF
  is no longer present. No theoretical values are presented as measurements.

## Quick start

```bash
git clone https://github.com/Kutarya/Kutarya-Cascade.git
cd Kutarya-Cascade
python -m pip install -e ".[metrics,test]"
python -m unittest discover -s tests -v
kutarya-cascade inspect "Never change the 3 kg value" --mode safe
```

## Pipeline

```text
prompt
  -> PromptInspector
  -> IntegrityGuard
  -> LosslessCompressor or SafeCompressor
  -> IntegrityGuard again
  -> compressed prompt, or fail-closed fallback to the original
  -> same llama.cpp model and generation settings
  -> raw JSON and CSV measurements
```

The guard protects negation, numbers, dates, money, units, entities, quoted
text, code, JSON, operators, and important instructions. The safe compressor
is intentionally conservative; code, JSON, and high-risk prompts usually fall
back to the original.

See [CASCADE_SPEC.md](CASCADE_SPEC.md) for the exact contract and
[TEST_REPORT.md](TEST_REPORT.md) for the evidence boundary.

## Real benchmark

```powershell
python -m kutarya_cascade benchmark `
  --model "D:\path\to\Qwen3-4B-Q6_K.gguf" `
  --llama-server "D:\path\to\llama-server.exe" `
  --warmups 2 --repeats 3
```

The runner measures input tokens, compression ratio, TTFT, server-reported
prefill time when available, total latency, output tokens/s, RAM, total GPU
VRAM, task-specific quality signals, critical retention, and fallback rate.
Unavailable metrics remain `null` in JSON and `ölçülemedi` in CSV.

## License and mandatory Kutarya attribution

This project is distributed under the BSD-4-Clause license. Source and binary
redistributions must preserve the required notices. Every advertising material
that mentions features or use of this software must display:

> This product includes software developed by Kutarya.

See [LICENSE](LICENSE) and [NOTICE](NOTICE). The advertising clause is an
intentional attribution requirement and may reduce compatibility with some
licenses and ecosystems.
