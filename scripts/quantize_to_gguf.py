#!/usr/bin/env python3
"""Convert Restormer-style checkpoints to a scriptable 8-bit GGUF artifact.

The converter is intentionally dependency-light: PyTorch is used only to load
`.pt`/`.pth` checkpoints, while GGUF writing and Q8_0 packing are implemented
locally so the path can run in CI or release automation without llama.cpp.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

GGUF_ALIGN = 32
GGML_TYPE_F32 = 0
GGML_TYPE_F16 = 1
GGML_TYPE_Q8_0 = 8
GGUF_VALUE_UINT32 = 4
GGUF_VALUE_STRING = 8
QK8_0 = 32


@dataclass
class TensorRecord:
    name: str
    shape: tuple[int, ...]
    ggml_type: int
    data: bytes
    offset: int = 0


def _align(value: int, alignment: int = GGUF_ALIGN) -> int:
    return (value + alignment - 1) // alignment * alignment


def _pack_string(text: str) -> bytes:
    raw = text.encode("utf-8")
    return struct.pack("<Q", len(raw)) + raw


def _pack_kv_string(key: str, value: str) -> bytes:
    return _pack_string(key) + struct.pack("<I", GGUF_VALUE_STRING) + _pack_string(value)


def _pack_kv_u32(key: str, value: int) -> bytes:
    return _pack_string(key) + struct.pack("<II", GGUF_VALUE_UINT32, value)


def _unwrap_state_dict(obj: Any, warnings: list[str]) -> dict[str, Any]:
    if isinstance(obj, dict):
        for key in ("state_dict", "model", "params", "net", "network"):
            candidate = obj.get(key)
            if isinstance(candidate, dict):
                warnings.append(f"using nested checkpoint key '{key}' as tensor source")
                return candidate
        return obj
    raise TypeError(f"unsupported checkpoint object: {type(obj)!r}")


def _load_checkpoint(path: Path, warnings: list[str]) -> dict[str, Any]:
    if path.suffix == ".npz":
        loaded = np.load(path, allow_pickle=False)
        return {name: loaded[name] for name in loaded.files}

    try:
        import torch
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("PyTorch is required to read .pt/.pth checkpoints") from exc

    obj = torch.load(path, map_location="cpu")
    return _unwrap_state_dict(obj, warnings)


def _as_numpy(value: Any) -> np.ndarray | None:
    if isinstance(value, np.ndarray):
        return value
    if hasattr(value, "detach") and hasattr(value, "cpu") and hasattr(value, "numpy"):
        return value.detach().cpu().numpy()
    return None


def _quantize_q8_0(array: np.ndarray) -> bytes:
    flat = np.ascontiguousarray(array.astype(np.float32, copy=False)).reshape(-1, QK8_0)
    chunks: list[bytes] = []
    for block in flat:
        absmax = float(np.max(np.abs(block)))
        scale = absmax / 127.0 if absmax else 0.0
        quants = np.zeros(QK8_0, dtype=np.int8) if scale == 0.0 else np.rint(block / scale).clip(-127, 127).astype(np.int8)
        chunks.append(np.float16(scale).tobytes() + quants.tobytes())
    return b"".join(chunks)


def _tensor_bytes(array: np.ndarray, quant_type: str, warnings: list[str], name: str) -> tuple[int, bytes, bool]:
    if quant_type == "f32":
        return GGML_TYPE_F32, np.ascontiguousarray(array.astype(np.float32, copy=False)).tobytes(), False
    if quant_type == "f16":
        return GGML_TYPE_F16, np.ascontiguousarray(array.astype(np.float16)).tobytes(), False

    if not np.issubdtype(array.dtype, np.floating):
        warnings.append(f"preserved non-floating tensor '{name}' as F32-compatible data")
        return GGML_TYPE_F32, np.ascontiguousarray(array.astype(np.float32)).tobytes(), True
    if array.size == 0 or array.size % QK8_0 != 0:
        warnings.append(f"preserved tensor '{name}' as F16 because element count is not divisible by {QK8_0}")
        return GGML_TYPE_F16, np.ascontiguousarray(array.astype(np.float16)).tobytes(), True
    return GGML_TYPE_Q8_0, _quantize_q8_0(array), False


def _write_gguf(path: Path, records: Iterable[TensorRecord], metadata: list[bytes]) -> None:
    records = list(records)
    offset = 0
    for rec in records:
        rec.offset = offset
        offset = _align(offset + len(rec.data))

    with path.open("wb") as handle:
        handle.write(b"GGUF")
        handle.write(struct.pack("<IQQ", 3, len(records), len(metadata)))
        for kv in metadata:
            handle.write(kv)
        for rec in records:
            handle.write(_pack_string(rec.name))
            handle.write(struct.pack("<I", len(rec.shape)))
            for dim in rec.shape:
                handle.write(struct.pack("<Q", dim))
            handle.write(struct.pack("<IQ", rec.ggml_type, rec.offset))
        pad = _align(handle.tell()) - handle.tell()
        handle.write(b"\0" * pad)
        data_start = handle.tell()
        for rec in records:
            handle.seek(data_start + rec.offset)
            handle.write(rec.data)
            pad = _align(handle.tell()) - handle.tell()
            handle.write(b"\0" * pad)


def convert(args: argparse.Namespace) -> dict[str, Any]:
    warnings: list[str] = []
    source = Path(args.source)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(args.tensor_regex) if args.tensor_regex else None

    state = _load_checkpoint(source, warnings)
    records: list[TensorRecord] = []
    skipped: list[str] = []
    preserved: list[str] = []

    for name, value in state.items():
        if pattern and not pattern.search(name):
            skipped.append(name)
            continue
        array = _as_numpy(value)
        if array is None:
            skipped.append(name)
            continue
        ggml_type, data, was_preserved = _tensor_bytes(array, args.quant_type, warnings, name)
        if was_preserved:
            preserved.append(name)
        records.append(TensorRecord(name=name, shape=tuple(int(d) for d in array.shape), ggml_type=ggml_type, data=data))

    if not records:
        raise RuntimeError("no tensors were found for GGUF export")

    metadata = [
        _pack_kv_string("general.architecture", "restormer"),
        _pack_kv_string("general.name", source.stem),
        _pack_kv_u32("general.quantization_version", 2),
        _pack_kv_u32("general.file_type", GGML_TYPE_Q8_0 if args.quant_type == "q8_0" else records[0].ggml_type),
    ]
    _write_gguf(output, records, metadata)

    report = {
        "source": str(source),
        "output": str(output),
        "quant_type": args.quant_type,
        "sizes": {"source_bytes": source.stat().st_size, "output_bytes": output.stat().st_size},
        "tensor_counts": {"total_keys": len(state), "written": len(records), "preserved": len(preserved), "skipped": len(skipped)},
        "preserved": preserved,
        "warnings": warnings,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a Restormer checkpoint to GGUF with optional Q8_0 quantization.")
    parser.add_argument("--source", required=True, help="Input .pth/.pt checkpoint or .npz tensor archive.")
    parser.add_argument("--output", required=True, help="Output .gguf path.")
    parser.add_argument("--quant-type", choices=("q8_0", "f16", "f32"), default="q8_0")
    parser.add_argument("--report", default="quantization_report.json", help="JSON report path.")
    parser.add_argument("--tensor-regex", help="Optional regex limiting which tensor names are exported.")
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(convert(parse_args()), indent=2))
