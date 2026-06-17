# RX 7800 XT 8-bit GGUF streaming runtime

This repository does not vendor llama.cpp or a native GGUF runtime. The added path integrates with an externally built llama.cpp binary so the AMD Radeon RX 7800 XT can use ROCm/HIP as the primary backend and Vulkan as a fallback/comparison backend.

## Build llama.cpp for ROCm/HIP

```bash
git clone https://github.com/ggml-org/llama.cpp /opt/llama.cpp
cmake -S /opt/llama.cpp -B /opt/llama.cpp/build-hip \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS=gfx1101 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /opt/llama.cpp/build-hip --config Release -j"$(nproc)"
```

If ROCm does not detect the RX 7800 XT correctly, test with `HSA_OVERRIDE_GFX_VERSION=11.0.1`; do not keep the override if native detection works.

## Vulkan fallback

```bash
cmake -S /opt/llama.cpp -B /opt/llama.cpp/build-vulkan \
  -DGGML_VULKAN=ON \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /opt/llama.cpp/build-vulkan --config Release -j"$(nproc)"
```

## Convert or quantize to Q8_0 GGUF

For an existing GGUF model:

```bash
python server/tools/convert_to_gguf.py \
  --model /models/model-f16.gguf \
  --out /models/model-q8_0.gguf \
  --quant q8_0 \
  --llama-quantize /opt/llama.cpp/build-hip/bin/llama-quantize \
  --llama-cli /opt/llama.cpp/build-hip/bin/llama-cli \
  --report quantization_report.json
```

For a Hugging Face model directory, add `--hf-converter /opt/llama.cpp/convert_hf_to_gguf.py`.

## Run the streaming server

```bash
export RESTORMER_GGUF_MODEL=/models/model-q8_0.gguf
export RESTORMER_LLAMA_CLI=/opt/llama.cpp/build-hip/bin/llama-cli
export RESTORMER_GGUF_PROFILE=conservative
HIP_VISIBLE_DEVICES=0 ROCR_VISIBLE_DEVICES=0 \
uvicorn server.app.gguf.server:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/v1/gguf/health
```

Streaming text request through the OpenAI-shaped endpoint:

```bash
curl -N http://localhost:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"input":"Hello from Q8_0 GGUF","stream":true,"chunk_ms":40,"response_format":"ndjson","max_tokens":64}'
```

The current repository has no TTS/audio decoder or vocoder. The endpoint therefore streams model text deltas and sets `X-Audio-Format: unavailable-text-stream-only` rather than claiming playable audio.

## Recommended RX 7800 XT settings

Conservative default profile:

- `--n-gpu-layers 45`
- `--ctx-size 4096`
- `--batch-size 512`
- `--ubatch-size 128`
- F16 KV cache if using llama-server directly; the Python adapter uses Q8 KV for memory pressure unless adjusted.

Aggressive profile:

- `--n-gpu-layers 999`
- `--ctx-size 8192`
- `--batch-size 2048`
- `--ubatch-size 512`
- `--cache-type-k q8_0 --cache-type-v q8_0`
- `--flash-attn --mlock`

If OOM occurs: reduce context, then batch, then microbatch; disable flash attention if correctness or stability issues appear.

## Benchmark

```bash
python tools/benchmark_rx7800xt_gguf.py \
  --runtime-cmd '/opt/llama.cpp/build-hip/bin/llama-server --model /models/model-q8_0.gguf --host 127.0.0.1 --port 8081 --n-gpu-layers 999 --ctx-size 4096' \
  --base-url http://127.0.0.1:8081 \
  --out-dir benchmark_results/rx7800xt-q8
```

The benchmark writes JSON and Markdown summaries and samples `rocm-smi`/`amd-smi` when available.

## Troubleshooting

- **Backend not detected:** run `rocminfo`, `rocm-smi`, and confirm the llama.cpp binary was built with `GGML_HIP=ON`.
- **Poor GPU utilization:** increase `--n-gpu-layers`, batch, or microbatch after confirming VRAM headroom.
- **OOM:** lower context length and batch sizes; close other GPU processes; avoid multiple Uvicorn workers.
- **Driver/runtime mismatch:** compare ROCm version, kernel driver, and `gfx1101` support; use Vulkan fallback for comparison.
