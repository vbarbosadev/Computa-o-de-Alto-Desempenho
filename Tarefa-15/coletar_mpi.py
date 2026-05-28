import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
OUT_DIR = ROOT / "resultados"
CSV_FILE = OUT_DIR / "tarefa15_resultados.csv"

PROGRAMS = {
    "send_recv": ROOT / "heat_send_recv.c",
    "isend_irecv_wait": ROOT / "heat_isend_irecv_wait.c",
    "isend_irecv_test": ROOT / "heat_isend_irecv_test.c",
}

RESULT_RE = re.compile(
    r"RESULT versao=(\S+) rank=(\d+) processos=(\d+) n=(\d+) local_n=(\d+) "
    r"passos=(\d+) tempo=([0-9.eE+-]+) soma=([0-9.eE+-]+)"
)


def run(cmd):
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        raise SystemExit(completed.returncode)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.stdout


def require_tool(tool):
    resolved = shutil.which(tool)
    if resolved is None:
        raise SystemExit(
            f"Ferramenta nao encontrada: {tool}. Carregue um modulo MPI "
            "ou informe o caminho com --mpicc/--mpirun."
        )
    return resolved


def compile_programs(mpicc):
    BUILD_DIR.mkdir(exist_ok=True)
    executables = {}
    for version, source in PROGRAMS.items():
        exe = BUILD_DIR / version
        cmd = [mpicc, "-O3", "-Wall", "-Wextra", str(source), "-lm", "-o", str(exe)]
        print("Compilando:", " ".join(cmd))
        run(cmd)
        executables[version] = exe
    return executables


def parse_output(output, expected_processes):
    rows = []
    for match in RESULT_RE.finditer(output):
        rows.append({
            "version": match.group(1),
            "rank": int(match.group(2)),
            "processes": int(match.group(3)),
            "n": int(match.group(4)),
            "local_n": int(match.group(5)),
            "steps": int(match.group(6)),
            "rank_time": float(match.group(7)),
            "local_sum": float(match.group(8)),
        })
    if len(rows) != expected_processes:
        raise ValueError(f"Saida inesperada ({len(rows)} RESULTs):\n{output}")
    return rows


def execute(mpirun, exe, processes, n, steps, launcher_args):
    cmd = [
        mpirun,
        *launcher_args,
        "-np",
        str(processes),
        str(exe),
        "--n",
        str(n),
        "--passos",
        str(steps),
    ]
    return parse_output(run(cmd), processes)


def write_csv(rows):
    OUT_DIR.mkdir(exist_ok=True)
    fields = [
        "rep",
        "version",
        "processes",
        "n",
        "steps",
        "elapsed_max",
        "elapsed_mean",
        "sum_total",
        "rank",
        "local_n",
        "rank_time",
        "local_sum",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV salvo em: {CSV_FILE}")


def best_by_group(rows):
    best = {}
    for row in rows:
        key = (row["version"], row["processes"], row["n"], row["steps"])
        if key not in best or row["elapsed_max"] < best[key]["elapsed_max"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["n"], row["processes"], row["version"]))


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    best = best_by_group(rows)
    versions = sorted({row["version"] for row in rows})
    ns = sorted({row["n"] for row in rows})

    for n in ns:
        plt.figure(figsize=(8, 5))
        for version in versions:
            data = [
                row for row in best
                if row["version"] == version and row["n"] == n
            ]
            plt.plot(
                [row["processes"] for row in data],
                [row["elapsed_max"] for row in data],
                marker="o",
                label=version,
            )
        plt.xlabel("Processos MPI")
        plt.ylabel("Tempo maximo entre ranks (s)")
        plt.title(f"Difusao de calor 1D - n={n}")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"tempo_n{n}.png", dpi=160)

    plt.figure(figsize=(8, 5))
    largest_n = max(ns)
    for version in versions:
        data = [
            row for row in best
            if row["version"] == version and row["n"] == largest_n
        ]
        base = next(row["elapsed_max"] for row in data if row["processes"] == min(r["processes"] for r in data))
        plt.plot(
            [row["processes"] for row in data],
            [base / row["elapsed_max"] for row in data],
            marker="o",
            label=version,
        )
    plt.xlabel("Processos MPI")
    plt.ylabel("Speedup relativo ao menor numero de processos")
    plt.title(f"Speedup relativo - n={largest_n}")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "speedup_relativo.png", dpi=160)
    print(f"Graficos salvos em: {OUT_DIR}")


def collect(args):
    mpicc = require_tool(args.mpicc)
    mpirun = require_tool(args.mpirun)
    executables = compile_programs(mpicc)
    rows = []

    for version, exe in executables.items():
        print(f"\nExecutando {version}")
        for processes in args.processes:
            for n in args.sizes:
                for rep in range(1, args.repeats + 1):
                    rank_rows = execute(mpirun, exe, processes, n, args.steps, args.launcher_arg)
                    elapsed_max = max(row["rank_time"] for row in rank_rows)
                    elapsed_mean = sum(row["rank_time"] for row in rank_rows) / len(rank_rows)
                    sum_total = sum(row["local_sum"] for row in rank_rows)
                    for row in rank_rows:
                        row["rep"] = rep
                        row["elapsed_max"] = elapsed_max
                        row["elapsed_mean"] = elapsed_mean
                        row["sum_total"] = sum_total
                        rows.append(row)
                    print(
                        f"{version} np={processes} n={n} rep={rep} "
                        f"tempo_max={elapsed_max:.6f}s soma={sum_total:.6f}"
                    )

    write_csv(rows)
    make_plots(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mpicc", default=os.environ.get("MPICC", "mpicc"))
    parser.add_argument("--mpirun", default=os.environ.get("MPIRUN", "mpirun"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100000, 1000000])
    parser.add_argument("--processes", nargs="+", type=int, default=[2, 4])
    parser.add_argument(
        "--launcher-arg",
        action="append",
        default=[],
        help="Argumento extra repassado ao mpirun. Pode ser usado varias vezes.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    collect(args)


if __name__ == "__main__":
    main()
