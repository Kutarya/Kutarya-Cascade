"""llama.cpp HTTP runtime and optional local server lifecycle."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GenerationSettings:
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 40
    seed: int = 42
    max_tokens: int = 128


@dataclass(frozen=True)
class InferenceMeasurement:
    text: str
    ttft_ms: float | None
    prefill_ms: float | None
    total_latency_ms: float
    output_tokens: int | None
    output_tokens_per_second: float | None
    usage: dict[str, Any]
    timings: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LlamaCppRuntime:
    def __init__(self, base_url: str, timeout_seconds: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _json_request(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if data is None else "POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def health(self) -> bool:
        try:
            result = self._json_request("/health")
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return False
        return isinstance(result, dict) and result.get("status") in {"ok", "ready"}

    def props(self) -> dict[str, Any]:
        result = self._json_request("/props")
        return result if isinstance(result, dict) else {"raw": result}

    def count_chat_tokens(self, messages: list[dict[str, str]]) -> int | None:
        prompt: str | None = None
        try:
            applied = self._json_request(
                "/apply-template",
                {
                    "messages": messages,
                    "add_generation_prompt": True,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            if isinstance(applied, dict):
                prompt = applied.get("prompt") or applied.get("content")
            elif isinstance(applied, str):
                prompt = applied
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            prompt = None

        if prompt is not None:
            try:
                tokenized = self._json_request("/tokenize", {"content": prompt})
                return self._token_count(tokenized)
            except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
                pass

        try:
            tokenized = self._json_request(
                "/tokenize",
                {"content": "\n".join(message["content"] for message in messages)},
            )
            return self._token_count(tokenized)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            return None

    @staticmethod
    def _token_count(value: Any) -> int | None:
        if isinstance(value, dict):
            if isinstance(value.get("tokens"), list):
                return len(value["tokens"])
            if isinstance(value.get("count"), int):
                return value["count"]
        if isinstance(value, list):
            return len(value)
        return None

    def generate(
        self,
        messages: list[dict[str, str]],
        settings: GenerationSettings,
    ) -> InferenceMeasurement:
        payload = {
            "model": "Kutarya Us",
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "top_k": settings.top_k,
            "seed": settings.seed,
            "max_tokens": settings.max_tokens,
            "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request = urllib.request.Request(
            self.base_url + "/v1/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            method="POST",
        )
        started = time.perf_counter()
        first_token_at: float | None = None
        chunks: list[str] = []
        usage: dict[str, Any] = {}
        timings: dict[str, Any] = {}
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                if isinstance(event.get("timings"), dict):
                    timings = event["timings"]
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content") or ""
                if content:
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    chunks.append(content)
                extra = choices[0].get("timings")
                if isinstance(extra, dict):
                    timings = extra
        ended = time.perf_counter()

        output_tokens = usage.get("completion_tokens")
        if not isinstance(output_tokens, int):
            try:
                output_tokens = self._token_count(
                    self._json_request("/tokenize", {"content": "".join(chunks)})
                )
            except Exception:
                output_tokens = None
        decode_ms = self._number(timings, "predicted_ms", "generation_ms", "decode_ms")
        output_tps = self._number(timings, "predicted_per_second", "tokens_per_second")
        if output_tps is None and output_tokens is not None and decode_ms and decode_ms > 0:
            output_tps = output_tokens / (decode_ms / 1000.0)
        prefill_ms = self._number(timings, "prompt_ms", "prefill_ms")
        return InferenceMeasurement(
            text="".join(chunks),
            ttft_ms=None if first_token_at is None else (first_token_at - started) * 1000.0,
            prefill_ms=prefill_ms,
            total_latency_ms=(ended - started) * 1000.0,
            output_tokens=output_tokens,
            output_tokens_per_second=output_tps,
            usage=usage,
            timings=timings,
        )

    @staticmethod
    def _number(mapping: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None


class LlamaServerProcess:
    """Starts the existing binary/model without moving or modifying either."""

    def __init__(
        self,
        executable: Path,
        model: Path,
        host: str = "127.0.0.1",
        port: int = 18912,
        context_size: int = 4096,
        threads: int = 8,
        gpu_layers: int = 20,
        log_path: Path | None = None,
    ) -> None:
        self.executable = executable
        self.model = model
        self.host = host
        self.port = port
        self.context_size = context_size
        self.threads = threads
        self.gpu_layers = gpu_layers
        self.log_path = log_path
        self.process: subprocess.Popen[bytes] | None = None
        self._log_handle: Any = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def pid(self) -> int | None:
        return None if self.process is None else self.process.pid

    def start(self, timeout_seconds: float = 180.0) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(f"llama-server bulunamadı: {self.executable}")
        if not self.model.is_file():
            raise FileNotFoundError(f"model bulunamadı: {self.model}")
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_handle = self.log_path.open("ab")
            output = self._log_handle
        else:
            output = subprocess.DEVNULL
        command = [
            str(self.executable),
            "-m", str(self.model),
            "--host", self.host,
            "--port", str(self.port),
            "-c", str(self.context_size),
            "-t", str(self.threads),
            "-ngl", str(self.gpu_layers),
            "--no-webui",
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        runtime = LlamaCppRuntime(self.base_url, timeout_seconds=10.0)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"llama-server erken kapandı (kod {self.process.returncode})")
            if runtime.health():
                return
            time.sleep(0.5)
        self.stop()
        raise TimeoutError("llama-server hazır olma zaman aşımı")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None

    def __enter__(self) -> "LlamaServerProcess":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
