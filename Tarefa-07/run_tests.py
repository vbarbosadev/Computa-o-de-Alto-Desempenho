#!/usr/bin/env python3
"""
Compara duas versoes da Tarefa 7:

- tasks.c        -> versao correta, com single
- tasks_error.c  -> versao incorreta, sem single

O objetivo principal nao e medir desempenho absoluto, e sim validar corretude:
1. Cada no foi processado?
2. Algum no foi duplicado ou ignorado?
3. O comportamento muda entre execucoes?
4. O que muda quando removemos o single?
"""

from __future__ import annotations

import csv
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


ROOT_DIR = Path(__file__).resolve().parent.parent
TASK_DIR = Path(__file__).resolve().parent
BUILD_DIR = TASK_DIR / "build"
DATA_DIR = ROOT_DIR / "dados"
REPORT_DIR = ROOT_DIR / "relatorios"

CSV_PATH = DATA_DIR / "tarefa7_runs.csv"
JSON_PATH = DATA_DIR / "tarefa7_summary.json"
PLOT_PATH = REPORT_DIR / "tarefa7_testes.png"
REPORT_PATH = REPORT_DIR / "relatorio_tarefa07.md"

DEFAULT_NODES = 64
DEFAULT_RUNS = 20

PTHREAD_DLL = Path(r"C:\MinGW\bin\pthreadGC-3.dll")
PTHREAD_DEF = BUILD_DIR / "pthreadGC-3.def"
PTHREAD_IMPORT_LIB = BUILD_DIR / "libpthread.dll.a"

PROCESS_RE = re.compile(r"^PROCESS node=(\d+) file=(\S+) thread=(\d+)$")
CONFIG_RE = re.compile(r"^CONFIG total_nodes=(\d+) requested_threads=(\d+)$")
SUMMARY_RE = re.compile(r"^SUMMARY total_nodes=(\d+) elapsed_seconds=([0-9.]+)$")

PTHREAD_EXPORTS = [
    "pthread_attr_destroy",
    "pthread_attr_getstacksize",
    "pthread_attr_init",
    "pthread_attr_setdetachstate",
    "pthread_attr_setstacksize",
    "pthread_create",
    "pthread_exit",
    "pthread_key_create",
    "pthread_key_delete",
    "pthread_mutex_destroy",
    "pthread_mutex_init",
    "pthread_mutex_lock",
    "pthread_mutex_unlock",
    "pthread_once",
    "pthread_setspecific",
    "sem_destroy",
    "sem_init",
    "sem_post",
    "sem_trywait",
    "sem_wait",
]

PROGRAMS = [
    {
        "id": "correct",
        "label": "Correto (com single)",
        "source": TASK_DIR / "tasks.c",
        "binary": BUILD_DIR / "tasks_correct",
        "notes": "Uma unica thread percorre a lista e cria exatamente uma task por no.",
    },
    {
        "id": "error",
        "label": "Incorreto (sem single)",
        "source": TASK_DIR / "tasks_error.c",
        "binary": BUILD_DIR / "tasks_error",
        "notes": "Todas as threads percorrem a lista e criam tasks duplicadas para os mesmos nos.",
    },
]


def detect_thread_counts() -> list[int]:
    max_threads = max(1, os.cpu_count() or 1)
    counts = [1]
    for candidate in (2, 4, 8):
        if candidate <= max_threads:
            counts.append(candidate)
    if max_threads not in counts:
        counts.append(max_threads)
    return counts


THREAD_COUNTS = detect_thread_counts()


def ensure_dirs() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def write_pthread_def() -> None:
    lines = ["LIBRARY pthreadGC-3.dll", "EXPORTS"]
    lines.extend(PTHREAD_EXPORTS)
    PTHREAD_DEF.write_text("\n".join(lines) + "\n", encoding="ascii")


