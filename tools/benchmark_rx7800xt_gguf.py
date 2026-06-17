#!/usr/bin/env python3
"""Small reproducible GGUF benchmark harness for Radeon RX 7800 XT hosts.

The harness starts a configurable GGUF runtime (for example llama.cpp's
`llama-server`), runs conservative/aggressive and streaming/non-streaming cases,
and writes compact JSON plus Markdown summaries. It is dependency-free and keeps
all generated artifacts under the selected output directory.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


DEFAULT_CASES = [
    {"name": "conservative_stream", "preset": "conservative", "stream": True, "n_predict": 64, "temperature": 0.2},
    {"name": "conservative_nonstream", "preset": "conservative", "stream": False, "n_predict": 64, "temperature": 0.2},
    {"name": "aggressive_stream", "preset": "aggressive", "stream": True, "n_predict": 256, "temperature": 0.7},
    {"name": "aggressive_nonstream", "preset": "aggressive", "stream": False, "n_predict": 256, "temperature": 0.7},
]


@dataclass
class Sample:
    ts: float
    gpu_util_pct: float | None = None
    vram_used_mib: float | None = None
    ram_used_mib: float | None = None


@dataclass
class CaseResult:
    name: str
    preset: str
    stream: bool
    prompt_chars: int
    n_predict: int
    load_time_s: float | None
    ttfo_s: float | None
    total_time_s: float | None
    rtf: float | None
    throughput_units_per_s: float | None
    output_units: int
    chunk_count: int
    chunk_jitter_ms: float | None
    gpu_util_avg_pct: float | None
    gpu_util_max_pct: float | None
    vram_peak_mib: float | None
    ram_peak_mib: float | None
    backend: str
    quant: str | None
    crashed: bool
    error: str | None = None


@dataclass
class BenchmarkReport:
    created_utc: str
    host: dict[str, Any]
    runtime_command: list[str]
    model: str | None
    endpoint: str
    health_url: str | None
    cases: list[CaseResult] = field(default_factory=list)


def now() -> float:
    return time.perf_counter()


def iso_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ram_used_mib() -> float | None:
    if platform.system() == "Linux":
        try:
            info = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                key, value = line.split(":", 1)
                info[key] = float(value.strip().split()[0]) / 1024.0
            return info.get("MemTotal", 0.0) - info.get("MemAvailable", 0.0)
        except Exception:
            return None
    return None


def parse_first_number(text: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def gpu_sample() -> tuple[float | None, float | None]:
    """Return (GPU util %, VRAM MiB) using AMD tools when available."""
    amd_smi = shutil.which("amd-smi")
    if amd_smi:
        try:
            out = subprocess.check_output([amd_smi, "metric", "--json"], text=True, stderr=subprocess.DEVNULL, timeout=2)
            data = json.loads(out)
            flat = json.dumps(data)
            util = parse_first_number(" ".join(re.findall(r'usage[^0-9-]*([-+]?\d+(?:\.\d+)?)', flat, re.I)))
            vram = parse_first_number(" ".join(re.findall(r'vram[^0-9-]*([-+]?\d+(?:\.\d+)?)', flat, re.I)))
            return util, vram
        except Exception:
            pass
    rocm_smi = shutil.which("rocm-smi")
    if rocm_smi:
        try:
            out = subprocess.check_output([rocm_smi, "--showuse", "--showmemuse", "--csv"], text=True, stderr=subprocess.DEVNULL, timeout=2)
            util = parse_first_number(out)
            mem = re.search(r"(\d+(?:\.\d+)?)\s*%", out)
            return util, float(mem.group(1)) if mem else None
        except Exception:
            pass
    return None, None


def infer_backend(command: list[str]) -> str:
    text = " ".join(command).lower()
    if "vulkan" in text:
        return "vulkan"
    if "hip" in text or "rocm" in text:
        return "rocm/hip"
    if "directml" in text or "dml" in text:
        return "directml"
    if "cuda" in text:
        return "cuda"
    return "unknown"


def infer_quant(model: str | None) -> str | None:
    if not model:
        return None
    m = re.search(r"\b(q\d(?:_[a-z0-9]+)+|iq\d_[a-z0-9_]+|f16|bf16|f32)\b", Path(model).name, re.I)
    return m.group(1).upper() if m else None


def post_json(url: str, payload: dict[str, Any], stream: bool) -> tuple[float | None, float, int, list[float], str]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    start = now(); first = None; chunks = []; size = 0; text_parts = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        if stream:
            while True:
                chunk = resp.readline()
                if not chunk:
                    break
                t = now()
                if first is None:
                    first = t
                chunks.append(t)
                size += len(chunk)
                text_parts.append(chunk.decode("utf-8", errors="ignore"))
        else:
            data = resp.read()
            first = now()
            size = len(data)
            text_parts.append(data.decode("utf-8", errors="ignore"))
    return (first - start if first else None), now() - start, size, chunks, "".join(text_parts)


def wait_health(url: str | None, timeout_s: float) -> float | None:
    if not url:
        return None
    start = now()
    while now() - start < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return now() - start
        except urllib.error.URLError:
            time.sleep(0.25)
    return None


def percentile(values: Iterable[float]) -> float | None:
    vals = list(values)
    return statistics.pstdev(vals) if len(vals) > 1 else None


def run_case(case: dict[str, Any], args: argparse.Namespace, load_time: float | None, proc: subprocess.Popen[str] | None) -> CaseResult:
    samples: list[Sample] = []
    payload = {"prompt": args.prompt, "n_predict": case["n_predict"], "temperature": case["temperature"], "stream": case["stream"]}
    crashed = False; error = None
    try:
        t0 = now()
        ttfo, total, units, chunk_times, text = post_json(args.endpoint, payload, case["stream"])
        samples.append(Sample(now(), *gpu_sample(), ram_used_mib()))
        crashed = bool(proc and proc.poll() is not None)
    except Exception as exc:
        total = now() - t0 if "t0" in locals() else None
        ttfo = None; units = 0; chunk_times = [] ; text = ""
        crashed = bool(proc and proc.poll() is not None)
        error = str(exc)
    for _ in range(2):
        samples.append(Sample(now(), *gpu_sample(), ram_used_mib()))
        time.sleep(0.1)
    intervals = [(b - a) * 1000 for a, b in zip(chunk_times, chunk_times[1:])]
    audio_s = args.audio_seconds if args.audio_seconds and args.audio_seconds > 0 else None
    return CaseResult(
        name=case["name"], preset=case["preset"], stream=case["stream"], prompt_chars=len(args.prompt),
        n_predict=case["n_predict"], load_time_s=load_time, ttfo_s=ttfo, total_time_s=total,
        rtf=(total / audio_s if total and audio_s else None),
        throughput_units_per_s=(units / total if total and total > 0 else None), output_units=units,
        chunk_count=len(chunk_times), chunk_jitter_ms=percentile(intervals),
        gpu_util_avg_pct=statistics.mean([s.gpu_util_pct for s in samples if s.gpu_util_pct is not None]) if any(s.gpu_util_pct is not None for s in samples) else None,
        gpu_util_max_pct=max([s.gpu_util_pct for s in samples if s.gpu_util_pct is not None], default=None),
        vram_peak_mib=max([s.vram_used_mib for s in samples if s.vram_used_mib is not None], default=None),
        ram_peak_mib=max([s.ram_used_mib for s in samples if s.ram_used_mib is not None], default=None),
        backend=args.backend or infer_backend(args.command), quant=args.quant or infer_quant(args.model), crashed=crashed, error=error,
    )


def write_markdown(report: BenchmarkReport, path: Path) -> None:
    headers = ["case", "stream", "load_s", "ttfo_s", "total_s", "rtf", "throughput", "jitter_ms", "gpu_avg", "vram_peak", "ram_peak", "backend", "quant", "crash"]
    lines = ["# RX 7800 XT GGUF Benchmark", "", f"Created: `{report.created_utc}`", "", "| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for c in report.cases:
        def f(v: Any) -> str:
            return "" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))
        lines.append("| " + " | ".join(f(x) for x in [c.name, c.stream, c.load_time_s, c.ttfo_s, c.total_time_s, c.rtf, c.throughput_units_per_s, c.chunk_jitter_ms, c.gpu_util_avg_pct, c.vram_peak_mib, c.ram_peak_mib, c.backend, c.quant, c.crashed]) + " |")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--command", nargs="+", required=True, help="Runtime command to start, e.g. llama-server -m model.gguf --port 8080 -ngl 999")
    p.add_argument("--endpoint", default="http://127.0.0.1:8080/completion")
    p.add_argument("--health-url", default="http://127.0.0.1:8080/health")
    p.add_argument("--model")
    p.add_argument("--backend")
    p.add_argument("--quant")
    p.add_argument("--prompt", default="Write a concise benchmark paragraph about GPU audio restoration.")
    p.add_argument("--audio-seconds", type=float, help="Set when prompt/input represents audio to report real-time factor.")
    p.add_argument("--out-dir", default="benchmark_results/rx7800xt_gguf")
    p.add_argument("--startup-timeout", type=float, default=120)
    args = p.parse_args()

    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(args.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    try:
        load_time = wait_health(args.health_url, args.startup_timeout)
        report = BenchmarkReport(iso_utc(), {"platform": platform.platform(), "python": sys.version.split()[0], "cpu": platform.processor(), "target_gpu": "AMD Radeon RX 7800 XT"}, args.command, args.model, args.endpoint, args.health_url)
        for case in DEFAULT_CASES:
            report.cases.append(run_case(case, args, load_time, proc))
        stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        json_path = out / f"rx7800xt_gguf_{stamp}.json"
        md_path = out / f"rx7800xt_gguf_{stamp}.md"
        json_path.write_text(json.dumps(asdict(report), indent=2) + "\n")
        write_markdown(report, md_path)
        print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, indent=2))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
