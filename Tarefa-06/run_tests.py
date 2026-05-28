#!/usr/bin/env python3
"""
Tarefa 6 - Estimativa estocastica de PI com OpenMP

Compila e executa 4 versoes do calculo de PI por Monte Carlo:
  1. pi_sequencial.c     -> baseline sequencial
  2. pi_parallel_for.c   -> com #pragma omp parallel for (race condition)
  3. pi_critical.c       -> corrigido com #pragma omp critical
  4. pi_clauses.c        -> reestruturado com clausulas private/firstprivate/
                            lastprivate/shared/default(none)

Coleta resultados, gera CSV, JSON, grafico e relatorio Markdown.
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
from collections import defaultdict
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

REAL_PI = 3.14159265358979323846

ROOT_DIR = Path(__file__).resolve().parent.parent
TASK_DIR = Path(__file__).resolve().parent
BUILD_DIR = TASK_DIR / "build"
DATA_DIR = ROOT_DIR / "dados"
REPORT_DIR = ROOT_DIR / "relatorios"

CSV_PATH = DATA_DIR / "tarefa6_runs.csv"
JSON_PATH = DATA_DIR / "tarefa6_summary.json"
PLOT_PATH = REPORT_DIR / "tarefa6_resultados.png"
REPORT_PATH = REPORT_DIR / "relatorio_tarefa06.md"

DEFAULT_N = 10000000
DEFAULT_RUNS = 10

CONFIG_RE = re.compile(r"^CONFIG program=(\S+) n=(\d+) threads=(\d+)$")
RESULT_RE = re.compile(
    r"^RESULT pi=([0-9.]+) count=(\d+) total=(\d+) "
    r"error=([0-9.]+) elapsed=([0-9.]+)"
    r"(?: last_i=(-?\d+))?$"
)

PROGRAMS = [
    {
        "id": "sequencial",
        "label": "Sequencial",
        "source": TASK_DIR / "pi_sequencial.c",
        "binary": BUILD_DIR / "pi_sequencial",
        "args_fn": lambda N, _test: [str(N)],
        "uses_openmp": False,
        "tests": [None],
        "notes": "Versao sequencial de referencia.",
    },
    {
        "id": "parallel_for",
        "label": "parallel for (race condition)",
        "source": TASK_DIR / "pi_parallel_for.c",
        "binary": BUILD_DIR / "pi_parallel_for",
        "args_fn": lambda N, _test: [str(N)],
        "uses_openmp": True,
        "tests": [None],
        "notes": "Usa #pragma omp parallel for sem protecao — condicao de corrida.",
    },
    {
        "id": "critical",
        "label": "critical (corrigido)",
        "source": TASK_DIR / "pi_critical.c",
        "binary": BUILD_DIR / "pi_critical",
        "args_fn": lambda N, _test: [str(N)],
        "uses_openmp": True,
        "tests": [None],
        "notes": "Corrige a race condition com #pragma omp critical.",
    },
    {
        "id": "shared_private",
        "label": "shared + private",
        "source": TASK_DIR / "pi_clauses.c",
        "binary": BUILD_DIR / "pi_clauses",
        "args_fn": lambda N, _test: ["1", str(N)],
        "uses_openmp": True,
        "tests": [1],
        "notes": "Clausulas shared e private com default(none).",
    },
    {
        "id": "firstprivate",
        "label": "firstprivate",
        "source": TASK_DIR / "pi_clauses.c",
        "binary": BUILD_DIR / "pi_clauses",
        "args_fn": lambda N, _test: ["2", str(N)],
        "uses_openmp": True,
        "tests": [2],
        "notes": "Clausula firstprivate: copia inicializada do valor pre-paralelo.",
    },
    {
        "id": "lastprivate",
        "label": "lastprivate",
        "source": TASK_DIR / "pi_clauses.c",
        "binary": BUILD_DIR / "pi_clauses",
        "args_fn": lambda N, _test: ["3", str(N)],
        "uses_openmp": True,
        "tests": [3],
        "notes": "Clausula lastprivate: variavel assume valor da ultima iteracao.",
    },
    {
        "id": "default_none",
        "label": "default(none)",
        "source": TASK_DIR / "pi_clauses.c",
        "binary": BUILD_DIR / "pi_clauses",
        "args_fn": lambda N, _test: ["4", str(N)],
        "uses_openmp": True,
        "tests": [4],
        "notes": "Clausula default(none): escopo explicito obrigatorio.",
    },
]


def detect_thread_counts() -> list[int]:
    max_threads = max(1, os.cpu_count() or 1)
    counts = [1]
    for c in (2, 4, 8):
        if c <= max_threads:
            counts.append(c)
    if max_threads not in counts:
        counts.append(max_threads)
    return counts


THREAD_COUNTS = detect_thread_counts()


def ensure_dirs() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def compile_program(source: Path, binary: Path, uses_openmp: bool) -> None:
    gcc = shutil.which("gcc")
    if not gcc:
        raise RuntimeError("gcc nao encontrado no PATH.")

    cmd = [gcc, "-O2", str(source), "-o", str(binary), "-lm"]
    if uses_openmp:
        cmd.insert(2, "-fopenmp")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Falha ao compilar {source.name}:\n{result.stderr.strip()}")


def compile_all() -> None:
    ensure_dirs()
    compiled = set()
    for prog in PROGRAMS:
        key = str(prog["source"])
        if key not in compiled:
            print(f"  Compilando {prog['source'].name}...")
            compile_program(prog["source"], prog["binary"], prog["uses_openmp"])
            compiled.add(key)


def build_env(threads: int) -> dict[str, str]:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"] = "FALSE"
    return env


def parse_output(output: str) -> dict[str, object]:
    config = None
    result = None

    for line in output.splitlines():
        line = line.strip()
        m = CONFIG_RE.match(line)
        if m:
            config = {
                "program": m.group(1),
                "n": int(m.group(2)),
                "threads": int(m.group(3)),
            }
            continue
        m = RESULT_RE.match(line)
        if m:
            result = {
                "pi": float(m.group(1)),
                "count": int(m.group(2)),
                "total": int(m.group(3)),
                "error": float(m.group(4)),
                "elapsed": float(m.group(5)),
                "last_i": int(m.group(6)) if m.group(6) else None,
            }

    if config is None or result is None:
        raise RuntimeError(f"Saida invalida do programa:\n{output}")

    return {"config": config, "result": result}


def run_once(prog: dict, threads: int, N: int) -> dict[str, object]:
    args = prog["args_fn"](N, prog["tests"][0])
    cmd = [str(prog["binary"])] + args

    proc = subprocess.run(cmd, capture_output=True, text=True, env=build_env(threads))
    if proc.returncode != 0:
        raise RuntimeError(
            f"Falha ao executar {prog['id']} com {threads} threads:\n{proc.stderr.strip()}"
        )

    return parse_output(proc.stdout)


def collect_runs(N: int, runs: int) -> list[dict[str, object]]:
    rows = []
    total = len(PROGRAMS) * len(THREAD_COUNTS) * runs
    count = 0

    for prog in PROGRAMS:
        thread_list = [1] if not prog["uses_openmp"] else THREAD_COUNTS
        for threads in thread_list:
            for run_id in range(1, runs + 1):
                count += 1
                parsed = run_once(prog, threads, N)
                r = parsed["result"]
                pi_error_pct = abs(r["pi"] - REAL_PI) / REAL_PI * 100.0
                is_accurate = r["error"] < 0.01

                row = {
                    "program_id": prog["id"],
                    "program_label": prog["label"],
                    "requested_threads": threads,
                    "actual_threads": parsed["config"]["threads"],
                    "run_id": run_id,
                    "n": N,
                    "pi": f"{r['pi']:.10f}",
                    "count": r["count"],
                    "error": f"{r['error']:.10f}",
                    "error_pct": f"{pi_error_pct:.6f}",
                    "elapsed": f"{r['elapsed']:.6f}",
                    "is_accurate": int(is_accurate),
                    "last_i": r["last_i"] if r["last_i"] is not None else "",
                }
                rows.append(row)

                if count % 10 == 0 or count == total:
                    print(f"  Progresso: {count}/{total} execucoes")

    return rows


def save_csv(rows: list[dict]) -> None:
    if not rows:
        return
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarise(rows: list[dict], N: int, runs: int) -> dict:
    programs_summary = []

    for prog in PROGRAMS:
        prog_rows = [r for r in rows if r["program_id"] == prog["id"]]
        per_thread = []
        thread_list = [1] if not prog["uses_openmp"] else THREAD_COUNTS

        for threads in thread_list:
            group = [r for r in prog_rows if int(r["requested_threads"]) == threads]
            if not group:
                continue

            pi_values = [float(r["pi"]) for r in group]
            errors = [float(r["error"]) for r in group]
            elapsed_values = [float(r["elapsed"]) for r in group]
            accurate_count = sum(int(r["is_accurate"]) for r in group)

            per_thread.append({
                "requested_threads": threads,
                "runs": len(group),
                "accurate_runs": accurate_count,
                "avg_pi": round(statistics.mean(pi_values), 10),
                "stddev_pi": round(statistics.stdev(pi_values), 10) if len(pi_values) > 1 else 0.0,
                "avg_error": round(statistics.mean(errors), 10),
                "max_error": round(max(errors), 10),
                "min_error": round(min(errors), 10),
                "avg_elapsed": round(statistics.mean(elapsed_values), 6),
                "min_elapsed": round(min(elapsed_values), 6),
                "max_elapsed": round(max(elapsed_values), 6),
            })

        all_accurate = all(t["accurate_runs"] == t["runs"] for t in per_thread)
        programs_summary.append({
            "id": prog["id"],
            "label": prog["label"],
            "source": prog["source"].name,
            "notes": prog["notes"],
            "all_accurate": all_accurate,
            "per_thread": per_thread,
        })

    return {
        "task": "Tarefa 6",
        "platform": {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "python": sys.version.split()[0],
        },
        "config": {
            "n": N,
            "runs_per_config": runs,
            "threads_tested": THREAD_COUNTS,
        },
        "programs": programs_summary,
    }


def save_json(summary: dict) -> None:
    JSON_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def plot_summary(summary: dict) -> None:
    if not HAS_MATPLOTLIB:
        return

    programs = summary["programs"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Tarefa 6 - Estimativa de PI por Monte Carlo com OpenMP",
        fontsize=13, fontweight="bold",
    )

    colors = {
        "sequencial": "#2E86DE",
        "parallel_for": "#E74C3C",
        "critical": "#27AE60",
        "shared_private": "#8E44AD",
        "firstprivate": "#F39C12",
        "lastprivate": "#1ABC9C",
        "default_none": "#E67E22",
    }
    markers = {
        "sequencial": "o",
        "parallel_for": "X",
        "critical": "s",
        "shared_private": "D",
        "firstprivate": "^",
        "lastprivate": "v",
        "default_none": "P",
    }

    # --- Grafico 1: PI medio por threads ---
    ax = axes[0, 0]
    for prog in programs:
        threads = [t["requested_threads"] for t in prog["per_thread"]]
        avg_pi = [t["avg_pi"] for t in prog["per_thread"]]
        ax.plot(threads, avg_pi,
                marker=markers.get(prog["id"], "o"),
                color=colors.get(prog["id"], "gray"),
                linewidth=2, label=prog["label"])
    ax.axhline(y=REAL_PI, color="gray", linestyle="--", linewidth=1.5, label="PI real")
    ax.set_title("PI medio estimado")
    ax.set_xlabel("Threads")
    ax.set_ylabel("PI")
    ax.legend(fontsize=7, loc="lower left")
    ax.grid(True, linestyle="--", alpha=0.4)

    # --- Grafico 2: Erro medio ---
    ax = axes[0, 1]
    for prog in programs:
        threads = [t["requested_threads"] for t in prog["per_thread"]]
        avg_err = [t["avg_error"] for t in prog["per_thread"]]
        ax.plot(threads, avg_err,
                marker=markers.get(prog["id"], "o"),
                color=colors.get(prog["id"], "gray"),
                linewidth=2, label=prog["label"])
    ax.set_title("Erro absoluto medio |PI_est - PI|")
    ax.set_xlabel("Threads")
    ax.set_ylabel("Erro")
    ax.set_yscale("log")
    ax.legend(fontsize=7)
    ax.grid(True, linestyle="--", alpha=0.4)

    # --- Grafico 3: Desvio padrao do PI ---
    ax = axes[1, 0]
    for prog in programs:
        threads = [t["requested_threads"] for t in prog["per_thread"]]
        stddev = [t["stddev_pi"] for t in prog["per_thread"]]
        if any(s > 0 for s in stddev):
            ax.plot(threads, stddev,
                    marker=markers.get(prog["id"], "o"),
                    color=colors.get(prog["id"], "gray"),
                    linewidth=2, label=prog["label"])
    ax.set_title("Desvio padrao do PI entre rodadas")
    ax.set_xlabel("Threads")
    ax.set_ylabel("Desvio padrao")
    ax.set_yscale("log")
    ax.legend(fontsize=7)
    ax.grid(True, linestyle="--", alpha=0.4)

    # --- Grafico 4: Tempo medio ---
    ax = axes[1, 1]
    for prog in programs:
        threads = [t["requested_threads"] for t in prog["per_thread"]]
        avg_ms = [t["avg_elapsed"] * 1000.0 for t in prog["per_thread"]]
        ax.plot(threads, avg_ms,
                marker=markers.get(prog["id"], "o"),
                color=colors.get(prog["id"], "gray"),
                linewidth=2, label=prog["label"])
    ax.set_title("Tempo medio de execucao")
    ax.set_xlabel("Threads")
    ax.set_ylabel("Tempo (ms)")
    ax.legend(fontsize=7)
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)


def format_table(prog: dict) -> str:
    headers = ["Threads", "Rodadas", "Precisas", "PI medio", "Desvio padrao",
               "Erro medio", "Tempo medio (ms)"]
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = ["|" + "|".join(headers) + "|", sep]

    for t in prog["per_thread"]:
        lines.append("|" + "|".join([
            str(t["requested_threads"]),
            str(t["runs"]),
            str(t["accurate_runs"]),
            f"{t['avg_pi']:.8f}",
            f"{t['stddev_pi']:.8f}",
            f"{t['avg_error']:.8f}",
            f"{t['avg_elapsed'] * 1000:.3f}",
        ]) + "|")

    return "\n".join(lines)


def build_report(summary: dict) -> str:
    N = summary["config"]["n"]
    runs = summary["config"]["runs_per_config"]
    threads_text = ", ".join(map(str, summary["config"]["threads_tested"]))

    prog_map = {p["id"]: p for p in summary["programs"]}

    image_block = f"![Resultados](tarefa6_resultados.png)" if PLOT_PATH.exists() else ""

    sections = []
    for prog in summary["programs"]:
        sections.append(f"### {prog['label']}\n\n{prog['notes']}\n\n{format_table(prog)}")

    return f"""# Tarefa 6 - Calculo de PI paralelo com OpenMP

