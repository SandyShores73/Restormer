# RX 7800 XT 8-bit GGUF Streaming Plan

## Relevant repo map

- `server/` is the only relevant serving/backend area for adding model-runtime integration.
- `server/app/main.py` and several existing files currently appear to contain patch-transcript text, so new GGUF serving code will be isolated under `server/app/gguf/` with a standalone FastAPI entrypoint.
- `server/tools/` is the appropriate focused location for conversion/quantization wrappers.
- `tools/` and `benchmarks/` are appropriate for reproducible benchmark harnesses and small scaffolding only.
- `README_RX7800XT.md` and `RESULTS.md` will document hardware-specific operation and validation.

## Files/directories that will not be touched

- `client/node_modules/` generated dependency tree.
- Existing Electron UI files under `client/` unless an API compatibility change requires it.
- Auth/user/OAuth code and unrelated publishing docs.
- Unrelated source formatting or repository restructuring.

## Backend/runtime discovery

No native llama.cpp, GGUF loader, GGUF converter, ROCm/HIP, HIPBLAS, Vulkan, or custom GGUF runtime was present in the repository. Existing documentation points to an ONNX/DirectML image-restoration app, which does not satisfy the Linux RX 7800 XT GGUF target. The implementation will therefore add a thin integration around externally built llama.cpp tools rather than vendoring a large runtime.

## 8-bit conversion plan

- Add `server/tools/convert_to_gguf.py` to drive llama.cpp `llama-quantize`.
- Support existing GGUF to Q8_0 directly.
- Support Hugging Face directories when a llama.cpp `convert_hf_to_gguf.py` path is supplied.
- Emit `quantization_report.json` with source/output paths, quantization type, byte sizes, tensor type counts when available, preserved tensors, warnings, and command records.
- Verify loadability with `llama-cli` when available.

## Streaming design

- Add `server/app/gguf/runtime.py` for subprocess-based llama.cpp generation and streaming.
- Add `server/app/gguf/api.py` with an OpenAI-shaped `/v1/audio/speech` route preserving non-streaming JSON behavior and adding `stream=true` low-latency chunking.
- Add `server/app/gguf/server.py` as a standalone `uvicorn` target because the existing main app is not safely importable in this snapshot.
- Explicitly document that no audio decoder/vocoder exists in this repo; stream text deltas without claiming playable audio.

## RX 7800 XT optimization plan

- Prefer llama.cpp ROCm/HIP build with `GGML_HIP=ON` and `AMDGPU_TARGETS=gfx1101`.
- Provide Vulkan fallback build with `GGML_VULKAN=ON`.
- Add conservative profile for stability on 16 GB VRAM and aggressive profile for throughput/latency exploration.
- Log/surface backend diagnostics from `rocm-smi`, `amd-smi`, `vulkaninfo`, and visible-device environment variables.

## Test/benchmark plan

- Compile new Python modules.
- Run converter and benchmark `--help` commands.
- Run existing smoke benchmark scaffold and pytest smoke tests.
- Add/use `tools/benchmark_rx7800xt_gguf.py` for target-host JSON and Markdown benchmark results including TTFO, total time, throughput, jitter, GPU utilization, VRAM, RAM, backend, quantization type, and crash/OOM state.

## Risks and fallback paths

- No real 8B GGUF model or RX 7800 XT is available in this container, so target performance cannot be claimed here.
- No TTS/audio model is available, so audio streaming is blocked and documented; the useful partial path is text streaming through the OpenAI-shaped endpoint.
- If ROCm/HIP is unstable on the target host, build and benchmark the Vulkan llama.cpp backend for comparison.
