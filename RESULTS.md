# RESULTS: RX 7800 XT 8-bit GGUF streaming

## Commands run in this environment

- `git status --short --branch`
- `git checkout -b rx7800xt-8bit-gguf-streaming`
- `python -m py_compile server/tools/convert_to_gguf.py server/app/gguf/runtime.py server/app/gguf/api.py server/app/gguf/server.py tools/benchmark_rx7800xt_gguf.py scripts/quantize_to_gguf.py`
- `python server/tools/convert_to_gguf.py --help`
- `python tools/benchmark_rx7800xt_gguf.py --help`
- `python -m pytest tests/test_smoke_scaffolding.py`

## Hardware/runtime details

This container does not expose an AMD Radeon RX 7800 XT, ROCm runtime, Vulkan device, llama.cpp binary, or an 8B GGUF model artifact. GPU utilization, VRAM, time-to-first-token, and throughput must be measured on the target Linux host with the benchmark harness.

## What works

- Added a scriptable Q8_0 GGUF quantization wrapper around llama.cpp tooling that emits `quantization_report.json`.
- Added a standalone FastAPI GGUF server entrypoint with non-streaming and streaming generation modes.
- Added RX 7800 XT backend diagnostics and conservative/aggressive runtime profiles.
- Added benchmark tooling that records latency, streaming jitter, throughput, GPU utilization, VRAM, RAM, backend, quantization, and crash/OOM status when target tools are available.
- Added focused RX 7800 XT documentation.

## What failed or remains blocked

- The repository does not contain a native llama.cpp/GGUF runtime, so llama.cpp must be built externally.
- The repository does not contain a TTS/audio decoder or vocoder, so `/v1/audio/speech` streams text deltas only and explicitly marks audio as unavailable.
- The checked-in server/client files appear to contain patch transcripts rather than directly runnable source, so the GGUF server is exposed as `server.app.gguf.server:app` instead of modifying the existing main app.
- No real 8B model was present, so model load verification and GPU benchmarks were not run here.

## Recommended RX 7800 XT config

Start with the conservative profile for stability:

```bash
export RESTORMER_GGUF_MODEL=/models/model-q8_0.gguf
export RESTORMER_LLAMA_CLI=/opt/llama.cpp/build-hip/bin/llama-cli
export RESTORMER_GGUF_PROFILE=conservative
HIP_VISIBLE_DEVICES=0 ROCR_VISIBLE_DEVICES=0 \
uvicorn server.app.gguf.server:app --host 0.0.0.0 --port 8000
```

After confirming VRAM headroom and correctness, test `RESTORMER_GGUF_PROFILE=aggressive` and compare benchmark output.