def ensure_windows_openmp_support() -> Path | None:
    if os.name != "nt":
        return None

    if PTHREAD_IMPORT_LIB.exists():
        return BUILD_DIR

    if not PTHREAD_DLL.exists():
        raise RuntimeError(
            "Nao foi possivel localizar pthreadGC-3.dll em C:\\MinGW\\bin."
        )

    dlltool = shutil.which("dlltool")
    if not dlltool:
        raise RuntimeError("dlltool nao esta disponivel no PATH.")

    write_pthread_def()
    command = [
        dlltool,
        "-d",
        str(PTHREAD_DEF),
        "-D",
        "pthreadGC-3.dll",
        "-l",
        str(PTHREAD_IMPORT_LIB),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Falha ao gerar a import library para pthreadGC-3.dll:\n"
            f"{result.stderr.strip()}"
        )

    return BUILD_DIR


def compile_program(program: dict[str, object]) -> None:
    gcc = shutil.which("gcc")
    if not gcc:
        raise RuntimeError("gcc nao encontrado no PATH.")

    command = [
        gcc,
        "-O2",
        "-fopenmp",
        str(program["source"]),
        "-o",
        str(program["binary"]),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return

    needs_pthread_workaround = os.name == "nt" and "cannot find -lpthread" in result.stderr
    if not needs_pthread_workaround:
        raise RuntimeError(
            f"Falha ao compilar {program['source']}:\n{result.stderr.strip()}"
        )

    lib_dir = ensure_windows_openmp_support()
    command.extend(["-L", str(lib_dir)])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha ao compilar {program['source']} mesmo apos preparar libpthread:\n"
            f"{result.stderr.strip()}"
        )


def compile_programs() -> None:
    ensure_dirs()
    for program in PROGRAMS:
        compile_program(program)


def build_env(threads: int) -> dict[str, str]:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"] = "FALSE"
    return env


def parse_run(output: str, expected_nodes: int) -> dict[str, object]:
    config = None
    summary = None
    process_events: list[dict[str, int | str]] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        config_match = CONFIG_RE.match(line)
        if config_match:
            config = {
                "total_nodes": int(config_match.group(1)),
                "requested_threads": int(config_match.group(2)),
            }
            continue

        process_match = PROCESS_RE.match(line)
        if process_match:
            process_events.append(
                {
                    "node": int(process_match.group(1)),
                    "file": process_match.group(2),
                    "thread": int(process_match.group(3)),
                }
            )
            continue

        summary_match = SUMMARY_RE.match(line)
        if summary_match:
            summary = {
                "total_nodes": int(summary_match.group(1)),
                "elapsed_seconds": float(summary_match.group(2)),
            }

    if config is None or summary is None:
        raise RuntimeError(f"Saida invalida do programa:\n{output}")

    node_counts = Counter(event["node"] for event in process_events)
    expected_node_ids = set(range(expected_nodes))
    seen_node_ids = set(node_counts.keys())

    missing_nodes = sorted(expected_node_ids - seen_node_ids)
    duplicate_nodes = sorted(node for node, count in node_counts.items() if count > 1)
    duplicate_events_total = sum(
        count - 1 for count in node_counts.values() if count > 1
    )
    invalid_files = sorted(
        event["node"]
        for event in process_events
        if event["file"] != f"file{event['node']}.txt"
    )
    assignment_by_node = {
        event["node"]: int(event["thread"])
        for event in process_events
        if node_counts[event["node"]] == 1
    }
    assignment_signature = tuple(
        assignment_by_node.get(node, -1) for node in range(expected_nodes)
    )
    order_signature = tuple(int(event["node"]) for event in process_events)
    threads_used = sorted({int(event["thread"]) for event in process_events})

    return {
        "config": config,
        "summary": summary,
        "process_count": len(process_events),
        "missing_nodes": missing_nodes,
        "duplicate_nodes": duplicate_nodes,
        "duplicate_events_total": duplicate_events_total,
        "invalid_files": invalid_files,
        "threads_used": threads_used,
        "thread_count_used": len(threads_used),
        "assignment_signature": assignment_signature,
        "order_signature": order_signature,
        "is_valid": (
            config["total_nodes"] == expected_nodes
            and summary["total_nodes"] == expected_nodes
            and len(process_events) == expected_nodes
            and not missing_nodes
            and not duplicate_nodes
            and not invalid_files
        ),
    }