## Objetivo

Implementar a estimativa estocastica de PI pelo metodo de Monte Carlo, paralelizar
com `#pragma omp parallel for`, identificar e explicar a condicao de corrida,
corrigi-la com `#pragma omp critical`, e testar as clausulas `private`, `firstprivate`,
`lastprivate`, `shared` e `default(none)`.

## Como executar

```bash
# Instalacao de dependencias (Ubuntu)
sudo apt update
sudo apt install -y build-essential python3 python3-pip
python3 -m pip install --user matplotlib

# Executar coleta completa
cd atividades-aula
bash Tarefa-06/run_tests.sh

# Ou diretamente
python3 Tarefa-06/run_tests.py [N] [rodadas]

# Apenas regenerar grafico/relatorio a partir do JSON salvo
python3 Tarefa-06/run_tests.py --report-only
```

## Configuracao dos testes

- **N (pontos Monte Carlo):** {N:,}
- **Rodadas por configuracao:** {runs}
- **Threads testadas:** {threads_text}

## Programas testados

| Arquivo | Descricao |
|---|---|
| `pi_sequencial.c` | Versao sequencial de referencia |
| `pi_parallel_for.c` | `#pragma omp parallel for` sem protecao (race condition) |
| `pi_critical.c` | Correcao com `#pragma omp critical` |
| `pi_clauses.c` | Testes com clausulas `private`, `firstprivate`, `lastprivate`, `default(none)` |

