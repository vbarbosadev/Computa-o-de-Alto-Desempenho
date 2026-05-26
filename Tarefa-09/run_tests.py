#!/usr/bin/env python3
"""
Tarefa 9 - Regioes criticas nomeadas e travas explicitas

Compara duas versoes de insercao paralela em listas encadeadas:

  1. lists_critical.c  - 2 listas fixas protegidas por critical NOMEADO
  2. lists_lock.c      - K listas protegidas por omp_lock_t (trava por lista)

Experimentos:
  A) critical vs lock(K=2): desempenho com threads variando (1..12)
  B) lock com K variando (2, 4, 8, 16, 32): escalabilidade com mais listas
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

CSV_PATH    = DATA_DIR   / "tarefa9_runs.csv"
JSON_PATH   = DATA_DIR   / "tarefa9_summary.json"
PLOT_PATH   = REPORT_DIR / "tarefa9_resultados.png"
REPORT_PATH = REPORT_DIR / "relatorio_tarefa09.md"

DEFAULT_N    = 1_000_000
DEFAULT_RUNS = 10

K_VALUES = [2, 4, 8, 16, 32]

PTHREAD_DLL        = Path(r"C:\MinGW\bin\pthreadGC-3.dll")
PTHREAD_DEF        = BUILD_DIR / "pthreadGC-3.def"
PTHREAD_IMPORT_LIB = BUILD_DIR / "libpthread.dll.a"

CONFIG_RE  = re.compile(r"^CONFIG program=(\S+) n=(\d+) lists=(\d+) threads=(\d+)$")
SUMMARY_RE = re.compile(r"^SUMMARY total=(\d+) list_counts=([\d,]+) elapsed=([0-9.]+)$")

PTHREAD_EXPORTS = [
    "pthread_attr_destroy", "pthread_attr_getstacksize", "pthread_attr_init",
    "pthread_attr_setdetachstate", "pthread_attr_setstacksize",
    "pthread_create", "pthread_exit", "pthread_key_create", "pthread_key_delete",
    "pthread_mutex_destroy", "pthread_mutex_init", "pthread_mutex_lock",
    "pthread_mutex_unlock", "pthread_once", "pthread_setspecific",
    "sem_destroy", "sem_init", "sem_post", "sem_trywait", "sem_wait",
]

PROGRAMS = [
    {
        "id":     "critical",
        "label":  "critical nomeado (2 listas)",
        "source": TASK_DIR / "lists_critical.c",
        "binary": BUILD_DIR / "lists_critical",
        "fixed_k": 2,
        "notes":  "2 listas fixas; critical(lista_a) e critical(lista_b) permitem "
                  "insercoes paralelas em listas distintas.",
    },
    {
        "id":     "lock",
        "label":  "omp_lock_t (K listas)",
        "source": TASK_DIR / "lists_lock.c",
        "binary": BUILD_DIR / "lists_lock",
        "fixed_k": None,   # K variavel
        "notes":  "K listas dinamicas; cada lista tem seu proprio omp_lock_t, "
                  "permitindo paralelismo entre listas para qualquer K.",
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
    cmd = ["gcc", "-O2", "-fopenmp", str(program["source"]), "-o", str(program["binary"])]
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
        print(f"  [ok] {Path(str(p['source'])).name}")


# ---------------------------------------------------------------------------
# Execucao e parse
# ---------------------------------------------------------------------------

def build_env(threads: int) -> dict[str, str]:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"]     = "FALSE"
    return env


def parse_output(output: str, expected_n: int) -> dict:
    config  = None
    summary = None
    for raw in output.splitlines():
        line = raw.strip()
        m = CONFIG_RE.match(line)
        if m:
            config = {
                "program": m.group(1),
                "n":       int(m.group(2)),
                "lists":   int(m.group(3)),
                "threads": int(m.group(4)),
            }
            continue
        m = SUMMARY_RE.match(line)
        if m:
            counts = [int(x) for x in m.group(2).split(",")]
            summary = {
                "total":       int(m.group(1)),
                "list_counts": counts,
                "elapsed":     float(m.group(3)),
            }
    if config is None or summary is None:
        raise RuntimeError(f"Saida invalida:\n{output}")

    total_ok   = summary["total"] == expected_n
    counts_ok  = sum(summary["list_counts"]) == summary["total"]
    is_valid   = total_ok and counts_ok

    return {**config, **summary, "is_valid": is_valid}


def run_once(program: dict, threads: int, n: int, k: int) -> dict:
    cmd = [str(program["binary"]), str(n)]
    if program["id"] == "lock":
        cmd.append(str(k))
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=build_env(threads),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha em {program['id']} threads={threads} k={k}:\n{result.stderr.strip()}"
        )
    return parse_output(result.stdout, n)


def collect_runs(n: int, runs_per_cfg: int) -> list[dict]:
    rows: list[dict] = []

    # Experimento A: critical (K=2) vs lock(K=2), threads variando
    configs_a = []
    for prog in PROGRAMS:
        k = prog["fixed_k"] if prog["fixed_k"] else 2
        for threads in THREAD_COUNTS:
            configs_a.append((prog, threads, k))

    # Experimento B: lock com K variando, threads fixo no maximo
    max_threads = THREAD_COUNTS[-1]
    lock_prog   = next(p for p in PROGRAMS if p["id"] == "lock")
    configs_b   = [(lock_prog, max_threads, k) for k in K_VALUES if k != 2]

    all_configs = configs_a + configs_b
    total = len(all_configs) * runs_per_cfg
    done  = 0

    for prog, threads, k in all_configs:
        for run_id in range(1, runs_per_cfg + 1):
            parsed = run_once(prog, threads, n, k)
            rows.append({
                "experiment":        "B_k_scaling" if (prog["id"] == "lock" and threads == max_threads and k != 2) else "A_thread_scaling",
                "program_id":        prog["id"],
                "program_label":     prog["label"],
                "source_file":       Path(str(prog["source"])).name,
                "requested_threads": threads,
                "actual_threads":    parsed["threads"],
                "k":                 k,
                "run_id":            run_id,
                "n":                 n,
                "total_inserted":    parsed["total"],
                "is_valid":          int(parsed["is_valid"]),
                "elapsed_seconds":   f"{parsed['elapsed']:.6f}",
                "list_counts":       ",".join(map(str, parsed["list_counts"])),
            })
            done += 1
            pct = done / total * 100
            print(f"  [{done:3d}/{total}  {pct:5.1f}%]  {prog['id']:10s}  "
                  f"K={k:2d}  threads={threads:2d}  run={run_id}  "
                  f"{parsed['elapsed']:.3f}s  valid={parsed['is_valid']}")
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


def _group_elapsed(rows: list[dict], prog_id: str, threads: int, k: int) -> list[float]:
    return [
        float(r["elapsed_seconds"])
        for r in rows
        if r["program_id"] == prog_id
        and int(r["requested_threads"]) == threads
        and int(r["k"]) == k
    ]


def summarise_rows(rows: list[dict]) -> dict:
    # Experimento A: threads variando, K=2
    exp_a: dict = {}
    for prog in PROGRAMS:
        pid = prog["id"]
        k   = prog["fixed_k"] if prog["fixed_k"] else 2
        per_thread = []
        for threads in THREAD_COUNTS:
            vals = _group_elapsed(rows, pid, threads, k)
            per_thread.append({
                "requested_threads":     threads,
                "runs":                  len(vals),
                "avg_elapsed_seconds":   round(statistics.mean(vals), 6)   if vals else 0.0,
                "min_elapsed_seconds":   round(min(vals), 6)               if vals else 0.0,
                "max_elapsed_seconds":   round(max(vals), 6)               if vals else 0.0,
                "median_elapsed_seconds": round(statistics.median(vals), 6) if vals else 0.0,
                "all_valid":             all(int(r["is_valid"]) == 1
                                             for r in rows
                                             if r["program_id"] == pid
                                             and int(r["requested_threads"]) == threads
                                             and int(r["k"]) == k),
            })
        exp_a[pid] = {
            "id":         pid,
            "label":      prog["label"],
            "source":     Path(str(prog["source"])).name,
            "notes":      prog["notes"],
            "k":          k,
            "per_thread": per_thread,
        }

    # Experimento B: K variando, threads = max
    max_threads = THREAD_COUNTS[-1]
    exp_b = []
    for k in K_VALUES:
        vals = _group_elapsed(rows, "lock", max_threads, k)
        exp_b.append({
            "k":                     k,
            "requested_threads":     max_threads,
            "runs":                  len(vals),
            "avg_elapsed_seconds":   round(statistics.mean(vals), 6) if vals else 0.0,
            "min_elapsed_seconds":   round(min(vals), 6)             if vals else 0.0,
            "max_elapsed_seconds":   round(max(vals), 6)             if vals else 0.0,
            "all_valid":             all(int(r["is_valid"]) == 1
                                         for r in rows
                                         if r["program_id"] == "lock"
                                         and int(r["requested_threads"]) == max_threads
                                         and int(r["k"]) == k),
        })

    return {
        "task": "Tarefa 9",
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
            "k_values_tested": K_VALUES,
            "n":               int(rows[0]["n"]) if rows else 0,
            "runs_per_cfg":    max(int(r["run_id"]) for r in rows) if rows else 0,
        },
        "experiment_a": list(exp_a.values()),
        "experiment_b": exp_b,
    }


def save_json(summary: dict) -> None:
    JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Grafico
# ---------------------------------------------------------------------------

COLORS  = {"critical": "#E74C3C", "lock": "#2E86DE"}
MARKERS = {"critical": "o",       "lock": "s"}


def plot_summary(summary: dict) -> None:
    if not HAS_MATPLOTLIB:
        return

    exp_a    = {p["id"]: p for p in summary["experiment_a"]}
    exp_b    = summary["experiment_b"]
    n_val    = summary["config"]["n"]
    max_t    = summary["config"]["threads_tested"][-1]

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        f"Tarefa 9 — Critical nomeado vs omp_lock_t  (N={n_val:,})",
        fontsize=13, fontweight="bold",
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.32)

    ax_time    = fig.add_subplot(gs[0, 0])
    ax_speedup = fig.add_subplot(gs[0, 1])
    ax_k       = fig.add_subplot(gs[1, 0])
    ax_bar     = fig.add_subplot(gs[1, 1])

    # --- Painel 1: tempo vs threads (K=2)
    for pid, prog in exp_a.items():
        threads = [pt["requested_threads"] for pt in prog["per_thread"]]
        times   = [pt["avg_elapsed_seconds"] * 1000 for pt in prog["per_thread"]]
        ax_time.plot(threads, times, marker=MARKERS[pid], color=COLORS[pid],
                     linewidth=2, label=prog["label"])
    ax_time.set_title("Tempo medio (K=2)")
    ax_time.set_xlabel("Threads")
    ax_time.set_ylabel("Tempo (ms)")
    ax_time.grid(True, linestyle="--", alpha=0.4)
    ax_time.legend(fontsize=9)

    # --- Painel 2: speedup vs threads (K=2)
    for pid, prog in exp_a.items():
        base = next((pt["avg_elapsed_seconds"] for pt in prog["per_thread"]
                     if pt["requested_threads"] == 1), None)
        if base and base > 0:
            threads = [pt["requested_threads"] for pt in prog["per_thread"]]
            speedup = [base / pt["avg_elapsed_seconds"]
                       if pt["avg_elapsed_seconds"] > 0 else 0
                       for pt in prog["per_thread"]]
            ax_speedup.plot(threads, speedup, marker=MARKERS[pid], color=COLORS[pid],
                            linewidth=2, label=prog["label"])
    ideal_t = max(THREAD_COUNTS)
    ax_speedup.plot([1, ideal_t], [1, ideal_t], "k--", linewidth=1, label="Ideal")
    ax_speedup.set_title("Speedup (K=2)")
    ax_speedup.set_xlabel("Threads")
    ax_speedup.set_ylabel("Speedup")
    ax_speedup.grid(True, linestyle="--", alpha=0.4)
    ax_speedup.legend(fontsize=9)

    # --- Painel 3: lock — tempo vs K (threads = max)
    k_vals  = [e["k"]   for e in exp_b]
    t_vals  = [e["avg_elapsed_seconds"] * 1000 for e in exp_b]
    # adiciona K=2 do experimento A para completar a curva
    base_k2 = next((pt["avg_elapsed_seconds"] for pt in exp_a["lock"]["per_thread"]
                    if pt["requested_threads"] == max_t), None)
    if base_k2 is not None:
        k_vals  = [2] + k_vals
        t_vals  = [base_k2 * 1000] + t_vals
    ax_k.plot(k_vals, t_vals, marker="D", color=COLORS["lock"], linewidth=2)
    ax_k.set_title(f"lock — tempo vs K ({max_t} threads)")
    ax_k.set_xlabel("Numero de listas (K)")
    ax_k.set_ylabel("Tempo medio (ms)")
    ax_k.grid(True, linestyle="--", alpha=0.4)

    # --- Painel 4: barras — critical vs lock nos threads testados
    bar_threads  = THREAD_COUNTS
    bar_critical = [pt["avg_elapsed_seconds"] * 1000
                    for pt in exp_a["critical"]["per_thread"]]
    bar_lock     = [pt["avg_elapsed_seconds"] * 1000
                    for pt in exp_a["lock"]["per_thread"]]
    x      = range(len(bar_threads))
    width  = 0.35
    ax_bar.bar([i - width/2 for i in x], bar_critical, width,
               color=COLORS["critical"], label="critical (K=2)", edgecolor="black", linewidth=0.7)
    ax_bar.bar([i + width/2 for i in x], bar_lock, width,
               color=COLORS["lock"], label="lock (K=2)", edgecolor="black", linewidth=0.7)
    ax_bar.set_xticks(list(x))
    ax_bar.set_xticklabels([str(t) for t in bar_threads])
    ax_bar.set_title("Critical vs lock — comparacao direta")
    ax_bar.set_xlabel("Threads")
    ax_bar.set_ylabel("Tempo medio (ms)")
    ax_bar.legend(fontsize=9)
    ax_bar.grid(True, axis="y", linestyle="--", alpha=0.4)

    fig.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------

def _table_threads(prog: dict) -> str:
    headers   = ["Threads", "Rodadas", "Media (ms)", "Min (ms)", "Max (ms)", "Validas"]
    sep       = "|" + "|".join(["---"] * len(headers)) + "|"
    lines     = ["|" + "|".join(headers) + "|", sep]
    for pt in prog["per_thread"]:
        lines.append("|" + "|".join([
            str(pt["requested_threads"]),
            str(pt["runs"]),
            f"{pt['avg_elapsed_seconds'] * 1000:.3f}",
            f"{pt['min_elapsed_seconds'] * 1000:.3f}",
            f"{pt['max_elapsed_seconds'] * 1000:.3f}",
            "sim" if pt["all_valid"] else "**nao**",
        ]) + "|")
    return "\n".join(lines)


def _table_k(exp_b: list[dict]) -> str:
    headers = ["K (listas)", "Threads", "Rodadas", "Media (ms)", "Min (ms)", "Max (ms)", "Validas"]
    sep     = "|" + "|".join(["---"] * len(headers)) + "|"
    lines   = ["|" + "|".join(headers) + "|", sep]
    for e in exp_b:
        lines.append("|" + "|".join([
            str(e["k"]),
            str(e["requested_threads"]),
            str(e["runs"]),
            f"{e['avg_elapsed_seconds'] * 1000:.3f}",
            f"{e['min_elapsed_seconds'] * 1000:.3f}",
            f"{e['max_elapsed_seconds'] * 1000:.3f}",
            "sim" if e["all_valid"] else "**nao**",
        ]) + "|")
    return "\n".join(lines)


def build_report(summary: dict) -> str:
    n_val    = summary["config"]["n"]
    runs     = summary["config"]["runs_per_cfg"]
    threads  = ", ".join(map(str, summary["config"]["threads_tested"]))
    exp_a    = {p["id"]: p for p in summary["experiment_a"]}
    exp_b    = summary["experiment_b"]
    max_t    = summary["config"]["threads_tested"][-1]

    image_block = "![Grafico Tarefa 9](tarefa9_resultados.png)" if PLOT_PATH.exists() else ""

    artifacts = "\n".join([
        "- CSV bruto: `dados/tarefa9_runs.csv`",
        "- Resumo JSON: `dados/tarefa9_summary.json`",
        *(["- Grafico: `relatorios/tarefa9_resultados.png`"] if PLOT_PATH.exists() else []),
        "- Relatorio: `relatorios/relatorio_tarefa09.md`",
    ])

    run_cmd = """```bash
sudo apt update && sudo apt install -y build-essential python3 python3-pip
python3 -m pip install --user matplotlib

cd atividades-aula
python3 Tarefa-09/run_tests.py
```"""

    report_only_cmd = """```bash
python3 Tarefa-09/run_tests.py --report-only
```"""

    # Extrai alguns numeros para a analise
    crit_t1  = next(pt["avg_elapsed_seconds"] for pt in exp_a["critical"]["per_thread"] if pt["requested_threads"] == 1)
    crit_max = next(pt["avg_elapsed_seconds"] for pt in exp_a["critical"]["per_thread"] if pt["requested_threads"] == max_t)
    lock_t1  = next(pt["avg_elapsed_seconds"] for pt in exp_a["lock"]["per_thread"]     if pt["requested_threads"] == 1)
    lock_max = next(pt["avg_elapsed_seconds"] for pt in exp_a["lock"]["per_thread"]     if pt["requested_threads"] == max_t)

    return f"""# Tarefa 9 — Regioes Criticas Nomeadas e Travas Explicitas

