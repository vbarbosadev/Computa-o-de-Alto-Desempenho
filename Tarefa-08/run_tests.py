#!/usr/bin/env python3
"""
Tarefa 8 - Coerencia de cache e falso compartilhamento

Compara quatro versoes da estimativa estocastica de PI:

  1. rand_critical  - rand()   + variavel privada + #pragma omp critical
  2. rand_vector    - rand()   + vetor compartilhado (false sharing)
  3. randr_critical - rand_r() + variavel privada + #pragma omp critical
  4. randr_vector   - rand_r() + vetor compartilhado (false sharing)

Objetivo: medir o impacto de:
  - Thread-safety do RNG (rand vs rand_r)
  - Estrategia de acumulacao (critical vs vetor com false sharing)
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
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


ROOT_DIR   = Path(__file__).resolve().parent.parent
TASK_DIR   = Path(__file__).resolve().parent
BUILD_DIR  = TASK_DIR / "build"
DATA_DIR   = ROOT_DIR / "dados"
REPORT_DIR = ROOT_DIR / "relatorios"

CSV_PATH    = DATA_DIR   / "tarefa8_runs.csv"
JSON_PATH   = DATA_DIR   / "tarefa8_summary.json"
PLOT_PATH   = REPORT_DIR / "tarefa8_resultados.png"
REPORT_PATH = REPORT_DIR / "relatorio_tarefa08.md"

DEFAULT_N    = 10_000_000
DEFAULT_RUNS = 10

PTHREAD_DLL        = Path(r"C:\MinGW\bin\pthreadGC-3.dll")
PTHREAD_DEF        = BUILD_DIR / "pthreadGC-3.def"
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
        "id":     "rand_critical",
        "label":  "rand() + critical",
        "source": TASK_DIR / "pi_rand_critical.c",
        "binary": BUILD_DIR / "pi_rand_critical",
        "notes":  "rand() nao e thread-safe; variavel privada por thread acumulada com critical.",
    },
    {
        "id":     "rand_vector",
        "label":  "rand() + vetor",
        "source": TASK_DIR / "pi_rand_vector.c",
        "binary": BUILD_DIR / "pi_rand_vector",
        "notes":  "rand() nao e thread-safe; acertos em hits[tid] — false sharing no vetor.",
    },
    {
        "id":     "randr_critical",
        "label":  "rand_r() + critical",
        "source": TASK_DIR / "pi_randr_critical.c",
        "binary": BUILD_DIR / "pi_randr_critical",
        "notes":  "rand_r() com seed privada; variavel privada acumulada com critical.",
    },
    {
        "id":     "randr_vector",
        "label":  "rand_r() + vetor",
        "source": TASK_DIR / "pi_randr_vector.c",
        "binary": BUILD_DIR / "pi_randr_vector",
        "notes":  "rand_r() com seed privada; acertos em hits[tid] — false sharing no vetor.",
    },
]


# ---------------------------------------------------------------------------
# Helpers de ambiente
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Compilacao
# ---------------------------------------------------------------------------

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
        capture_output=True, text=True,
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
    for p in PROGRAMS:
        compile_program(p)
        print(f"  [ok] compilado: {Path(str(p['source'])).name}")


# ---------------------------------------------------------------------------
# Execucao e parse
# ---------------------------------------------------------------------------

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
        m = CONFIG_RE.match(line)
        if m:
            config = {"program": m.group(1), "n": int(m.group(2)), "threads": int(m.group(3))}
            continue
        m = RESULT_RE.match(line)
        if m:
            result = {
                "pi":      float(m.group(1)),
                "count":   int(m.group(2)),
                "total":   int(m.group(3)),
                "error":   float(m.group(4)),
                "elapsed": float(m.group(5)),
            }
    if config is None or result is None:
        raise RuntimeError(f"Saida invalida:\n{output}")
    return {**config, **result}


def run_once(program: dict, threads: int, n: int) -> dict:
    result = subprocess.run(
        [str(program["binary"]), str(n)],
        capture_output=True, text=True,
        env=build_env(threads),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha em {program['source']} ({threads} threads):\n{result.stderr.strip()}"
        )
    return parse_output(result.stdout)


def collect_runs(n: int, runs_per_thread: int) -> list[dict]:
    rows: list[dict] = []
    total = len(PROGRAMS) * len(THREAD_COUNTS) * runs_per_thread
    done  = 0
    for prog in PROGRAMS:
        for threads in THREAD_COUNTS:
            for run_id in range(1, runs_per_thread + 1):
                parsed = run_once(prog, threads, n)
                rows.append({
                    "program_id":        prog["id"],
                    "program_label":     prog["label"],
                    "source_file":       Path(str(prog["source"])).name,
                    "requested_threads": threads,
                    "run_id":            run_id,
                    "n":                 parsed["n"],
                    "actual_threads":    parsed["threads"],
                    "pi":                f"{parsed['pi']:.10f}",
                    "count":             parsed["count"],
                    "error":             f"{parsed['error']:.10f}",
                    "elapsed_seconds":   f"{parsed['elapsed']:.6f}",
                })
                done += 1
                pct = done / total * 100
                print(f"  [{done:3d}/{total}  {pct:5.1f}%] {prog['id']:20s} threads={threads} run={run_id}  {parsed['elapsed']:.3f}s")
    return rows


# ---------------------------------------------------------------------------
# CSV / JSON
# ---------------------------------------------------------------------------

def save_csv(rows: list[dict]) -> None:
    if not rows:
        return
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarise_rows(rows: list[dict]) -> dict:
    from collections import defaultdict

    grouped: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["program_id"]][int(row["requested_threads"])].append(row)

    programs_summary = []
    for prog in PROGRAMS:
        per_thread = []
        for threads in THREAD_COUNTS:
            g = grouped[prog["id"]][threads]
            elapsed_vals = [float(r["elapsed_seconds"]) for r in g]
            errors       = [float(r["error"])           for r in g]
            per_thread.append({
                "requested_threads":    threads,
                "runs":                 len(g),
                "avg_elapsed_seconds":  round(statistics.mean(elapsed_vals), 6)  if elapsed_vals else 0.0,
                "min_elapsed_seconds":  round(min(elapsed_vals), 6)              if elapsed_vals else 0.0,
                "max_elapsed_seconds":  round(max(elapsed_vals), 6)              if elapsed_vals else 0.0,
                "median_elapsed_seconds": round(statistics.median(elapsed_vals), 6) if elapsed_vals else 0.0,
                "avg_error":            round(statistics.mean(errors), 10)       if errors       else 0.0,
            })
        programs_summary.append({
            "id":         prog["id"],
            "label":      prog["label"],
            "source":     Path(str(prog["source"])).name,
            "notes":      prog["notes"],
            "per_thread": per_thread,
        })

    return {
        "task": "Tarefa 8",
        "platform": {
            "os":        platform.system(),
            "version":   platform.version(),
            "machine":   platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "python":    sys.version.split()[0],
        },
        "config": {
            "threads_tested":  THREAD_COUNTS,
            "n":               int(rows[0]["n"]) if rows else 0,
            "runs_per_thread": max(int(r["run_id"]) for r in rows) if rows else 0,
        },
        "programs": programs_summary,
    }


def save_json(summary: dict) -> None:
    JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Grafico
# ---------------------------------------------------------------------------

COLORS = {
    "rand_critical":  "#E74C3C",
    "rand_vector":    "#E67E22",
    "randr_critical": "#2E86DE",
    "randr_vector":   "#27AE60",
}
MARKERS = {
    "rand_critical":  "o",
    "rand_vector":    "s",
    "randr_critical": "^",
    "randr_vector":   "D",
}


def plot_summary(summary: dict) -> None:
    if not HAS_MATPLOTLIB:
        return

    prog_map = {p["id"]: p for p in summary["programs"]}
    n_val    = summary["config"]["n"]

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        f"Tarefa 8 — Coerencia de cache e falso compartilhamento  (N={n_val:,})",
        fontsize=13, fontweight="bold",
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.32)

    ax_time    = fig.add_subplot(gs[0, 0])
    ax_speedup = fig.add_subplot(gs[0, 1])
    ax_bar_2t  = fig.add_subplot(gs[1, 0])
    ax_err     = fig.add_subplot(gs[1, 1])

    # --- tempo medio ---
    for pid, prog in prog_map.items():
        threads = [pt["requested_threads"]    for pt in prog["per_thread"]]
        times   = [pt["avg_elapsed_seconds"] * 1000 for pt in prog["per_thread"]]
        ax_time.plot(threads, times, marker=MARKERS[pid], color=COLORS[pid],
                     linewidth=2, label=prog["label"])
    ax_time.set_title("Tempo medio de execucao")
    ax_time.set_xlabel("Threads")
    ax_time.set_ylabel("Tempo (ms)")
    ax_time.grid(True, linestyle="--", alpha=0.4)
    ax_time.legend(fontsize=8)

    # --- speedup relativo ao proprio t=1 ---
    for pid, prog in prog_map.items():
        base = next((pt["avg_elapsed_seconds"] for pt in prog["per_thread"]
                     if pt["requested_threads"] == 1), None)
        if base and base > 0:
            threads = [pt["requested_threads"] for pt in prog["per_thread"]]
            speedup = [base / pt["avg_elapsed_seconds"] if pt["avg_elapsed_seconds"] > 0 else 0
                       for pt in prog["per_thread"]]
            ax_speedup.plot(threads, speedup, marker=MARKERS[pid], color=COLORS[pid],
                            linewidth=2, label=prog["label"])
    # linha ideal
    max_t = max(THREAD_COUNTS)
    ax_speedup.plot([1, max_t], [1, max_t], "k--", linewidth=1, label="Ideal")
    ax_speedup.set_title("Speedup (relativo a 1 thread)")
    ax_speedup.set_xlabel("Threads")
    ax_speedup.set_ylabel("Speedup")
    ax_speedup.grid(True, linestyle="--", alpha=0.4)
    ax_speedup.legend(fontsize=8)

    # --- comparacao em barras para 2 threads ---
    target_t = 2 if 2 in THREAD_COUNTS else THREAD_COUNTS[-1]
    labels_bar, times_bar, colors_bar = [], [], []
    for pid, prog in prog_map.items():
        pt = next((p for p in prog["per_thread"] if p["requested_threads"] == target_t), None)
        if pt:
            labels_bar.append(prog["label"])
            times_bar.append(pt["avg_elapsed_seconds"] * 1000)
            colors_bar.append(COLORS[pid])
    ax_bar_2t.bar(range(len(labels_bar)), times_bar, color=colors_bar, edgecolor="black", linewidth=0.8)
    ax_bar_2t.set_xticks(range(len(labels_bar)))
    ax_bar_2t.set_xticklabels(labels_bar, rotation=15, ha="right", fontsize=8)
    ax_bar_2t.set_title(f"Tempo medio com {target_t} threads")
    ax_bar_2t.set_ylabel("Tempo (ms)")
    ax_bar_2t.grid(True, axis="y", linestyle="--", alpha=0.4)

    # --- erro medio de PI ---
    for pid, prog in prog_map.items():
        threads = [pt["requested_threads"] for pt in prog["per_thread"]]
        errors  = [pt["avg_error"]         for pt in prog["per_thread"]]
        ax_err.plot(threads, errors, marker=MARKERS[pid], color=COLORS[pid],
                    linewidth=2, label=prog["label"])
    ax_err.set_title("Erro medio da estimativa de PI")
    ax_err.set_xlabel("Threads")
    ax_err.set_ylabel("|pi_estimado - pi_real|")
    ax_err.grid(True, linestyle="--", alpha=0.4)
    ax_err.legend(fontsize=8)

    fig.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------

def _table(prog: dict) -> str:
    headers   = ["Threads", "Rodadas", "Media (ms)", "Min (ms)", "Max (ms)", "Erro medio"]
    separator = "|" + "|".join(["---"] * len(headers)) + "|"
    lines     = ["|" + "|".join(headers) + "|", separator]
    for pt in prog["per_thread"]:
        lines.append(
            "|"
            + "|".join([
                str(pt["requested_threads"]),
                str(pt["runs"]),
                f"{pt['avg_elapsed_seconds'] * 1000:.3f}",
                f"{pt['min_elapsed_seconds'] * 1000:.3f}",
                f"{pt['max_elapsed_seconds'] * 1000:.3f}",
                f"{pt['avg_error']:.8f}",
            ])
            + "|"
        )
    return "\n".join(lines)


def build_report(summary: dict) -> str:
    n_val   = summary["config"]["n"]
    runs    = summary["config"]["runs_per_thread"]
    threads = ", ".join(map(str, summary["config"]["threads_tested"]))
    prog_map = {p["id"]: p for p in summary["programs"]}

    image_block = "![Grafico Tarefa 8](tarefa8_resultados.png)" if PLOT_PATH.exists() else ""

    tables = "\n\n".join(
        f"### {p['label']}\n\n_{p['notes']}_\n\n{_table(p)}"
        for p in summary["programs"]
    )

    artifacts = "\n".join([
        "- CSV bruto: `dados/tarefa8_runs.csv`",
        "- Resumo JSON: `dados/tarefa8_summary.json`",
        *(["- Grafico: `relatorios/tarefa8_resultados.png`"] if PLOT_PATH.exists() else []),
        "- Relatorio: `relatorios/relatorio_tarefa08.md`",
    ])

    run_cmd = """```bash
sudo apt update && sudo apt install -y build-essential python3 python3-pip
python3 -m pip install --user matplotlib

cd atividades-aula
python3 Tarefa-08/run_tests.py
```"""

    report_only_cmd = """```bash
python3 Tarefa-08/run_tests.py --report-only
```"""

    return f"""# Tarefa 8 — Coerencia de cache e falso compartilhamento