## Resultados

{chr(10).join(sections)}

{image_block}

## Analise da condicao de corrida

A versao `pi_parallel_for.c` apresenta **resultado incorreto** porque:

1. **Race condition em `count++`:** a variavel `count` e compartilhada entre todas as threads.
   Quando multiplas threads leem, incrementam e escrevem `count` simultaneamente, algumas
   atualizacoes sao perdidas (lost updates). O resultado e um `count` menor que o real,
   levando a um PI subestimado.

2. **`rand()` nao e thread-safe:** a funcao `rand()` usa estado global interno. Multiplas
   threads acessando esse estado geram numeros repetidos ou correlacionados, comprometendo
   a aleatoriedade da amostragem.

## Correcao com `critical`

A versao `pi_critical.c` resolve ambos os problemas:
- Usa `rand_r(&seed)` com seed privada por thread (thread-safe).
- Protege `count++` com `#pragma omp critical`, garantindo acesso exclusivo.

Limitacao: o `critical` serializa o incremento, reduzindo o paralelismo efetivo.

## Explicacao das clausulas

### `shared(var)`
A variavel e **compartilhada** entre todas as threads. Todas leem e escrevem na mesma
posicao de memoria. Requer protecao (critical/atomic) para escritas concorrentes.

### `private(var)`
Cada thread recebe uma **copia propria** da variavel, **nao inicializada**. O valor
original nao e copiado — a variavel comeca com lixo. E necessario inicializar
manualmente dentro do bloco paralelo.