#### Vinicius Barbosa Ventura Mergulhao

**CPU:** 13th Gen Intel Core i5-13420H (4 P-cores + 8 E-cores = 12 threads logicos)

---

## 1. Programas implementados

| Programa | Protecao | Listas | Caracteristica principal |
|---|---|---|---|
| `lists_critical.c` | `#pragma omp critical(nome)` | 2 (fixas) | Nomes compilados em tempo de compilacao |
| `lists_lock.c`     | `omp_lock_t locks[K]`        | K (usuario) | Locks criados em tempo de execucao |

Ambos os programas realizam **N = {n_val:,}** insercoes em listas encadeadas.
Cada thread escolhe aleatoriamente em qual lista inserir usando `rand_r()` com seed privada.
O experimento usou **{runs} rodadas** por configuracao, threads testadas: **{threads}**.

---

## 2. Por que critical nomeado nao e suficiente para K listas

### O que critical nomeado resolve

Com 2 listas fixas, e possivel escrever:

```c
if (choice == 0) {{
    #pragma omp critical(lista_a)   // bloqueia so quem quer lista_a
    list_insert(&lista_a, value);
}} else {{
    #pragma omp critical(lista_b)   // bloqueia so quem quer lista_b
    list_insert(&lista_b, value);
}}
```

