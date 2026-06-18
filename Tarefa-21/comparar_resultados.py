from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "resultados"
VARIANT_ORDER = ["cpu", "gpu_baseline", "gpu_resident"]


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


@dataclass(frozen=True)
class VariantSummary:
    n: int
    nsteps: int
    variant: str
    repeats: int
    best_solve_s: float
    avg_solve_s: float
    avg_total_s: float
    avg_l2: float


def parse_float(value: str, field: str, source: Path) -> float:
    if value == "":
        raise ValueError(f"campo vazio {field} em {source}")
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
                        )
                    )
                except (KeyError, ValueError) as exc:
                    warnings.append(f"Ignorando {path.name}:{row_number}: {exc}")

    return runs, warnings


def variant_sort_key(variant: str) -> tuple[int, str]:
    try:
        return (VARIANT_ORDER.index(variant), variant)
    except ValueError:
        return (len(VARIANT_ORDER), variant)


def summarize(runs: list[Run]) -> list[VariantSummary]:
    grouped: dict[tuple[int, int, str], list[Run]] = defaultdict(list)
    for run in runs:
        grouped[(run.n, run.nsteps, run.variant)].append(run)

    summaries: list[VariantSummary] = []
    for (n, nsteps, variant), items in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], variant_sort_key(item[0][2]))
    ):
        summaries.append(
            VariantSummary(
                n=n,
                nsteps=nsteps,
                variant=variant,
                repeats=len(items),
                best_solve_s=min(run.solve_time_s for run in items),
                avg_solve_s=statistics.fmean(run.solve_time_s for run in items),
                avg_total_s=statistics.fmean(run.total_time_s for run in items),
                avg_l2=statistics.fmean(run.error_l2 for run in items),
            )
        )

    return summaries


def write_summary_csv(summaries: list[VariantSummary]) -> Path:
    path = RESULTS_DIR / "comparacao_heat_resumo.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "n",
                "nsteps",
                "variant",
                "repeats",
                "best_solve_s",
                "avg_solve_s",
                "avg_total_s",
                "avg_l2",
            ]
        )
        for item in summaries:
            writer.writerow(
                [
                    item.n,
                    item.nsteps,
                    item.variant,
                    item.repeats,
                    f"{item.best_solve_s:.9f}",
                    f"{item.avg_solve_s:.9f}",
                    f"{item.avg_total_s:.9f}",
                    f"{item.avg_l2:.9e}",
                ]
            )
    return path


def summaries_by_case(
    summaries: list[VariantSummary],
) -> dict[tuple[int, int], dict[str, VariantSummary]]:
    cases: dict[tuple[int, int], dict[str, VariantSummary]] = defaultdict(dict)
    for item in summaries:
        cases[(item.n, item.nsteps)][item.variant] = item
    return dict(cases)


def fmt_speedup(num: float | None, den: float | None) -> str:
    if num is None or den is None or den == 0.0:
        return "-"
    return f"{num / den:.3f}x"


def markdown_table(summaries: list[VariantSummary]) -> str:
    lines = [
        "| N | Passos | Variante | Reps | Solve medio (s) | Melhor solve (s) | Total medio (s) | L2 medio |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summaries:
        lines.append(
            f"| {item.n} | {item.nsteps} | `{item.variant}` | {item.repeats} | "
            f"{item.avg_solve_s:.9f} | {item.best_solve_s:.9f} | "
            f"{item.avg_total_s:.9f} | {item.avg_l2:.9e} |"
        )
    return "\n".join(lines)


def speedup_table(summaries: list[VariantSummary]) -> str:
    lines = [
        "| N | Passos | CPU/resident | CPU/baseline | Baseline/resident | Delta L2 baseline-resident |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (n, nsteps), variants in sorted(summaries_by_case(summaries).items()):
        cpu = variants.get("cpu")
        baseline = variants.get("gpu_baseline")
        resident = variants.get("gpu_resident")
        l2_delta = "-"
        if baseline and resident:
            l2_delta = f"{abs(baseline.avg_l2 - resident.avg_l2):.3e}"
        lines.append(
            f"| {n} | {nsteps} | "
            f"{fmt_speedup(cpu.avg_solve_s if cpu else None, resident.avg_solve_s if resident else None)} | "
            f"{fmt_speedup(cpu.avg_solve_s if cpu else None, baseline.avg_solve_s if baseline else None)} | "
            f"{fmt_speedup(baseline.avg_solve_s if baseline else None, resident.avg_solve_s if resident else None)} | "
            f"{l2_delta} |"
        )
    return "\n".join(lines)


def write_report(
    summaries: list[VariantSummary], sources: list[Path], warnings: list[str]
) -> Path:
    path = RESULTS_DIR / "comparacao_heat.md"
    source_names = ", ".join(path.name for path in sources)
    warning_lines = "\n".join(f"- {warning}" for warning in warnings)

    path.write_text(
        f"""# Comparacao heat - Tarefa 21

## Fonte dos dados

CSVs lidos: `{source_names}`.

## Tempos por variante

{markdown_table(summaries)}

## Speedups do solve

{speedup_table(summaries)}

## Leitura esperada

`gpu_baseline` usa `map(tofrom: ...)` dentro do kernel chamado a cada passo de
tempo. `gpu_resident` usa `target enter data` antes do laco temporal e
`target exit data` depois, evitando a copia CPU-GPU-CPU repetida em cada passo.

O speedup usa tempo medio de `solve` no numerador dividido pelo tempo medio de
`solve` no denominador. Portanto, `Baseline/resident` acima de 1 indica ganho da
versao com dados residentes.

## Avisos

{warning_lines if warning_lines else "Nenhum aviso."}
""",
        encoding="utf-8",
    )
    return path


def find_csvs(args: argparse.Namespace) -> list[Path]:
    if args.csv:
        return [Path(path) for path in args.csv]
    return sorted(RESULTS_DIR.glob("heat_resultados_*.csv"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera resumo Markdown/CSV para os resultados da Tarefa 21."
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
        raise SystemExit("Nao ha execucoes validas para comparar.")

    summary_csv = write_summary_csv(summaries)
    report = write_report(summaries, csv_paths, warnings)

    print(f"Resumo CSV: {summary_csv}")
    print(f"Relatorio: {report}")


if __name__ == "__main__":
    main()
