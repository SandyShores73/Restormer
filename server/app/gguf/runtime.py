"""Thin llama.cpp runtime adapter for GGUF inference and streaming.

The repository does not vendor a GGUF runtime. This module integrates with an
externally built llama.cpp command-line binary so Linux ROCm/HIP and Vulkan
builds can be swapped without changing the FastAPI API surface.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator


@dataclass(frozen=True)
class GgufProfile:
    name: str
    backend: str = "hip"
    gpu_layers: int = 999
    ctx_size: int = 4096
    batch_size: int = 1024
    ubatch_size: int = 256
    threads: int = max(1, (os.cpu_count() or 8) // 2)
    flash_attention: bool = True
    extra_args: tuple[str, ...] = field(default_factory=tuple)


PROFILES = {
    "conservative": GgufProfile(
        name="conservative",
        gpu_layers=45,
        ctx_size=4096,
        batch_size=512,
        ubatch_size=128,
        extra_args=("--cache-type-k", "q8_0", "--cache-type-v", "q8_0"),
    ),
    "aggressive": GgufProfile(
        name="aggressive",
        gpu_layers=999,
        ctx_size=8192,
        batch_size=2048,
        ubatch_size=512,
        extra_args=("--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--mlock"),
    ),
}


@dataclass(frozen=True)
class RuntimeConfig:
    model_path: Path
    llama_cli: str = "llama-cli"
    profile: GgufProfile = PROFILES["conservative"]
    default_predict_tokens: int = 256

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        model = os.environ.get("RESTORMER_GGUF_MODEL")
        if not model:
            raise RuntimeError("RESTORMER_GGUF_MODEL must point to a Q8_0 GGUF model")
        profile_name = os.environ.get("RESTORMER_GGUF_PROFILE", "conservative")
        profile = PROFILES.get(profile_name)
        if profile is None:
            raise RuntimeError(f"unknown RESTORMER_GGUF_PROFILE={profile_name!r}; expected one of {sorted(PROFILES)}")
        return cls(
            model_path=Path(model),
            llama_cli=os.environ.get("RESTORMER_LLAMA_CLI", "llama-cli"),
            profile=profile,
            default_predict_tokens=int(os.environ.get("RESTORMER_GGUF_N_PREDICT", "256")),
        )

    def command(self, prompt: str, n_predict: int | None = None) -> list[str]:
        if not self.model_path.exists():
            raise FileNotFoundError(f"GGUF model not found: {self.model_path}")
        binary = shutil.which(self.llama_cli) or self.llama_cli
        cmd = [
            binary,
            "-m", str(self.model_path),
            "-p", prompt,
            "-n", str(n_predict if n_predict is not None else self.default_predict_tokens),
            "--ctx-size", str(self.profile.ctx_size),
            "--batch-size", str(self.profile.batch_size),
            "--ubatch-size", str(self.profile.ubatch_size),
            "--threads", str(self.profile.threads),
            "--n-gpu-layers", str(self.profile.gpu_layers),
            "--no-display-prompt",
        ]
        if self.profile.flash_attention:
            cmd.append("--flash-attn")
        cmd.extend(self.profile.extra_args)
        return cmd


def backend_snapshot() -> dict[str, str | None]:
    """Return lightweight backend diagnostics for startup logs/benchmarks."""
    def version(cmd: list[str]) -> str | None:
        try:
            return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3, check=False).stdout.strip()[:2000]
        except (OSError, subprocess.SubprocessError):
            return None
    return {
        "rocm_smi": version(["rocm-smi", "--showproductname", "--showmeminfo", "vram"]),
        "amd_smi": version(["amd-smi", "static", "--gpu", "0"]),
        "vulkaninfo": version(["vulkaninfo", "--summary"]),
        "hip_visible_devices": os.environ.get("HIP_VISIBLE_DEVICES"),
        "rocr_visible_devices": os.environ.get("ROCR_VISIBLE_DEVICES"),
    }


async def generate_text(config: RuntimeConfig, prompt: str, n_predict: int | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(*config.command(prompt, n_predict), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode("utf-8", "replace")[-2000:]
        raise RuntimeError(f"llama.cpp generation failed with code {proc.returncode}: {err}")
    return stdout.decode("utf-8", "replace")


async def stream_text(config: RuntimeConfig, prompt: str, n_predict: int | None = None) -> AsyncIterator[tuple[bytes, float]]:
    start = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(*config.command(prompt, n_predict), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    assert proc.stdout is not None
    try:
        while True:
            chunk = await proc.stdout.read(128)
            if not chunk:
                break
            yield chunk, time.perf_counter() - start
    except asyncio.CancelledError:
        proc.terminate()
        raise
    finally:
        if proc.returncode is None:
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                proc.kill()
