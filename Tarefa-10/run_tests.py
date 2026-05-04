#!/usr/bin/env python3
"""
Tarefa 10 - Comparacao entre critical, atomic, contadores privados e reduction

Compara cinco versoes da estimativa estocastica de PI, todas usando rand_r():

  1. shared_critical   - contador compartilhado com #pragma omp critical
  2. shared_atomic     - contador compartilhado com #pragma omp atomic
  3. private_critical  - contador privado por thread + critical final
  4. private_vector    - hits[tid] em vetor compartilhado (false sharing)
  5. reduction         - reduction(+:count)
"""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


TASK_DIR = Path(__file__).resolve().parent
BUILD_DIR = TASK_DIR / "build"
DATA_DIR = TASK_DIR / "dados"
REPORT_DIR = TASK_DIR / "relatorios"

CSV_PATH = DATA_DIR / "tarefa10_runs.csv"
JSON_PATH = DATA_DIR / "tarefa10_summary.json"
PLOT_PATH = REPORT_DIR / "tarefa10_resultados.png"
REPORT_PATH = REPORT_DIR / "relatorio_tarefa10.md"

DEFAULT_N = 10_000_000
DEFAULT_RUNS = 10

PTHREAD_DLL = Path(r"C:\MinGW\bin\pthreadGC-3.dll")
PTHREAD_DEF = BUILD_DIR / "pthreadGC-3.def"
PTHREAD_IMPORT_LIB = BUILD_DIR / "libpthread.dll.a"

CONFIG_RE = re.compile(r"^CONFIG program=(\S+) n=(\d+) threads=(\d+)$")
RESULT_RE = re.compile(
    r"^RESULT pi=([0-9.]+) count=(\d+) total=(\d+) error=([0-9.]+) elapsed=([0-9.]+)$"
)

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
        "id": "shared_critical",
        "label": "shared + critical",
        "source": TASK_DIR / "pi_randr_shared_critical.c",
        "binary": BUILD_DIR / "pi_randr_shared_critical",
        "notes": "Cada acerto entra em critical; maior serializacao do contador global.",
    },
    {
        "id": "shared_atomic",
        "label": "shared + atomic",
        "source": TASK_DIR / "pi_randr_shared_atomic.c",
        "binary": BUILD_DIR / "pi_randr_shared_atomic",
        "notes": "Cada acerto atualiza o contador global com atomic; menor overhead que critical para incrementos simples.",
    },
    {
        "id": "private_critical",
        "label": "private + critical final",
        "source": TASK_DIR / "pi_randr_private_critical.c",
        "binary": BUILD_DIR / "pi_randr_private_critical",
        "notes": "Cada thread soma localmente e entra em critical apenas uma vez no final.",
    },
    {
        "id": "private_vector",
        "label": "private vetor hits[tid]",
        "source": TASK_DIR / "pi_randr_private_vector.c",
        "binary": BUILD_DIR / "pi_randr_private_vector",
        "notes": "Acumula em hits[tid] contiguos; pode sofrer false sharing entre threads vizinhas.",
    },
    {
        "id": "reduction",
        "label": "reduction(+:count)",
        "source": TASK_DIR / "pi_randr_reduction.c",
        "binary": BUILD_DIR / "pi_randr_reduction",
        "notes": "OpenMP cria acumuladores privados e combina automaticamente ao final do loop.",
    },
]

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

COMPARISON_GROUPS = [
    ("shared_critical", "shared_atomic"),
    ("shared_atomic", "private_critical"),
    ("shared_critical", "private_critical"),
    ("private_critical", "private_vector"),
    ("private_critical", "reduction"),
    ("private_vector", "reduction"),
    ("shared_atomic", "reduction"),
    ("shared_critical", "reduction"),
]


def detect_thread_counts() -> list[int]:
    max_t = max(1, os.cpu_count() or 1)
    counts = [1]
    for c in (2, 4, 8, 12):
        if c <= max_t:
            counts.append(c)
    if max_t not in counts:
        counts.append(max_t)
    return counts


THREAD_COUNTS = detect_thread_counts()