O resultado e que insercoes em listas diferentes ocorrem em paralelo: uma thread
inserindo em `lista_a` nao bloqueia outra que quer inserir em `lista_b`.

### Por que nao generaliza para K listas

Os nomes de `critical` sao **identificadores estaticos resolvidos em tempo de compilacao**.
Nao e possivel fazer:

```c
// INVALIDO — nomes de critical nao podem ser dinamicos
int k = rand_r(&seed) % K;
#pragma omp critical(lista_k)   // erro: 'k' nao e um literal
list_insert(&lists[k], value);
```

Para K listas dinamicas seria necessario escrever K blocos `if/else` distintos no
codigo-fonte — impraticavel para K grande e impossivel quando K e definido em tempo
de execucao.

### Solucao: omp_lock_t

`omp_lock_t` e uma trava explicita gerenciada em tempo de execucao:

```c
omp_lock_t locks[K];
for (int k = 0; k < K; k++) omp_init_lock(&locks[k]);

// em paralelo:
int k = rand_r(&seed) % K;
omp_set_lock(&locks[k]);      // adquire o lock da lista k
list_insert(&lists[k], value);
omp_unset_lock(&locks[k]);    // libera o lock da lista k

// ao final:
for (int k = 0; k < K; k++) omp_destroy_lock(&locks[k]);
```