## Objetivo

Implementar a estimativa estocastica de PI em quatro variantes que combinam
dois geradores de numeros aleatorios (`rand` e `rand_r`) com duas estrategias
de acumulacao (variavel privada + `critical`; vetor compartilhado com
false sharing). Comparar o desempenho das quatro versoes e explicar os
resultados com base na coerencia de cache.

## Como rodar no Ubuntu

{run_cmd}

Para regenerar apenas o grafico e o relatorio a partir do JSON ja salvo:

{report_only_cmd}

Argumentos opcionais: `python3 Tarefa-08/run_tests.py [N] [rodadas]`

## Configuracao

- N = {n_val:,} pontos por execucao
- {runs} rodadas por configuracao de threads
- Threads testadas: {threads}
- Compilacao: `gcc -O2 -fopenmp`

## Programas comparados

| ID | Arquivo | Gerador | Acumulacao |
|---|---|---|---|
| rand_critical  | pi_rand_critical.c  | `rand()`   | variavel privada + `critical` |
| rand_vector    | pi_rand_vector.c    | `rand()`   | `hits[tid]` (false sharing)   |
| randr_critical | pi_randr_critical.c | `rand_r()` | variavel privada + `critical` |
| randr_vector   | pi_randr_vector.c   | `rand_r()` | `hits[tid]` (false sharing)   |

