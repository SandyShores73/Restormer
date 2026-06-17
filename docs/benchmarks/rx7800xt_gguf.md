# RX 7800 XT GGUF benchmark harness

Use `tools/benchmark_rx7800xt_gguf.py` to run a small, reproducible GGUF runtime benchmark on an AMD Radeon RX 7800 XT host. The harness starts the runtime command you provide, waits for a health endpoint, runs four built-in cases, and writes compact JSON plus Markdown summaries under `benchmark_results/rx7800xt_gguf/` by default.

Measured fields include load time, time to first output (TTFO, including first audio bytes for audio endpoints), total time, real-time factor when `--audio-seconds` is supplied, throughput, streaming chunk jitter, GPU utilisation, VRAM, RAM, backend, quantisation, and crash/error state.

## Example: llama.cpp server

```bash
python tools/benchmark_rx7800xt_gguf.py \
  --model /models/model.Q4_K_M.gguf \
  --backend vulkan \
  --command ./llama-server -m /models/model.Q4_K_M.gguf --port 8080 -ngl 999 \
  --endpoint http://127.0.0.1:8080/completion \
  --health-url http://127.0.0.1:8080/health
```

The built-in matrix is intentionally small:

| case | preset | stream | generated units |
| --- | --- | --- | --- |
| conservative_stream | conservative | yes | 64 |
| conservative_nonstream | conservative | no | 64 |
| aggressive_stream | aggressive | yes | 256 |
| aggressive_nonstream | aggressive | no | 256 |

For audio GGUF runtimes, point `--endpoint` at the JSON endpoint that returns streaming or non-streaming audio/text bytes and pass `--audio-seconds` with the input duration to compute RTF.

Do not commit files generated in `benchmark_results/`; they are ignored except for optional tiny hand-curated examples.