### `firstprivate(var)`
Como `private`, mas a copia e **inicializada com o valor** que a variavel tinha antes
da regiao paralela. Elimina a necessidade de inicializacao manual.

### `lastprivate(var)`
Apos o termino do loop paralelo, a variavel assume o **valor da ultima iteracao**
(na ordem sequencial). Util quando o resultado final do loop precisa ser preservado.

### `default(none)`
Obriga o programador a declarar **explicitamente** o escopo de toda variavel usada
na regiao paralela. Se alguma variavel for esquecida, o compilador emite erro.
Isso previne race conditions acidentais e torna o codigo mais seguro em programas
complexos.

## Artefatos gerados

- CSV bruto: `dados/tarefa6_runs.csv`
- Resumo estruturado: `dados/tarefa6_summary.json`
{("- Grafico: `relatorios/tarefa6_resultados.png`" + chr(10)) if PLOT_PATH.exists() else ""}- Relatorio: `relatorios/relatorio_tarefa06.md`
"""


def save_report(summary: dict) -> None:
    REPORT_PATH.write_text(build_report(summary), encoding="utf-8", newline="\n")


def report_only() -> int:
    if not JSON_PATH.exists():
        raise RuntimeError(
            f"Resumo nao encontrado em {JSON_PATH}. Execute a coleta antes."
        )
    summary = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    plot_summary(summary)
    save_report(summary)
    print("Relatorio regenerado com sucesso.")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico:   {PLOT_PATH}")
    print(f"  Relatorio: {REPORT_PATH}")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--report-only":
        return report_only()

    N = DEFAULT_N
    runs = DEFAULT_RUNS

    if len(sys.argv) > 1:
        N = int(sys.argv[1])
    if len(sys.argv) > 2:
        runs = int(sys.argv[2])

    print(f"Tarefa 6 - Calculo de PI por Monte Carlo com OpenMP")
    print(f"  N = {N:,} | Rodadas = {runs} | Threads = {THREAD_COUNTS}")
    print()

    print("Compilando programas...")
    compile_all()
    print()

    print("Executando testes...")
    rows = collect_runs(N, runs)
    print()

    save_csv(rows)
    summary = summarise(rows, N, runs)
    save_json(summary)
    plot_summary(summary)
    save_report(summary)

    print("Coleta da Tarefa 6 concluida com sucesso.")
    print(f"  CSV:       {CSV_PATH}")
    print(f"  JSON:      {JSON_PATH}")
    if HAS_MATPLOTLIB and PLOT_PATH.exists():
        print(f"  Grafico:   {PLOT_PATH}")
    elif not HAS_MATPLOTLIB:
        print("  Grafico:   nao gerado (matplotlib indisponivel).")
    print(f"  Relatorio: {REPORT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