def run_once(program: dict[str, object], threads: int, total_nodes: int) -> dict[str, object]:
    result = subprocess.run(
        [str(program["binary"]), str(total_nodes)],
        capture_output=True,
        text=True,
        env=build_env(threads),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha na execucao de {program['source']} com {threads} thread(s):\n"
            f"{result.stderr.strip()}"
        )

    parsed = parse_run(result.stdout, total_nodes)
    parsed["stdout"] = result.stdout
    return parsed


def collect_runs(total_nodes: int, runs_per_thread: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for program in PROGRAMS:
        for threads in THREAD_COUNTS:
            for run_id in range(1, runs_per_thread + 1):
                parsed = run_once(program, threads, total_nodes)
                summary = parsed["summary"]
                rows.append(
                    {
                        "program_id": str(program["id"]),
                        "program_label": str(program["label"]),
                        "source_file": Path(str(program["source"])).name,
                        "requested_threads": threads,
                        "run_id": run_id,
                        "total_nodes": total_nodes,
                        "processed_events": parsed["process_count"],
                        "extra_events": parsed["process_count"] - total_nodes,
                        "missing_count": len(parsed["missing_nodes"]),
                        "duplicate_node_count": len(parsed["duplicate_nodes"]),
                        "duplicate_events_total": parsed["duplicate_events_total"],
                        "invalid_file_count": len(parsed["invalid_files"]),
                        "threads_used": parsed["thread_count_used"],
                        "thread_ids": ";".join(map(str, parsed["threads_used"])),
                        "elapsed_seconds": f"{summary['elapsed_seconds']:.6f}",
                        "order_signature": ",".join(map(str, parsed["order_signature"])),
                        "assignment_signature": ",".join(
                            map(str, parsed["assignment_signature"])
                        ),
                        "is_valid": int(bool(parsed["is_valid"])),
                    }
                )

    return rows


def save_csv(rows: list[dict[str, object]]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with CSV_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarise_program(
    program: dict[str, object], rows: list[dict[str, object]], total_nodes: int
) -> dict[str, object]:
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["requested_threads"])].append(row)

    per_thread = []
    for threads in THREAD_COUNTS:
        group = grouped.get(threads, [])
        elapsed_values = [float(row["elapsed_seconds"]) for row in group]
        valid_runs = sum(int(row["is_valid"]) for row in group)
        order_signatures = {row["order_signature"] for row in group}
        assignment_signatures = {row["assignment_signature"] for row in group}

        per_thread.append(
            {
                "requested_threads": threads,
                "runs": len(group),
                "valid_runs": valid_runs,
                "invalid_runs": len(group) - valid_runs,
                "all_valid": valid_runs == len(group),
                "avg_processed_events": round(
                    statistics.mean(int(row["processed_events"]) for row in group), 2
                )
                if group
                else 0.0,
                "avg_extra_events": round(
                    statistics.mean(int(row["extra_events"]) for row in group), 2
                )
                if group
                else 0.0,
                "avg_duplicate_node_count": round(
                    statistics.mean(int(row["duplicate_node_count"]) for row in group), 2
                )
                if group
                else 0.0,
                "avg_duplicate_events_total": round(
                    statistics.mean(int(row["duplicate_events_total"]) for row in group), 2
                )
                if group
                else 0.0,
                "avg_missing_count": round(
                    statistics.mean(int(row["missing_count"]) for row in group), 2
                )
                if group
                else 0.0,
                "avg_threads_used": round(
                    statistics.mean(int(row["threads_used"]) for row in group), 2
                )
                if group
                else 0.0,
                "unique_order_signatures": len(order_signatures),
                "unique_assignment_signatures": len(assignment_signatures),
                "avg_elapsed_seconds": round(statistics.mean(elapsed_values), 6)
                if elapsed_values
                else 0.0,
                "median_elapsed_seconds": round(statistics.median(elapsed_values), 6)
                if elapsed_values
                else 0.0,
                "min_elapsed_seconds": round(min(elapsed_values), 6)
                if elapsed_values
                else 0.0,
                "max_elapsed_seconds": round(max(elapsed_values), 6)
                if elapsed_values
                else 0.0,
            }
        )

    all_runs_valid = all(item["all_valid"] for item in per_thread)
    behavior_changes = any(
        item["unique_order_signatures"] > 1 or item["unique_assignment_signatures"] > 1
        for item in per_thread
        if item["requested_threads"] > 1
    )
    only_single_thread_valid = all(
        (item["all_valid"] if item["requested_threads"] == 1 else not item["all_valid"])
        for item in per_thread
    )

    return {
        "id": str(program["id"]),
        "label": str(program["label"]),
        "source": Path(str(program["source"])).name,
        "notes": str(program["notes"]),
        "expected_nodes": total_nodes,
        "all_runs_valid": all_runs_valid,
        "behavior_changes_between_runs": behavior_changes,
        "only_single_thread_valid": only_single_thread_valid,
        "per_thread": per_thread,
    }