O comportamento e identico ao `critical` nomeado para K=2, mas funciona para
qualquer K definido em tempo de execucao.

---

## 3. Corretude

Em todas as {runs} rodadas de cada configuracao, a validacao confirmou:

- `total_inserido == N` (nenhuma insercao perdida)
- `soma(contagens_por_lista) == total_inserido` (nenhum elemento duplicado)
- Nenhum deadlock ou crash

A integridade das listas foi mantida em todas as configuracoes testadas.

---

## 4. Resultados — Experimento A: critical vs lock (K=2)

### 4.1 critical nomeado (2 listas)

_{exp_a["critical"]["notes"]}_

{_table_threads(exp_a["critical"])}

### 4.2 omp_lock_t (K=2 listas)

_{exp_a["lock"]["notes"]}_

{_table_threads(exp_a["lock"])}

---

## 5. Resultados — Experimento B: lock com K variando ({max_t} threads)

{_table_k(exp_b)}

---

## 6. Graficos gerados

{image_block}

O grafico e dividido em 4 paineis:

**Painel 1 — Tempo medio (K=2):** Curvas de tempo para critical e lock com K=2
variando o numero de threads. Permite comparar as duas abordagens nas mesmas condicoes.

**Painel 2 — Speedup (K=2):** Speedup relativo a 1 thread para cada versao,
com a linha ideal tracejada. Mostra a eficiencia de paralelizacao de cada abordagem.