## Resultados por programa

{tables}

{image_block}

## Analise e interpretacao

### 1. rand() vs rand_r()

`rand()` mantem um estado global unico protegido internamente por um mutex
(em implementacoes POSIX tipicas). Cada chamada feita por qualquer thread
adquire esse lock, serializa a geracao e libera. Com muitas threads, a
contenção no mutex do RNG pode dominar o tempo de execucao — o programa
passa mais tempo esperando o lock do que calculando pontos.

`rand_r()` recebe a seed por referencia: cada thread usa sua propria seed,
sem estado compartilhado e sem lock. A geracao torna-se verdadeiramente
paralela.

### 2. Variavel privada + critical vs vetor compartilhado (false sharing)

**Variavel privada + critical**: cada thread acumula em uma variavel local
(na sua pilha ou em um registrador). O `critical` e executado apenas uma
vez por thread, ao final do laco — o custo e minimo.

**Vetor compartilhado (false sharing)**: `hits[tid]` e uma posicao distinta
por thread, portanto nao ha corrida de dados. Porem, um cache line de
64 bytes armazena ate 8 `long` (8 bytes cada). Se threads 0 e 1 escrevem
em `hits[0]` e `hits[1]` respectivamente, ambas escrevem na **mesma linha
de cache**. Toda escrita de uma thread invalida a copia da linha nas demais,
forcando recargas constantes no protocolo de coerencia (MESI/MOESI). O
resultado e um aumento no trafego do barramento de cache — sem qualquer
beneficio logico — piorando o desempenho comparado a versao com variavel
privada.

