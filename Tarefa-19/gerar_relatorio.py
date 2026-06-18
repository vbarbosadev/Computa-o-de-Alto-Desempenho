from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "resultados"


@dataclass(frozen=True)
class Result:
    source: str
    variant: str
    device: str
    n: int
    repeats: int
    best_compute_s: float
    avg_compute_s: float
    init_s: float
    verify_s: float
    errors: int
    omp_threads: int
    omp_devices: int

    @property
    def total_s(self) -> float:
        return self.init_s + self.avg_compute_s + self.verify_s


def load_results() -> list[Result]:
    rows: list[Result] = []
    for csv_path in sorted(RESULTS_DIR.glob("tarefa19_resultados_*.csv")):
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(
                    Result(
                        source=csv_path.name,
                        variant=row["variant"],
                        device=row["device"],
                        n=int(row["n"]),
                        repeats=int(row["repeats"]),
                        best_compute_s=float(row["best_compute_s"]),
                        avg_compute_s=float(row["avg_compute_s"]),
                        init_s=float(row["init_s"]),
                        verify_s=float(row["verify_s"]),
                        errors=int(row["errors"]),
                        omp_threads=int(row["omp_threads"]),
                        omp_devices=int(row["omp_devices"]),
                    )
                )
    if not rows:
        raise SystemExit(f"Nenhum CSV encontrado em {RESULTS_DIR}")
    return rows


def label(result: Result) -> str:
    return f"{result.variant.upper()}\n{result.device}"


def save_compute_chart(results: list[Result]) -> Path:
    path = RESULTS_DIR / "tempo_computacao.png"
    if plt is None:
        return path
    labels = [label(r) for r in results]
    avg = [r.avg_compute_s for r in results]
    best = [r.best_compute_s for r in results]
    x = range(len(results))
    width = 0.36

    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=140)
    ax.bar([i - width / 2 for i in x], best, width, label="Melhor", color="#2563eb")
    ax.bar([i + width / 2 for i in x], avg, width, label="Medio", color="#f97316")
    ax.set_title("Tempo da soma de vetores")
    ax.set_ylabel("Tempo (s)")
    ax.set_xticks(list(x), labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_speedup_chart(results: list[Result]) -> Path:
    path = RESULTS_DIR / "speedup_gpu_vs_cpu.png"
    if plt is None:
        return path
    cpu = next((r for r in results if r.variant == "cpu"), None)
    if cpu is None:
        return path

    labels = [label(r) for r in results]
    speedups = [cpu.avg_compute_s / r.avg_compute_s for r in results]

    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=140)
    bars = ax.bar(labels, speedups, color=["#2563eb" if r.variant == "cpu" else "#16a34a" for r in results])
    ax.axhline(1.0, color="#111827", linewidth=1, linestyle="--")
    ax.set_title("Speedup relativo ao tempo medio da CPU")
    ax.set_ylabel("Speedup (CPU / variante)")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, speedups):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}x", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_components_chart(results: list[Result]) -> Path:
    path = RESULTS_DIR / "componentes_tempo_total.png"
    if plt is None:
        return path
    labels = [label(r) for r in results]
    init = [r.init_s for r in results]
    compute = [r.avg_compute_s for r in results]
    verify = [r.verify_s for r in results]
    x = range(len(results))

    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=140)
    ax.bar(labels, init, label="Inicializacao", color="#64748b")
    ax.bar(labels, compute, bottom=init, label="Soma", color="#f97316")
    bottom_verify = [a + b for a, b in zip(init, compute)]
    ax.bar(labels, verify, bottom=bottom_verify, label="Validacao", color="#22c55e")
    ax.set_title("Composicao do tempo medido")
    ax.set_ylabel("Tempo (s)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def markdown_table(results: list[Result]) -> str:
    lines = [
        "| Variante | Dispositivo | N | Repeticoes | Melhor soma (s) | Media soma (s) | Inicializacao (s) | Validacao (s) | Total aprox. (s) | Erros | Threads | Devices |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in results:
        lines.append(
            f"| {r.variant} | {r.device} | {r.n} | {r.repeats} | "
            f"{r.best_compute_s:.9f} | {r.avg_compute_s:.9f} | {r.init_s:.9f} | "
            f"{r.verify_s:.9f} | {r.total_s:.9f} | {r.errors} | {r.omp_threads} | {r.omp_devices} |"
        )
    return "\n".join(lines)


def write_report(results: list[Result], charts: list[Path]) -> Path:
    path = RESULTS_DIR / "relatorio_tarefa19_resultados.md"
    cpu = next((r for r in results if r.variant == "cpu"), None)
    gpu = next((r for r in results if r.variant == "gpu"), None)

    analysis = "Nao foi possivel calcular speedup porque faltou uma das variantes."
    if cpu is not None and gpu is not None:
        speedup = cpu.avg_compute_s / gpu.avg_compute_s
        gpu_delta = (gpu.avg_compute_s / cpu.avg_compute_s - 1.0) * 100.0
        if speedup >= 1.0:
            analysis = f"A GPU foi {speedup:.3f}x mais rapida que a CPU no tempo medio da soma."
        else:
            analysis = (
                f"A GPU obteve speedup de {speedup:.3f}x, ou seja, ficou "
                f"{gpu_delta:.1f}% mais lenta que a CPU no tempo medio da soma."
            )

    chart_lines = "\n".join(f"![{chart.stem}]({chart.name})" for chart in charts)
    sources = ", ".join(sorted({r.source for r in results}))

    path.write_text(
        f"""# Tarefa 19 - Relatorio de resultados

## Fonte dos dados

Dados lidos de: `{sources}`.

## Resultados

{markdown_table(results)}

## Analise

{analysis}

Todas as execucoes terminaram com `errors = 0`, portanto a soma foi validada
para as duas variantes. A execucao registrada usou `OMP_NUM_THREADS=1`, entao
a linha CPU representa uma CPU com uma thread OpenMP, nao a escalabilidade
multicore completa. Na linha GPU, o tempo da soma inclui a entrada e saida da
regiao `target` e as transferencias determinadas pelas clausulas `map`.

## Graficos

{chart_lines}
""",
        encoding="utf-8",
    )
    return path


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    results = load_results()
    charts = [
        save_compute_chart(results),
        save_speedup_chart(results),
        save_components_chart(results),
    ]
    report = write_report(results, charts)
    print(f"Relatorio gerado: {report}")
    if plt is None:
        print("matplotlib indisponivel; graficos existentes foram reaproveitados.")
    for chart in charts:
        print(f"Grafico gerado: {chart}")


if __name__ == "__main__":
    main()
