"""Concurrent RAM/VRAM sampling with explicit measurement scope."""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ResourceMeasurement:
    process_ram_start_mb: float | None
    process_ram_peak_mb: float | None
    process_ram_delta_mb: float | None
    system_ram_start_mb: float | None
    system_ram_peak_mb: float | None
    gpu_vram_start_mb: float | None
    gpu_vram_peak_mb: float | None
    gpu_vram_delta_mb: float | None
    gpu_scope: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResourceSampler:
    def __init__(self, process_id: int | None, interval_seconds: float = 0.05) -> None:
        self.process_id = process_id
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._process_values: list[float] = []
        self._system_values: list[float] = []
        self._gpu_values: list[float] = []

    def start(self) -> None:
        self._sample()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> ResourceMeasurement:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._sample()
        return ResourceMeasurement(
            process_ram_start_mb=self._first(self._process_values),
            process_ram_peak_mb=self._max(self._process_values),
            process_ram_delta_mb=self._delta(self._process_values),
            system_ram_start_mb=self._first(self._system_values),
            system_ram_peak_mb=self._max(self._system_values),
            gpu_vram_start_mb=self._first(self._gpu_values),
            gpu_vram_peak_mb=self._max(self._gpu_values),
            gpu_vram_delta_mb=self._delta(self._gpu_values),
            gpu_scope="GPU toplam kullanımı; süreç özel değil" if self._gpu_values else "ölçülemedi",
        )

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._sample()

    def _sample(self) -> None:
        try:
            import psutil  # type: ignore

            if self.process_id is not None:
                self._process_values.append(psutil.Process(self.process_id).memory_info().rss / 1048576)
            self._system_values.append(psutil.virtual_memory().used / 1048576)
        except (ImportError, OSError):
            pass
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            completed = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=creationflags,
                check=False,
            )
            if completed.returncode == 0:
                values = [float(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
                if values:
                    self._gpu_values.append(sum(values))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass

    @staticmethod
    def _first(values: list[float]) -> float | None:
        return None if not values else round(values[0], 3)

    @staticmethod
    def _max(values: list[float]) -> float | None:
        return None if not values else round(max(values), 3)

    @staticmethod
    def _delta(values: list[float]) -> float | None:
        return None if not values else round(max(values) - values[0], 3)
