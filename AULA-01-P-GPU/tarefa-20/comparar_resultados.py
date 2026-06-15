from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "resultados"


@dataclass(frozen=True)
class Run:
    source: str
    variant: str
    n: int
    nsteps: int
    repeat: int
    error_l2: float
    solve_time_s: float
    total_time_s: float
    omp_threads: str
    omp_devices: str
    offload_policy: str


@dataclass(frozen=True)
class Summary:
    n: int
    nsteps: int
    cpu_repeats: int
    gpu_repeats: int
    cpu_best_solve_s: float
    gpu_best_solve_s: float
    cpu_avg_solve_s: float
    gpu_avg_solve_s: float
    speedup_solve: float
    cpu_avg_total_s: float
    gpu_avg_total_s: float
    speedup_total: float
    cpu_avg_l2: float
    gpu_avg_l2: float
    l2_abs_diff: float


def parse_float(value: str, field: str, source: Path) -> float:
    if value == "":
        raise ValueError(f"Campo vazio {field} em {source}")
    return float(value)


def load_runs(paths: list[Path]) -> tuple[list[Run], list[str]]:
    runs: list[Run] = []
    warnings: list[str] = []

    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):
                if row.get("status") != "0":
                    warnings.append(
                        f"Ignorando {path.name}:{row_number}, status={row.get('status')}"
                    )
                    continue

                try:
                    runs.append(
                        Run(
                            source=path.name,
                            variant=row["variant"],
                            n=int(row["n"]),
                            nsteps=int(row["nsteps"]),
                            repeat=int(row["repeat"]),
                            error_l2=parse_float(row["error_l2"], "error_l2", path),
                            solve_time_s=parse_float(
                                row["solve_time_s"], "solve_time_s", path
                            ),
                            total_time_s=parse_float(
                                row["total_time_s"], "total_time_s", path
                            ),
                            omp_threads=row.get("omp_threads", ""),
                            omp_devices=row.get("omp_devices", ""),
                            offload_policy=row.get("offload_policy", ""),
                        )
                    )
                except (KeyError, ValueError) as exc:
                    warnings.append(f"Ignorando {path.name}:{row_number}: {exc}")

    return runs, warnings


def average(values: list[float]) -> float:
    return statistics.fmean(values)


def summarize(runs: list[Run]) -> list[Summary]:
    cases = sorted({(run.n, run.nsteps) for run in runs})
    summaries: list[Summary] = []

    for n, nsteps in cases:
        cpu = [
            run
            for run in runs
            if run.n == n and run.nsteps == nsteps and run.variant == "cpu"
        ]
        gpu = [
            run
            for run in runs
            if run.n == n and run.nsteps == nsteps and run.variant == "gpu"
        ]
        if not cpu or not gpu:
            continue

        cpu_avg_solve = average([run.solve_time_s for run in cpu])
        gpu_avg_solve = average([run.solve_time_s for run in gpu])
        cpu_avg_total = average([run.total_time_s for run in cpu])
        gpu_avg_total = average([run.total_time_s for run in gpu])
        cpu_avg_l2 = average([run.error_l2 for run in cpu])
        gpu_avg_l2 = average([run.error_l2 for run in gpu])

        summaries.append(
            Summary(
                n=n,
                nsteps=nsteps,
                cpu_repeats=len(cpu),
                gpu_repeats=len(gpu),
                cpu_best_solve_s=min(run.solve_time_s for run in cpu),
                gpu_best_solve_s=min(run.solve_time_s for run in gpu),
                cpu_avg_solve_s=cpu_avg_solve,
                gpu_avg_solve_s=gpu_avg_solve,
                speedup_solve=cpu_avg_solve / gpu_avg_solve,
                cpu_avg_total_s=cpu_avg_total,
                gpu_avg_total_s=gpu_avg_total,
                speedup_total=cpu_avg_total / gpu_avg_total,
                cpu_avg_l2=cpu_avg_l2,
                gpu_avg_l2=gpu_avg_l2,
                l2_abs_diff=abs(cpu_avg_l2 - gpu_avg_l2),
            )
        )

    return summaries


def write_summary_csv(summaries: list[Summary]) -> Path:
    path = RESULTS_DIR / "comparacao_heat_resumo.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "n",
                "nsteps",
                "cpu_repeats",
                "gpu_repeats",
                "cpu_best_solve_s",
                "gpu_best_solve_s",
                "cpu_avg_solve_s",
                "gpu_avg_solve_s",
                "speedup_solve",
                "cpu_avg_total_s",
                "gpu_avg_total_s",
                "speedup_total",
                "cpu_avg_l2",
                "gpu_avg_l2",
                "l2_abs_diff",
            ]
        )
        for item in summaries:
            writer.writerow(
                [
                    item.n,
                    item.nsteps,
                    item.cpu_repeats,
                    item.gpu_repeats,
                    f"{item.cpu_best_solve_s:.9f}",
                    f"{item.gpu_best_solve_s:.9f}",
                    f"{item.cpu_avg_solve_s:.9f}",
                    f"{item.gpu_avg_solve_s:.9f}",
                    f"{item.speedup_solve:.6f}",
                    f"{item.cpu_avg_total_s:.9f}",
                    f"{item.gpu_avg_total_s:.9f}",
                    f"{item.speedup_total:.6f}",
                    f"{item.cpu_avg_l2:.9e}",
                    f"{item.gpu_avg_l2:.9e}",
                    f"{item.l2_abs_diff:.9e}",
                ]
            )
    return path