def ensure_dirs() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def write_pthread_def() -> None:
    lines = ["LIBRARY pthreadGC-3.dll", "EXPORTS"] + PTHREAD_EXPORTS
    PTHREAD_DEF.write_text("\n".join(lines) + "\n", encoding="ascii")


def ensure_windows_openmp_support() -> Path | None:
    if os.name != "nt":
        return None
    if PTHREAD_IMPORT_LIB.exists():
        return BUILD_DIR
    if not PTHREAD_DLL.exists():
        raise RuntimeError("Nao foi possivel localizar pthreadGC-3.dll em C:\\MinGW\\bin.")
    dlltool = shutil.which("dlltool")
    if not dlltool:
        raise RuntimeError("dlltool nao esta disponivel no PATH.")
    write_pthread_def()
    result = subprocess.run(
        [dlltool, "-d", str(PTHREAD_DEF), "-D", "pthreadGC-3.dll", "-l", str(PTHREAD_IMPORT_LIB)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Falha ao gerar libpthread:\n{result.stderr.strip()}")
    return BUILD_DIR


def compile_program(program: dict) -> None:
    gcc = shutil.which("gcc")
    if not gcc:
        raise RuntimeError("gcc nao encontrado no PATH.")
    cmd = ["gcc", "-O2", "-fopenmp", str(program["source"]), "-o", str(program["binary"]), "-lm"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return
    if os.name == "nt" and "cannot find -lpthread" in result.stderr:
        lib_dir = ensure_windows_openmp_support()
        cmd += ["-L", str(lib_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return
    raise RuntimeError(f"Falha ao compilar {program['source']}:\n{result.stderr.strip()}")


def compile_programs() -> None:
    ensure_dirs()
    for program in PROGRAMS:
        compile_program(program)
        print(f"  [ok] compilado: {Path(str(program['source'])).name}")


def build_env(threads: int) -> dict[str, str]:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"] = "FALSE"
    return env


def parse_output(output: str) -> dict:
    config = None
    result = None
    for raw in output.splitlines():
        line = raw.strip()
        config_match = CONFIG_RE.match(line)
        if config_match:
            config = {
                "program": config_match.group(1),
                "n": int(config_match.group(2)),
                "threads": int(config_match.group(3)),
            }
            continue
        result_match = RESULT_RE.match(line)
        if result_match:
            result = {
                "pi": float(result_match.group(1)),
                "count": int(result_match.group(2)),
                "total": int(result_match.group(3)),
                "error": float(result_match.group(4)),
                "elapsed": float(result_match.group(5)),
            }
    if config is None or result is None:
        raise RuntimeError(f"Saida invalida:\n{output}")
    return {**config, **result}


def validate_run(parsed: dict) -> tuple[bool, str]:
    if parsed["count"] < 0 or parsed["count"] > parsed["n"]:
        return False, "count fora do intervalo [0, N]"
    if parsed["total"] != parsed["n"]:
        return False, "total diferente de N"
    if not (2.5 <= parsed["pi"] <= 3.8):
        return False, "pi fora da faixa plausivel"
    if not math.isfinite(parsed["elapsed"]) or parsed["elapsed"] < 0.0:
        return False, "elapsed invalido"
    return True, "ok"


def run_once(program: dict, threads: int, n: int) -> dict:
    result = subprocess.run(
        [str(program["binary"]), str(n)],
        capture_output=True,
        text=True,
        env=build_env(threads),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha em {program['id']} ({threads} threads):\n{result.stderr.strip()}"
        )
    parsed = parse_output(result.stdout)
    is_valid, validation_note = validate_run(parsed)
    if parsed["program"] != program["id"]:
        raise RuntimeError(
            f"Programa retornou id inesperado: esperado={program['id']} obtido={parsed['program']}"
        )
    parsed["is_valid"] = is_valid
    parsed["validation_note"] = validation_note
    return parsed


def collect_runs(n: int, runs_per_thread: int) -> list[dict]:
    rows: list[dict] = []
    total = len(PROGRAMS) * len(THREAD_COUNTS) * runs_per_thread
    done = 0

    for program in PROGRAMS:
        for threads in THREAD_COUNTS:
            for run_id in range(1, runs_per_thread + 1):
                parsed = run_once(program, threads, n)
                rows.append({
                    "program_id": program["id"],
                    "program_label": program["label"],
                    "source_file": Path(str(program["source"])).name,
                    "requested_threads": threads,
                    "run_id": run_id,
                    "n": parsed["n"],
                    "actual_threads": parsed["threads"],
                    "pi": f"{parsed['pi']:.10f}",
                    "count": parsed["count"],
                    "error": f"{parsed['error']:.10f}",
                    "elapsed_seconds": f"{parsed['elapsed']:.6f}",
                    "is_valid": int(parsed["is_valid"]),
                    "validation_note": parsed["validation_note"],
                })
                done += 1
                pct = done / total * 100.0
                print(
                    f"  [{done:3d}/{total}  {pct:5.1f}%] {program['id']:18s} "
                    f"threads={threads:2d} run={run_id:2d} "
                    f"{parsed['elapsed']:.3f}s valid={parsed['is_valid']}"
                )
    return rows


def save_csv(rows: list[dict]) -> None:
    if not rows:
        return
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _rows_for(rows: list[dict], program_id: str, threads: int) -> list[dict]:
    return [
        row for row in rows
        if row["program_id"] == program_id and int(row["requested_threads"]) == threads
    ]


def _mean_elapsed(rows: list[dict], program_id: str, threads: int) -> float:
    vals = [float(row["elapsed_seconds"]) for row in _rows_for(rows, program_id, threads)]
    return statistics.mean(vals) if vals else 0.0


def _comparison_text(base_time: float, candidate_time: float) -> str:
    if base_time <= 0.0 or candidate_time <= 0.0:
        return "sem dados suficientes"
    ratio = candidate_time / base_time
    if math.isclose(ratio, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        return "empatadas"
    if candidate_time < base_time:
        gain = (1.0 - ratio) * 100.0
        return f"{gain:.1f}% mais rapido"
    loss = (ratio - 1.0) * 100.0
    return f"{loss:.1f}% mais lento"


def summarise_rows(rows: list[dict]) -> dict:
    programs_summary = []
    for program in PROGRAMS:
        per_thread = []
        for threads in THREAD_COUNTS:
            group = _rows_for(rows, program["id"], threads)
            elapsed_vals = [float(row["elapsed_seconds"]) for row in group]
            errors = [float(row["error"]) for row in group]
            pis = [float(row["pi"]) for row in group]
            per_thread.append({
                "requested_threads": threads,
                "runs": len(group),
                "avg_elapsed_seconds": round(statistics.mean(elapsed_vals), 6) if elapsed_vals else 0.0,
                "min_elapsed_seconds": round(min(elapsed_vals), 6) if elapsed_vals else 0.0,
                "max_elapsed_seconds": round(max(elapsed_vals), 6) if elapsed_vals else 0.0,
                "median_elapsed_seconds": round(statistics.median(elapsed_vals), 6) if elapsed_vals else 0.0,
                "avg_error": round(statistics.mean(errors), 10) if errors else 0.0,
                "avg_pi": round(statistics.mean(pis), 10) if pis else 0.0,
                "all_valid": all(int(row["is_valid"]) == 1 for row in group),
            })
        programs_summary.append({
            "id": program["id"],
            "label": program["label"],
            "source": Path(str(program["source"])).name,
            "notes": program["notes"],
            "per_thread": per_thread,
        })

    fixed_threads = THREAD_COUNTS[-1]
    comparisons = []
    for left, right in COMPARISON_GROUPS:
        left_time = _mean_elapsed(rows, left, fixed_threads)
        right_time = _mean_elapsed(rows, right, fixed_threads)
        comparisons.append({
            "left": left,
            "right": right,
            "threads": fixed_threads,
            "left_avg_elapsed_seconds": round(left_time, 6),
            "right_avg_elapsed_seconds": round(right_time, 6),
            "relative_to_left": _comparison_text(left_time, right_time),
        })

    rankings = []
    for threads in THREAD_COUNTS:
        ranking = []
        for program in PROGRAMS:
            avg_time = _mean_elapsed(rows, program["id"], threads)
            ranking.append({
                "id": program["id"],
                "label": program["label"],
                "avg_elapsed_seconds": round(avg_time, 6),
            })
        ranking.sort(key=lambda item: item["avg_elapsed_seconds"])
        rankings.append({"threads": threads, "ranking": ranking})

    return {
        "task": "Tarefa 10",
        "platform": {
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "python": sys.version.split()[0],
        },
        "config": {
            "threads_tested": THREAD_COUNTS,
            "n": int(rows[0]["n"]) if rows else 0,
            "runs_per_thread": max(int(row["run_id"]) for row in rows) if rows else 0,
            "fixed_bar_threads": fixed_threads,
        },
        "programs": programs_summary,
        "comparisons": comparisons,
        "rankings": rankings,
    }


def save_json(summary: dict) -> None:
    JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def plot_summary(summary: dict) -> None:
    if not HAS_MATPLOTLIB:
        return

    prog_map = {program["id"]: program for program in summary["programs"]}
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

    for pid, program in prog_map.items():
        threads = [pt["requested_threads"] for pt in program["per_thread"]]
        times = [pt["avg_elapsed_seconds"] * 1000.0 for pt in program["per_thread"]]
        ax_time.plot(
            threads,
            times,
            marker=MARKERS[pid],
            color=COLORS[pid],
            linewidth=2,
            label=program["label"],
        )
    ax_time.set_title("Tempo medio de execucao")
    ax_time.set_xlabel("Threads")
    ax_time.set_ylabel("Tempo (ms)")
    ax_time.grid(True, linestyle="--", alpha=0.4)
    ax_time.legend(fontsize=8)

    for pid, program in prog_map.items():
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
                marker=MARKERS[pid],
                color=COLORS[pid],
                linewidth=2,
                label=program["label"],
            )
    max_threads = max(THREAD_COUNTS)
    ax_speedup.plot([1, max_threads], [1, max_threads], "k--", linewidth=1, label="Ideal")
    ax_speedup.set_title("Speedup relativo a 1 thread")
    ax_speedup.set_xlabel("Threads")
    ax_speedup.set_ylabel("Speedup")
    ax_speedup.grid(True, linestyle="--", alpha=0.4)
    ax_speedup.legend(fontsize=8)

    for pid, program in prog_map.items():
        threads = [pt["requested_threads"] for pt in program["per_thread"]]
        errors = [pt["avg_error"] for pt in program["per_thread"]]
        ax_error.plot(
            threads,
            errors,
            marker=MARKERS[pid],
            color=COLORS[pid],
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
    for program in PROGRAMS:
        pt = next(
            (item for item in prog_map[program["id"]]["per_thread"] if item["requested_threads"] == fixed_threads),
            None,
        )
        if pt:
            labels.append(program["label"])
            values.append(pt["avg_elapsed_seconds"] * 1000.0)
            colors.append(COLORS[program["id"]])
    ax_bar.bar(range(len(labels)), values, color=colors, edgecolor="black", linewidth=0.8)
    ax_bar.set_xticks(range(len(labels)))
    ax_bar.set_xticklabels(labels, rotation=18, ha="right", fontsize=8)
    ax_bar.set_title(f"Comparacao direta com {fixed_threads} threads")
    ax_bar.set_ylabel("Tempo (ms)")
    ax_bar.grid(True, axis="y", linestyle="--", alpha=0.4)

    fig.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _table(program: dict) -> str:
    headers = ["Threads", "Rodadas", "Media (ms)", "Min (ms)", "Max (ms)", "Erro medio", "Validas"]
    separator = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = ["|" + "|".join(headers) + "|", separator]
    for pt in program["per_thread"]:
        lines.append(
            "|"
            + "|".join([
                str(pt["requested_threads"]),
                str(pt["runs"]),
                f"{pt['avg_elapsed_seconds'] * 1000:.3f}",
                f"{pt['min_elapsed_seconds'] * 1000:.3f}",
                f"{pt['max_elapsed_seconds'] * 1000:.3f}",
                f"{pt['avg_error']:.8f}",
                "sim" if pt["all_valid"] else "**nao**",
            ])
            + "|"
        )
    return "\n".join(lines)


def _comparison_bullets(summary: dict) -> str:
    labels = {program["id"]: program["label"] for program in summary["programs"]}
    lines = []
    for item in summary["comparisons"]:
        left_label = labels[item["left"]]
        right_label = labels[item["right"]]
        left_ms = item["left_avg_elapsed_seconds"] * 1000
        right_ms = item["right_avg_elapsed_seconds"] * 1000
        if item["left_avg_elapsed_seconds"] == 0.0 and item["right_avg_elapsed_seconds"] == 0.0:
            detail = "ambas ficaram abaixo da resolucao do timer."
        elif item["left_avg_elapsed_seconds"] == 0.0 or item["right_avg_elapsed_seconds"] == 0.0:
            detail = "comparacao limitada pela resolucao do timer."
        else:
            detail = f"{right_label} ficou {item['relative_to_left']}."
        lines.append(
            f"- {left_label} vs {right_label} ({item['threads']} threads): "
            f"{left_ms:.3f} ms vs {right_ms:.3f} ms; {detail}"
        )
    return "\n".join(lines)


def _ranking_text(summary: dict) -> str:
    lines = []
    for block in summary["rankings"]:
        ranking = ", ".join(
            f"{item['id']}={item['avg_elapsed_seconds'] * 1000:.2f}ms"
            for item in block["ranking"]
        )
        lines.append(f"- {block['threads']} threads: {ranking}")
    return "\n".join(lines)


def build_report(summary: dict) -> str:
    n_value = summary["config"]["n"]
    runs = summary["config"]["runs_per_thread"]
    threads = ", ".join(map(str, summary["config"]["threads_tested"]))
    fixed_threads = summary["config"]["fixed_bar_threads"]

    image_block = "![Grafico Tarefa 10](tarefa10_resultados.png)" if PLOT_PATH.exists() else ""
    tables = "\n\n".join(
        f"### {program['label']}\n\n_{program['notes']}_\n\n{_table(program)}"
        for program in summary["programs"]
    )
    artifacts = "\n".join([
        "- CSV bruto: `Tarefa-10/dados/tarefa10_runs.csv`",
        "- Resumo JSON: `Tarefa-10/dados/tarefa10_summary.json`",
        *(["- Grafico: `Tarefa-10/relatorios/tarefa10_resultados.png`"] if PLOT_PATH.exists() else []),
        "- Relatorio: `Tarefa-10/relatorios/relatorio_tarefa10.md`",
    ])

    run_cmd = """```bash
sudo apt update && sudo apt install -y build-essential python3 python3-pip
python3 -m pip install --user matplotlib

cd atividades-aula
python3 Tarefa-10/run_tests.py
```"""

    report_only_cmd = """```bash
python3 Tarefa-10/run_tests.py --report-only
```"""

    return f"""# Tarefa 10 - Comparar critical, atomic, contadores privados e reduction no estimador de PI

## Objetivo

Implementar cinco versoes da estimativa de PI, todas usando `rand_r()` com seed privada
por thread, para comparar custo de sincronizacao, speedup, corretude e impacto de
false sharing. O foco agora nao e mais o gerador aleatorio, e sim **como os acertos
sao acumulados**.

## Como rodar no Ubuntu

{run_cmd}

Para regenerar apenas grafico e relatorio a partir do JSON salvo:

{report_only_cmd}

Argumentos opcionais: `python3 Tarefa-10/run_tests.py [N] [rodadas]`

## Configuracao

- N = {n_value:,} pontos por execucao
- {runs} rodadas por configuracao de threads
- Threads testadas: {threads}
- Compilacao: `gcc -O2 -fopenmp`
- Escalonamento: `schedule(static)` em todas as versoes

## Programas comparados

| ID | Arquivo | Estrategia |
|---|---|---|
| shared_critical  | pi_randr_shared_critical.c  | contador global com `critical` a cada acerto |
| shared_atomic    | pi_randr_shared_atomic.c    | contador global com `atomic` a cada acerto |
| private_critical | pi_randr_private_critical.c | contador local por thread + `critical` final |
| private_vector   | pi_randr_private_vector.c   | `hits[tid]` em vetor compartilhado |
| reduction        | pi_randr_reduction.c        | `reduction(+:count)` |

## Resultados por programa

{tables}

{image_block}

## Comparacoes diretas ({fixed_threads} threads)

{_comparison_bullets(summary)}

## Ranking por numero de threads

{_ranking_text(summary)}

## Analise conceitual

### 1. shared_critical vs shared_atomic

As duas versoes atualizam a mesma variavel global em alta frequencia. A diferenca e
que `atomic` protege exatamente a operacao de incremento, enquanto `critical` precisa
entrar e sair de uma regiao mutua mais geral. Para `count++`, `atomic` tende a ser a
escolha correta porque expressa melhor a intencao e reduz overhead.

### 2. shared_* vs private_critical

Mover a contagem para uma variavel privada por thread reduz drasticamente a contencao:
em vez de sincronizar a cada acerto, cada thread sincroniza apenas uma vez no final.
Essa mudanca costuma produzir um salto de desempenho muito maior do que trocar
`critical` por `atomic`.

### 3. private_critical vs private_vector

Ambas evitam disputar uma variavel global a cada acerto, mas `private_vector`
materializa os contadores em um vetor compartilhado contiguo. Isso pode introduzir
false sharing: threads escrevem em posicoes diferentes, porem no mesmo cache line.
`private_critical` normalmente vence porque preserva os contadores no contexto local
da thread durante quase toda a execucao.

### 4. Todas as anteriores vs reduction

`reduction(+:count)` e o caso mais natural para OpenMP: soma associativa simples.
O compilador/runtime criam acumuladores privados e fazem a combinacao final de forma
otimizada. Alem do desempenho esperado, a versao e a mais curta e menos sujeita a
erros de sincronizacao no codigo-fonte.

## Roteiro de escolha do mecanismo

- Use `reduction` quando o problema for uma reducao associativa simples, como soma, maximo ou minimo.
- Use `atomic` quando houver uma atualizacao simples em variavel compartilhada e a operacao nao puder ser modelada como `reduction`.
- Use `critical` para trechos curtos que exigem exclusao mutua, mas nao cabem em `atomic`.
- Use `critical(nome)` quando existirem poucos recursos fixos independentes conhecidos em tempo de compilacao.
- Use `omp_lock_t` quando a granularidade do bloqueio precisar ser dinamica em tempo de execucao.

## Conclusao

O experimento separa dois tipos de decisao. A primeira e **micro**: entre `critical`
e `atomic`, `atomic` costuma ganhar quando a operacao e apenas um incremento. A segunda
e **estrutural**: evitar sincronizacao por iteracao quase sempre vale mais do que
otimizar a forma da trava. Por isso, `private_critical` e `reduction` tendem a dominar
as versoes com contador compartilhado. Entre elas, `reduction` costuma ser a melhor
combinacao de produtividade e desempenho quando o padrao do problema coincide com uma
reducao classica.

## Artefatos gerados

{artifacts}
"""


def save_report(summary: dict) -> None:
    REPORT_PATH.write_text(build_report(summary), encoding="utf-8", newline="\n")


def report_only() -> int:
    if not JSON_PATH.exists():
        raise RuntimeError(f"JSON nao encontrado em {JSON_PATH}. Execute a coleta antes de --report-only.")
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    plot_summary(summary)
    save_report(summary)
    print("Relatorio/grafico regenerados com sucesso.")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico:   {PLOT_PATH}")
    print(f"  Relatorio: {REPORT_PATH}")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--report-only":
        return report_only()

    n = DEFAULT_N
    runs = DEFAULT_RUNS

    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    if len(sys.argv) > 2:
        runs = int(sys.argv[2])

    print(f"Tarefa 10 - N={n:,}  rodadas={runs}  threads={THREAD_COUNTS}")
    print()

    print("[1/4] Compilando programas...")
    compile_programs()
    print()

    print("[2/4] Coletando dados...")
    rows = collect_runs(n, runs)
    print()

    print("[3/4] Salvando CSV e JSON...")
    save_csv(rows)
    summary = summarise_rows(rows)
    save_json(summary)

    print("[4/4] Gerando grafico e relatorio...")
    plot_summary(summary)
    save_report(summary)
    print()

    print("Concluido!")
    print(f"  CSV:       {CSV_PATH}")
    print(f"  JSON:      {JSON_PATH}")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico:   {PLOT_PATH}")
    else:
        print("  Grafico:   nao gerado (matplotlib indisponivel).")
    print(f"  Relatorio: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
