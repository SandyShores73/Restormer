# GGUF quantization path

Use `scripts/quantize_to_gguf.py` to convert a Restormer PyTorch checkpoint
(`.pth`/`.pt`) or NumPy archive (`.npz`) into a GGUF v3 file. The default path
writes Q8_0 8-bit blocks for floating-point tensors whose element count is
compatible with GGML Q8_0 block packing. Tensors that cannot be safely packed
(for example, tensors with a non-multiple-of-32 element count) are preserved as
F16 and listed in the report.

```bash
python scripts/quantize_to_gguf.py \
  --source path/to/restormer.pth \
  --output artifacts/restormer-q8_0.gguf \
  --quant-type q8_0 \
  --report artifacts/quantization_report.json
```

The report is always JSON and contains:

- `source` and `output` paths.
- `quant_type` requested for the conversion.
- input/output byte sizes.
- total, written, preserved, and skipped tensor counts.
- exact tensor names preserved outside the requested quantization type.
- warnings produced while loading or packing the checkpoint.

For smoke tests without a PyTorch checkpoint, create a small `.npz` archive and
run the same command against it.