def summarise_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    total_nodes = int(rows[0]["total_nodes"]) if rows else 0
    program_summaries = []

    for program in PROGRAMS:
        program_rows = [row for row in rows if row["program_id"] == program["id"]]
        program_summaries.append(summarise_program(program, program_rows, total_nodes))

    program_map = {item["id"]: item for item in program_summaries}
    correct = program_map["correct"]
    error = program_map["error"]

    error_multi_thread_all_invalid = all(
        (item["invalid_runs"] == 0 if item["requested_threads"] == 1 else item["valid_runs"] == 0)
        for item in error["per_thread"]
    )
    expected_pattern_observed = bool(correct["all_runs_valid"] and error_multi_thread_all_invalid)

    return {
        "task": "Tarefa 7",
        "platform": {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "python": sys.version.split()[0],
        },
        "config": {
            "threads_tested": THREAD_COUNTS,
            "total_nodes": total_nodes,
            "runs_per_thread": max(int(row["run_id"]) for row in rows) if rows else 0,
        },
        "expected_pattern_observed": expected_pattern_observed,
        "programs": program_summaries,
        "comparison": {
            "correct_all_runs_valid": bool(correct["all_runs_valid"]),
            "error_only_single_thread_valid": bool(error["only_single_thread_valid"]),
            "error_multi_thread_all_invalid": error_multi_thread_all_invalid,
            "correct_behavior_changes_between_runs": bool(
                correct["behavior_changes_between_runs"]
            ),
            "error_behavior_changes_between_runs": bool(
                error["behavior_changes_between_runs"]
            ),
        },
    }


def save_json(summary: dict[str, object]) -> None:
    JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def get_program_summary(summary: dict[str, object], program_id: str) -> dict[str, object]:
    for program in summary["programs"]:
        if program["id"] == program_id:
            return program
    raise KeyError(program_id)


def plot_summary(summary: dict[str, object]) -> None:
    if not HAS_MATPLOTLIB:
        return

    correct = get_program_summary(summary, "correct")
    error = get_program_summary(summary, "error")
    programs = [correct, error]
    styles = {
        "correct": {"color": "#2E86DE", "marker": "o"},
        "error": {"color": "#E74C3C", "marker": "s"},
    }

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Tarefa 7 - Comparacao entre tasks.c (com single) e tasks_error.c (sem single)",
        fontsize=13,
        fontweight="bold",
    )

    for program in programs:
        style = styles[program["id"]]
        threads = [item["requested_threads"] for item in program["per_thread"]]
        valid_pct = [
            (item["valid_runs"] / item["runs"]) * 100.0 if item["runs"] else 0.0
            for item in program["per_thread"]
        ]
        avg_processed = [item["avg_processed_events"] for item in program["per_thread"]]
        avg_duplicates = [item["avg_duplicate_events_total"] for item in program["per_thread"]]
        avg_ms = [item["avg_elapsed_seconds"] * 1000.0 for item in program["per_thread"]]

        axes[0, 0].plot(
            threads,
            valid_pct,
            marker=style["marker"],
            color=style["color"],
            linewidth=2,
            label=program["label"],
        )
        axes[0, 1].plot(
            threads,
            avg_processed,
            marker=style["marker"],
            color=style["color"],
            linewidth=2,
            label=program["label"],
        )
        axes[1, 0].plot(
            threads,
            avg_duplicates,
            marker=style["marker"],
            color=style["color"],
            linewidth=2,
            label=program["label"],
        )
        axes[1, 1].plot(
            threads,
            avg_ms,
            marker=style["marker"],
            color=style["color"],
            linewidth=2,
            label=program["label"],
        )

    axes[0, 0].set_title("Taxa de corretude")
    axes[0, 0].set_xlabel("Threads solicitadas")
    axes[0, 0].set_ylabel("Rodadas validas (%)")
    axes[0, 0].set_ylim(-5, 105)
    axes[0, 0].grid(True, linestyle="--", alpha=0.4)
    axes[0, 0].legend()

    axes[0, 1].axhline(
        y=summary["config"]["total_nodes"],
        color="gray",
        linestyle="--",
        linewidth=1.5,
        label="Total esperado de nos",
    )
    axes[0, 1].set_title("Eventos PROCESS por rodada")
    axes[0, 1].set_xlabel("Threads solicitadas")
    axes[0, 1].set_ylabel("Eventos medios")
    axes[0, 1].grid(True, linestyle="--", alpha=0.4)
    axes[0, 1].legend()

    axes[1, 0].set_title("Eventos duplicados por rodada")
    axes[1, 0].set_xlabel("Threads solicitadas")
    axes[1, 0].set_ylabel("Duplicacoes medias")
    axes[1, 0].grid(True, linestyle="--", alpha=0.4)

    axes[1, 1].set_title("Tempo medio")
    axes[1, 1].set_xlabel("Threads solicitadas")
    axes[1, 1].set_ylabel("Tempo medio (ms)")
    axes[1, 1].grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


