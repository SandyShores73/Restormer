#!/usr/bin/env python3
"""Create or verify an 8-bit GGUF artifact with llama.cpp tooling.

This wrapper keeps model conversion reproducible without vendoring llama.cpp.
It supports two common paths:
  * GGUF input -> Q8_0 GGUF via llama-quantize
  * HF directory -> F16/BF16 GGUF via convert_hf_to_gguf.py, then Q8_0
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

QTYPE_ALIASES = {"q8": "Q8_0", "q8_0": "Q8_0", "Q8_0": "Q8_0"}


def _size(path: Path) -> int | None:
    return path.stat().st_size if path.exists() and path.is_file() else None


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return proc.returncode, proc.stdout


def _find_binary(explicit: str | None, names: list[str]) -> str | None:
    if explicit:
        return explicit
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _parse_metadata(text: str) -> tuple[dict[str, int], list[str]]:
    counts: Counter[str] = Counter()
    warnings: list[str] = []
    tensor_re = re.compile(r"\b(F32|F16|BF16|Q[0-9A-Z_]+|IQ[0-9A-Z_]+)\b")
    for line in text.splitlines():
        lowered = line.lower()
        if "warn" in lowered or "unsupported" in lowered:
            warnings.append(line.strip())
        if "tensor" in lowered or "type" in lowered:
            for match in tensor_re.findall(line):
                counts[match] += 1
    return dict(counts), warnings


def build_report(args: argparse.Namespace, commands: list[dict[str, Any]], load_output: str = "") -> dict[str, Any]:
    source = Path(args.model)
    output = Path(args.out)
    tensor_counts, warnings = _parse_metadata("\n".join(c.get("output", "") for c in commands) + "\n" + load_output)
    if args.quant.upper() == "Q8_0" and not tensor_counts:
        warnings.append("Tensor type counts were not available from installed llama.cpp tooling; use llama-info for richer reports.")
    return {
        "source_model_path": str(source),
        "output_gguf_path": str(output),
        "quantization_type": args.quant,
        "original_size_bytes": _size(source),
        "quantized_size_bytes": _size(output),
        "tensor_counts_by_dtype_or_quant_type": tensor_counts,
        "preserved_tensors": [],
        "warnings": warnings,
        "commands": commands,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert/quantize a model to 8-bit GGUF (Q8_0).")
    parser.add_argument("--model", required=True, help="Source GGUF file or Hugging Face model directory.")
    parser.add_argument("--out", required=True, help="Output .gguf path.")
    parser.add_argument("--quant", default="q8_0", choices=sorted(QTYPE_ALIASES), help="Quantization type; Q8_0 is currently supported.")
    parser.add_argument("--llama-quantize", help="Path to llama.cpp llama-quantize binary.")
    parser.add_argument("--hf-converter", help="Path to llama.cpp convert_hf_to_gguf.py for HF directories.")
    parser.add_argument("--llama-cli", help="Optional llama-cli/main binary used to verify the output loads.")
    parser.add_argument("--report", default="quantization_report.json", help="Report path.")
    parser.add_argument("--verify-prompt", default="Hello", help="Short prompt for load verification.")
    args = parser.parse_args()
    args.quant = QTYPE_ALIASES[args.quant]

    source = Path(args.model).expanduser().resolve()
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    commands: list[dict[str, Any]] = []
    if not source.exists():
        raise SystemExit(f"source model does not exist: {source}")

    quantize = _find_binary(args.llama_quantize, ["llama-quantize", "quantize"])
    if not quantize:
        raise SystemExit("llama-quantize not found; build llama.cpp with ROCm/HIP or Vulkan and pass --llama-quantize")

    quant_input = source
    tmpdir_obj: tempfile.TemporaryDirectory[str] | None = None
    try:
        if source.is_dir():
            converter = args.hf_converter
            if not converter:
                raise SystemExit("HF directory input requires --hf-converter pointing to llama.cpp convert_hf_to_gguf.py")
            tmpdir_obj = tempfile.TemporaryDirectory(prefix="gguf-f16-")
            quant_input = Path(tmpdir_obj.name) / "model-f16.gguf"
            cmd = [sys.executable, converter, str(source), "--outfile", str(quant_input), "--outtype", "f16"]
            rc, out = _run(cmd)
            commands.append({"command": cmd, "returncode": rc, "output": out[-8000:]})
            if rc != 0 or not quant_input.exists():
                Path(args.report).write_text(json.dumps(build_report(args, commands), indent=2), encoding="utf-8")
                return rc or 1
        cmd = [quantize, str(quant_input), str(output), args.quant]
        rc, out = _run(cmd)
        commands.append({"command": cmd, "returncode": rc, "output": out[-8000:]})
        if rc != 0 or not output.exists():
            Path(args.report).write_text(json.dumps(build_report(args, commands), indent=2), encoding="utf-8")
            return rc or 1

        cli = _find_binary(args.llama_cli, ["llama-cli", "main"])
        load_output = ""
        if cli:
            cmd = [cli, "-m", str(output), "-p", args.verify_prompt, "-n", "1", "--no-display-prompt"]
            rc, load_output = _run(cmd)
            commands.append({"command": cmd, "returncode": rc, "output": load_output[-8000:]})
            if rc != 0:
                commands[-1]["warning"] = "Quantized model was written but load verification failed."
        else:
            commands.append({"command": [], "returncode": None, "output": "llama-cli not found; skipped load verification."})
        Path(args.report).write_text(json.dumps(build_report(args, commands, load_output), indent=2), encoding="utf-8")
        return 0
    finally:
        if tmpdir_obj:
            tmpdir_obj.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
