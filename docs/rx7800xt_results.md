# RX 7800 XT smoke benchmark RESULTS

Focused scaffold for recording Restormer backend smoke checks on the target AMD Radeon RX 7800 XT workstation. Keep this file to command lines, environment notes, and compact result tables.

## Hardware target

- GPU: AMD Radeon RX 7800 XT
- OS target: Windows 11
- Backend acceleration path: ONNX Runtime DirectML
- Baseline path: CPU

## Smoke commands

Run from the repository root after installing server dependencies.

```powershell
python benchmarks/rx7800xt_smoke.py --mode cpu --image-size 512 --warmup-runs 1 --measured-runs 3
python benchmarks/rx7800xt_smoke.py --mode directml --image-size 512 --warmup-runs 1 --measured-runs 3
```

Optional larger input check:

```powershell
python benchmarks/rx7800xt_smoke.py --mode directml --image-size 1024 --warmup-runs 1 --measured-runs 3
```

## RESULTS

| Date | Commit | Mode | Image size | Warmup | Runs | Median latency | Peak VRAM | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| TBD | TBD | cpu | 512 | 1 | 3 | TBD | N/A | Baseline smoke |
| TBD | TBD | directml | 512 | 1 | 3 | TBD | TBD | RX 7800 XT smoke |

## Acceptance checklist

- CPU smoke command completes and emits JSON.
- DirectML smoke command completes on the RX 7800 XT host.
- DirectML result records driver version and any provider fallback warnings.
- Any benchmark using real images lists input dimensions and model artifact names.