def format_program_table(program: dict[str, object]) -> str:
    headers = [
        "Threads",
        "Rodadas",
        "Validas",
        "Eventos medios",
        "Duplicacoes medias",
        "Ordens distintas",
        "Tempo medio (ms)",
    ]
    separator = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = [
        "|" + "|".join(headers) + "|",
        separator,
    ]

    for item in program["per_thread"]:
        lines.append(
            "|"
            + "|".join(
                [
                    str(item["requested_threads"]),
                    str(item["runs"]),
                    str(item["valid_runs"]),
                    f"{item['avg_processed_events']:.2f}",
                    f"{item['avg_duplicate_events_total']:.2f}",
                    str(item["unique_order_signatures"]),
                    f"{item['avg_elapsed_seconds'] * 1000.0:.3f}",
                ]
            )
            + "|"
        )

    return "\n".join(lines)


def build_report(summary: dict[str, object]) -> str:
    correct = get_program_summary(summary, "correct")
    error = get_program_summary(summary, "error")
    total_nodes = summary["config"]["total_nodes"]
    runs_per_thread = summary["config"]["runs_per_thread"]
    threads_text = ", ".join(map(str, summary["config"]["threads_tested"]))

    image_block = f"![Teste Tarefa 7](tarefa7_testes.png)" if PLOT_PATH.exists() else ""
    artifact_lines = [
        "- CSV bruto: `dados/tarefa7_runs.csv`",
        "- Resumo estruturado: `dados/tarefa7_summary.json`",
    ]
    if PLOT_PATH.exists():
        artifact_lines.append("- Grafico: `relatorios/tarefa7_testes.png`")
    artifact_lines.append("- Relatorio: `relatorios/relatorio_tarefa07.md`")

    ubuntu_run = """```bash
sudo apt update
sudo apt install -y build-essential python3 python3-pip
python3 -m pip install --user matplotlib

cd atividades-aula
python3 Tarefa-07/run_tests.py
```"""

    ubuntu_report_only = """```bash
python3 Tarefa-07/run_tests.py --report-only
```"""

    return f"""# Tarefa 7 - Comparacao entre `tasks.c` e `tasks_error.c`

## Objetivo

Comparar a versao correta [tasks.c](../Tarefa-07/tasks.c), que usa `single` para criar uma unica task por no, com a versao [tasks_error.c](../Tarefa-07/tasks_error.c), que remove o `single` e deixa todas as threads percorrerem a lista.

## Como rodar no Ubuntu

Para rodar a coleta completa no Ubuntu:

{ubuntu_run}

Para apenas regenerar o grafico e o relatorio a partir do JSON ja salvo:

{ubuntu_report_only}

Argumentos opcionais:

- `python3 Tarefa-07/run_tests.py 64 20`
- o primeiro argumento e o numero de nos
- o segundo argumento e o numero de rodadas por configuracao de threads

## O que foi testado

- Compilacao com `gcc -O2 -fopenmp`
- {runs_per_thread} rodadas por programa
- configuracoes de threads: {threads_text}
- lista com {total_nodes} nos por rodada
- validacao de corretude:
  - cada no esperado apareceu exatamente uma vez
  - nenhum no foi ignorado
  - nenhum no foi processado mais de uma vez
  - a saida final `SUMMARY` bate com o total esperado

## Programas comparados

- `tasks.c`: {correct["notes"]}
- `tasks_error.c`: {error["notes"]}

## Resultados - Versao correta

{format_program_table(correct)}

## Resultados - Versao sem `single`

{format_program_table(error)}

{image_block}

## Comparacao

- `tasks.c` ficou valido em todas as rodadas: {"sim" if correct["all_runs_valid"] else "nao"}.
- `tasks.c` mudou ordem/thread entre execucoes com mais de uma thread: {"sim" if correct["behavior_changes_between_runs"] else "nao"}.
- `tasks_error.c` ficou valido apenas com 1 thread: {"sim" if summary["comparison"]["error_only_single_thread_valid"] else "nao"}.
- `tasks_error.c` falhou em todas as rodadas com mais de 1 thread: {"sim" if summary["comparison"]["error_multi_thread_all_invalid"] else "nao"}.
- Padrao esperado da comparacao foi observado: {"sim" if summary["expected_pattern_observed"] else "nao"}.

## Interpretacao

O `single` e a diretiva que realmente impede a duplicacao do trabalho nesta tarefa. Com `single`, apenas uma thread percorre a lista encadeada e cria uma task para cada no. Sem `single`, todas as threads entram no mesmo trecho, percorrem a lista inteira e criam tasks para os mesmos nos. O efeito nao e um problema de impressao: e um problema de criacao duplicada de tarefas.

Isso tambem mostra por que `critical(output)` nao resolve o erro de `tasks_error.c`. O `critical` apenas serializa o `printf`, evitando linhas embaralhadas no terminal. Ele nao impede que varias threads criem tarefas repetidas para o mesmo no.

Em resumo:

- `tasks.c` demonstra o comportamento correto: 1 task por no, sem perdas e sem duplicacoes.
- `tasks_error.c` demonstra o erro estrutural: para `N` threads, a tendencia e criar aproximadamente `N` vezes mais eventos `PROCESS` do que o total de nos.
- a variacao entre execucoes continua existindo nas duas versoes, mas so a versao com `single` preserva a corretude.

## Artefatos gerados

{"\n".join(artifact_lines)}
"""


