from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_core_scaffold_mentions_expected_entrypoints() -> None:
    readme = read("README.md")
    server_readme = read("server/README.md")
    client_package = read("client/package.json")

    assert "Restormer" in readme
    assert "uvicorn app.main:app" in server_readme
    assert '"build:renderer": "vite build"' in client_package


def test_rx7800xt_results_doc_has_reproducible_commands() -> None:
    results = read("docs/rx7800xt_results.md")

    assert "RX 7800 XT" in results
    assert "python benchmarks/rx7800xt_smoke.py --mode cpu" in results
    assert "python benchmarks/rx7800xt_smoke.py --mode directml" in results
    assert "RESULTS" in results


def test_benchmark_smoke_script_exposes_cli_modes() -> None:
    script = read("benchmarks/rx7800xt_smoke.py")

    assert "--mode" in script
    assert "directml" in script
    assert "cpu" in script
    assert "--image-size" in script
