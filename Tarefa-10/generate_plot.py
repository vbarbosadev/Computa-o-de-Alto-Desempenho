#!/usr/bin/env python3
"""
Gera apenas o grafico da Tarefa 10 a partir do arquivo JSON de resumo.

Uso:
  python3 Tarefa-10/generate_plot.py
  python3 Tarefa-10/generate_plot.py Tarefa-10/dados/tarefa10_summary.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


TASK_DIR = Path(__file__).resolve().parent
DEFAULT_JSON_PATH = TASK_DIR / "dados" / "tarefa10_summary.json"
OUTPUT_DIR = TASK_DIR / "relatorios"
OUTPUT_PATH = OUTPUT_DIR / "tarefa10_resultados.png"

COLORS = {
    "shared_critical": "#C0392B",
    "shared_atomic": "#E67E22",
    "private_critical": "#2980B9",
    "private_vector": "#16A085",
    "reduction": "#2E7D32",
}

MARKERS = {
    "shared_critical": "o",
    "shared_atomic": "s",
    "private_critical": "^",
    "private_vector": "D",
    "reduction": "P",
}


def load_summary(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"JSON nao encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def plot_summary(summary: dict, output_path: Path) -> None:
    programs = {program["id"]: program for program in summary["programs"]}
    threads_tested = summary["config"]["threads_tested"]
    fixed_threads = summary["config"]["fixed_bar_threads"]
    n_value = summary["config"]["n"]

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        f"Tarefa 10 - PI com rand_r() e diferentes formas de sincronizacao (N={n_value:,})",
        fontsize=13,
        fontweight="bold",
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.28)

    ax_time = fig.add_subplot(gs[0, 0])
    ax_speedup = fig.add_subplot(gs[0, 1])
    ax_error = fig.add_subplot(gs[1, 0])
    ax_bar = fig.add_subplot(gs[1, 1])

    for pid, program in programs.items():
        threads = [pt["requested_threads"] for pt in program["per_thread"]]
        times = [pt["avg_elapsed_seconds"] * 1000.0 for pt in program["per_thread"]]
        ax_time.plot(
            threads,
            times,
            marker=MARKERS.get(pid, "o"),
            color=COLORS.get(pid, "#333333"),
            linewidth=2,
            label=program["label"],
        )
    ax_time.set_title("Tempo medio de execucao")
    ax_time.set_xlabel("Threads")
    ax_time.set_ylabel("Tempo (ms)")
    ax_time.grid(True, linestyle="--", alpha=0.4)
    ax_time.legend(fontsize=8)

    for pid, program in programs.items():
        base = next(
            (pt["avg_elapsed_seconds"] for pt in program["per_thread"] if pt["requested_threads"] == 1),
            None,
        )
        if base and base > 0.0:
            threads = [pt["requested_threads"] for pt in program["per_thread"]]
            speedups = [
                base / pt["avg_elapsed_seconds"] if pt["avg_elapsed_seconds"] > 0.0 else 0.0
                for pt in program["per_thread"]
            ]
            ax_speedup.plot(
                threads,
                speedups,
                marker=MARKERS.get(pid, "o"),
                color=COLORS.get(pid, "#333333"),
                linewidth=2,
                label=program["label"],
            )
    max_threads = max(threads_tested)
    ax_speedup.plot([1, max_threads], [1, max_threads], "k--", linewidth=1, label="Ideal")
    ax_speedup.set_title("Speedup relativo a 1 thread")
    ax_speedup.set_xlabel("Threads")
    ax_speedup.set_ylabel("Speedup")
    ax_speedup.grid(True, linestyle="--", alpha=0.4)
    ax_speedup.legend(fontsize=8)

    for pid, program in programs.items():
        threads = [pt["requested_threads"] for pt in program["per_thread"]]
        errors = [pt["avg_error"] for pt in program["per_thread"]]
        ax_error.plot(
            threads,
            errors,
            marker=MARKERS.get(pid, "o"),
            color=COLORS.get(pid, "#333333"),
            linewidth=2,
            label=program["label"],
        )
    ax_error.set_title("Erro medio da estimativa")
    ax_error.set_xlabel("Threads")
    ax_error.set_ylabel("|pi_estimado - pi_real|")
    ax_error.grid(True, linestyle="--", alpha=0.4)
    ax_error.legend(fontsize=8)

    labels = []
    values = []
    colors = []
    for program in summary["programs"]:
        point = next(
            (pt for pt in program["per_thread"] if pt["requested_threads"] == fixed_threads),
            None,
        )
        if point:
            labels.append(program["label"])
            values.append(point["avg_elapsed_seconds"] * 1000.0)
            colors.append(COLORS.get(program["id"], "#333333"))
    ax_bar.bar(range(len(labels)), values, color=colors, edgecolor="black", linewidth=0.8)
    ax_bar.set_xticks(range(len(labels)))
    ax_bar.set_xticklabels(labels, rotation=18, ha="right", fontsize=8)
    ax_bar.set_title(f"Comparacao direta com {fixed_threads} threads")
    ax_bar.set_ylabel("Tempo (ms)")
    ax_bar.grid(True, axis="y", linestyle="--", alpha=0.4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON_PATH
    summary = load_summary(json_path)
    plot_summary(summary, OUTPUT_PATH)
    print(f"Grafico gerado com sucesso: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