### 3. Combinando os efeitos

| Versao | Gargalo principal |
|---|---|
| rand_critical  | Mutex do `rand()` + trafego de coerencia do estado global |
| rand_vector    | Mutex do `rand()` + false sharing no vetor                |
| randr_critical | Apenas o `critical` (1 vez por thread) — gargalo minimo  |
| randr_vector   | False sharing no vetor — visivel sem o ruido do mutex     |

A versao `randr_critical` tende a ser a mais rapida: elimina o mutex do
RNG e o false sharing simultaneamente. A versao `rand_vector` costuma ser
a mais lenta por acumular os dois problemas.

## Artefatos gerados

{artifacts}
"""


def save_report(summary: dict) -> None:
    REPORT_PATH.write_text(build_report(summary), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Modo --report-only
# ---------------------------------------------------------------------------

def report_only() -> int:
    if not JSON_PATH.exists():
        raise RuntimeError(
            f"JSON nao encontrado em {JSON_PATH}. Execute a coleta antes de --report-only."
        )
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    plot_summary(summary)
    save_report(summary)
    print("Relatorio/grafico regenerados com sucesso.")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico:   {PLOT_PATH}")
    print(f"  Relatorio: {REPORT_PATH}")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--report-only":
        return report_only()

    n    = DEFAULT_N
    runs = DEFAULT_RUNS

    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    if len(sys.argv) > 2:
        runs = int(sys.argv[2])

    print(f"Tarefa 8 — N={n:,}  rodadas={runs}  threads={THREAD_COUNTS}")
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