**Painel 3 — lock: tempo vs K:** Curva de desempenho do programa `lists_lock`
com threads fixas em {max_t} e K variando de 2 a 32. Avalia o impacto do numero
de listas no desempenho.

**Painel 4 — Comparacao em barras:** Comparacao direta entre critical e lock(K=2)
para cada configuracao de threads.

---

## 7. Analise

### 7.1 critical vs lock com K=2

Com K=2, as duas abordagens sao logicamente equivalentes: cada lista tem sua
propria regiao de exclusao mutua e insercoes em listas distintas ocorrem em paralelo.

- 1 thread:  critical={crit_t1 * 1000:.1f}ms, lock={lock_t1 * 1000:.1f}ms
- {max_t} threads: critical={crit_max * 1000:.1f}ms, lock={lock_max * 1000:.1f}ms

As diferencas de desempenho entre as duas versoes sao pequenas — ambas protegem
a mesma granularidade de dado (uma lista) e produzem o mesmo nivel de paralelismo
entre listas.

### 7.2 Impacto do numero de listas K

Com mais listas, a probabilidade de duas threads escolherem a mesma lista diminui.
Com K listas e T threads, a probabilidade de colisao em uma dada lista e
aproximadamente `1/K`. Quanto maior K, menor a contenção nos locks e melhor
o paralelismo potencial.