def markdown_table(summaries: list[Summary]) -> str:
    lines = [
        "| N | Passos | Reps CPU | Reps GPU | CPU solve medio (s) | GPU solve medio (s) | Speedup solve | CPU total medio (s) | GPU total medio (s) | Speedup total | Delta L2 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summaries:
        lines.append(
            f"| {item.n} | {item.nsteps} | {item.cpu_repeats} | {item.gpu_repeats} | "
            f"{item.cpu_avg_solve_s:.9f} | {item.gpu_avg_solve_s:.9f} | "
            f"{item.speedup_solve:.3f}x | {item.cpu_avg_total_s:.9f} | "
            f"{item.gpu_avg_total_s:.9f} | {item.speedup_total:.3f}x | "
            f"{item.l2_abs_diff:.3e} |"
        )
    return "\n".join(lines)


def write_report(
    summaries: list[Summary], sources: list[Path], warnings: list[str], charts: list[Path]
) -> Path:
    path = RESULTS_DIR / "comparacao_heat.md"
    source_names = ", ".join(path.name for path in sources)

    best = max(summaries, key=lambda item: item.speedup_solve)
    worst = min(summaries, key=lambda item: item.speedup_solve)
    chart_lines = "\n".join(f"![{chart.stem}]({chart.name})" for chart in charts)
    warning_lines = "\n".join(f"- {warning}" for warning in warnings)

    path.write_text(
        f"""# Comparacao heat CPU x GPU

## Fonte dos dados

CSVs lidos: `{source_names}`.

## Resumo

{markdown_table(summaries)}

## Leitura dos resultados

O speedup usa `tempo medio CPU / tempo medio GPU`. Valores acima de 1 indicam
vantagem da versao GPU; valores abaixo de 1 indicam que a versao CPU foi mais
rapida nesse caso.

Melhor speedup de solve: `{best.speedup_solve:.3f}x` com `N={best.n}` e
`nsteps={best.nsteps}`.

Menor speedup de solve: `{worst.speedup_solve:.3f}x` com `N={worst.n}` e
`nsteps={worst.nsteps}`.

A diferenca `Delta L2` compara o erro numerico medio das duas versoes. Ela deve
ficar muito pequena, porque o stencil calculado e o mesmo; diferencas pequenas
podem aparecer por ordem de execucao e arredondamento.

## Graficos

{chart_lines if chart_lines else "Graficos nao gerados porque matplotlib nao esta disponivel."}

## Avisos

{warning_lines if warning_lines else "Nenhum aviso."}
""",
        encoding="utf-8",
    )
    return path


def save_charts(summaries: list[Summary]) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    labels = [f"{item.n}x{item.n}\n{item.nsteps} passos" for item in summaries]
    x = list(range(len(summaries)))
    width = 0.36
    charts: list[Path] = []

    path = RESULTS_DIR / "tempo_solve_cpu_gpu.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.6), dpi=140)
    ax.bar(
        [i - width / 2 for i in x],
        [item.cpu_avg_solve_s for item in summaries],
        width,
        label="CPU",
        color="#2563eb",
    )
    ax.bar(
        [i + width / 2 for i in x],
        [item.gpu_avg_solve_s for item in summaries],
        width,
        label="GPU",
        color="#16a34a",
    )
    ax.set_title("Tempo medio do solve")
    ax.set_ylabel("Tempo (s)")
    ax.set_xticks(x, labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    charts.append(path)

    path = RESULTS_DIR / "speedup_solve_cpu_gpu.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.6), dpi=140)
    bars = ax.bar(labels, [item.speedup_solve for item in summaries], color="#f97316")
    ax.axhline(1.0, color="#111827", linewidth=1, linestyle="--")
    ax.set_title("Speedup do solve")
    ax.set_ylabel("CPU / GPU")
    ax.grid(axis="y", alpha=0.25)
    for bar, item in zip(bars, summaries):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            item.speedup_solve,
            f"{item.speedup_solve:.2f}x",
            ha="center",
            va="bottom",
        )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    charts.append(path)

    return charts


def find_csvs(args: argparse.Namespace) -> list[Path]:
    if args.csv:
        return [Path(path) for path in args.csv]
    return sorted(RESULTS_DIR.glob("heat_resultados_*.csv"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara resultados CPU x GPU do heat da tarefa 20."
    )
    parser.add_argument(
        "csv",
        nargs="*",
        help="CSVs especificos para comparar. Se omitido, le resultados/heat_resultados_*.csv.",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    csv_paths = find_csvs(args)
    if not csv_paths:
        raise SystemExit(f"Nenhum CSV encontrado em {RESULTS_DIR}")

    runs, warnings = load_runs(csv_paths)
    summaries = summarize(runs)
    if not summaries:
        raise SystemExit("Nao ha pares CPU/GPU validos para comparar.")

    summary_csv = write_summary_csv(summaries)
    charts = save_charts(summaries)
    report = write_report(summaries, csv_paths, warnings, charts)

    print(f"Resumo CSV: {summary_csv}")
    print(f"Relatorio: {report}")
    for chart in charts:
        print(f"Grafico: {chart}")


if __name__ == "__main__":
    main()