def save_report(summary: dict[str, object]) -> None:
    REPORT_PATH.write_text(build_report(summary), encoding="utf-8", newline="\n")


def report_only() -> int:
    if not JSON_PATH.exists():
        raise RuntimeError(
            f"Resumo nao encontrado em {JSON_PATH}. Execute a coleta antes do modo --report-only."
        )

    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    plot_summary(summary)
    save_report(summary)

    print("Relatorio/regeneracao concluido(a) com sucesso.")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico: {PLOT_PATH}")
    print(f"  Relatorio: {REPORT_PATH}")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--report-only":
        return report_only()

    total_nodes = DEFAULT_NODES
    runs_per_thread = DEFAULT_RUNS

    if len(sys.argv) > 1:
        total_nodes = int(sys.argv[1])
    if len(sys.argv) > 2:
        runs_per_thread = int(sys.argv[2])

    compile_programs()
    rows = collect_runs(total_nodes, runs_per_thread)
    save_csv(rows)
    summary = summarise_rows(rows)
    save_json(summary)
    plot_summary(summary)
    save_report(summary)

    print("Comparacao da Tarefa 7 gerada com sucesso.")
    print(f"  CSV:      {CSV_PATH}")
    print(f"  JSON:     {JSON_PATH}")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico:  {PLOT_PATH}")
    elif not HAS_MATPLOTLIB:
        print("  Grafico:  nao gerado (matplotlib indisponivel neste Python).")
    print(f"  Relatorio: {REPORT_PATH}")

    return 0 if summary["expected_pattern_observed"] else 1


if __name__ == "__main__":
    sys.exit(main())