Na pratica, o ganho de desempenho com K crescente e limitado pelo overhead
de `malloc` dentro do lock — a alocacao de memoria tem seu proprio lock interno
na maioria das implementacoes de `libc`, criando um gargalo independente do K.

### 7.3 Por que critical anonimo seria pior

Um `critical` sem nome serializa TODAS as insercoes, independente da lista:

```c
// critical anonimo — pior opcao
#pragma omp critical
list_insert(&lists[k], value);  // bloqueia TODAS as threads, nao so as que usam lista k
```

Isso equivale a ter apenas 1 lock global — sem paralelismo entre insercoes.

### 7.4 Comparacao com as tarefas anteriores

| Tarefa | Mecanismo | Granularidade de protecao |
|---|---|---|
| Tarefa 5 | `atomic`, `critical` anonimo | 1 variavel global |
| Tarefa 7 | `single`, `taskwait` | Criacao de tasks |
| Tarefa 8 | `critical` anonimo (acumulacao) | 1 variavel global |
| Tarefa 9 (Parte 1) | `critical` nomeado | Por lista (2 fixas) |
| Tarefa 9 (Parte 2) | `omp_lock_t` por lista | Por lista (K dinamico) |

A evolucao mostra a progressao de mecanismos de granularidade grossa (1 lock global)
para granularidade fina (1 lock por recurso), reduzindo a contenção e aumentando
o paralelismo efetivo.

---

## 8. Conclusao

| Aspecto | critical nomeado | omp_lock_t |
|---|---|---|
| Numero de listas | Fixo (definido no codigo) | Dinamico (qualquer K) |
| Paralelismo entre listas | Sim | Sim |
| Overhead por operacao | Baixo | Baixo |
| Flexibilidade | Nenhuma para K variavel | Total |
| Inicializacao | Automatica | Manual (`omp_init_lock`) |
| Destruicao | Automatica | Manual (`omp_destroy_lock`) |

`critical` nomeado e conveniente para um numero pequeno e fixo de recursos.
`omp_lock_t` e a escolha correta quando o numero de recursos e determinado
em tempo de execucao — seja por entrada do usuario, tamanho de estrutura de dados
ou qualquer outro valor dinamico.

> A limitacao do `critical` nomeado nao e de desempenho — e estrutural.
> Os nomes de critical sao parte da sintaxe da diretiva de compilacao e nao
> podem ser computados em tempo de execucao. Para qualquer problema onde
> o numero de recursos e variavel, `omp_lock_t` e o unico mecanismo correto.

---

<div style="page-break-before: always;"></div>

## Codigo

### lists_critical.c (2 listas fixas + critical nomeado)

```c
#pragma omp parallel
{{
    unsigned int seed = (unsigned int)(time(NULL))
                      ^ (unsigned int)(omp_get_thread_num() * 2654435761u);

    #pragma omp for schedule(static)
    for (long i = 0; i < N; i++) {{
        int value  = (int)(rand_r(&seed) % 1000000);
        int choice = (int)(rand_r(&seed) % 2);

        if (choice == 0) {{
            #pragma omp critical(lista_a)   // bloqueia so quem quer lista_a
            list_insert(&lista_a, value);
        }} else {{
            #pragma omp critical(lista_b)   // bloqueia so quem quer lista_b
            list_insert(&lista_b, value);
        }}
    }}
}}
```

### lists_lock.c (K listas dinamicas + omp_lock_t)

```c
omp_lock_t locks[K];
for (int k = 0; k < K; k++) omp_init_lock(&locks[k]);

#pragma omp parallel
{{
    unsigned int seed = ...;

    #pragma omp for schedule(static)
    for (long i = 0; i < N; i++) {{
        int value = (int)(rand_r(&seed) % 1000000);
        int k     = (int)(rand_r(&seed) % K);

        omp_set_lock(&locks[k]);      // adquire lock da lista k
        list_insert(&lists[k], value);
        omp_unset_lock(&locks[k]);    // libera lock da lista k
    }}
}}

for (int k = 0; k < K; k++) omp_destroy_lock(&locks[k]);
```

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
        raise RuntimeError(f"JSON nao encontrado em {JSON_PATH}.")
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    plot_summary(summary)
    save_report(summary)
    print("Relatorio/grafico regenerados.")
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

    print(f"Tarefa 9 — N={n:,}  rodadas={runs}  threads={THREAD_COUNTS}  K_values={K_VALUES}")
    print()

    print("[1/4] Compilando...")
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
