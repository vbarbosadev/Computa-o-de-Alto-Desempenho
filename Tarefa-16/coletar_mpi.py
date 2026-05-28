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
CSV_FILE = OUT_DIR / "tarefa16_resultados.csv"

SEQ_SRC = ROOT / "primos_seq.c"
MPI_SRC = ROOT / "leader_worker_primes.c"
SEQ_EXE = BUILD_DIR / "primos_seq"
MPI_EXE = BUILD_DIR / "leader_worker_primes"

SEQ_RE = re.compile(r"RESULT versao=seq max=(\d+) primos=(\d+) tempo=([0-9.eE+-]+)")
MPI_RE = re.compile(
    r"RESULT versao=leader_worker processos=(\d+) trabalhadores=(\d+) max=(\d+) "
    r"tarefas=(\d+) primos=(\d+) tempo=([0-9.eE+-]+)(.*)"
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
        raise SystemExit(f"Ferramenta nao encontrada: {tool}")
    return resolved


def compile_programs(cc, mpicc):
    BUILD_DIR.mkdir(exist_ok=True)
    run([cc, "-O3", "-Wall", "-Wextra", str(SEQ_SRC), "-lm", "-o", str(SEQ_EXE)])
    run([mpicc, "-O3", "-Wall", "-Wextra", str(MPI_SRC), "-lm", "-o", str(MPI_EXE)])


def parse_seq(output):
    match = SEQ_RE.search(output)
    if match is None:
        raise ValueError("Saida sequencial inesperada:\n" + output)
    return {
        "primes": int(match.group(2)),
        "elapsed": float(match.group(3)),
    }


def parse_workers(extra):
    workers = {}
    for item in extra.strip().split():
        if item.startswith("w") and "=" in item:
            key, value = item.split("=", 1)
            workers[key] = int(value)
    return workers


def parse_mpi(output):
    match = MPI_RE.search(output)
    if match is None:
        raise ValueError("Saida MPI inesperada:\n" + output)
    return {
        "processes": int(match.group(1)),
        "workers": int(match.group(2)),
        "max": int(match.group(3)),
        "tasks": int(match.group(4)),
        "primes": int(match.group(5)),
        "elapsed": float(match.group(6)),
        "worker_tasks": parse_workers(match.group(7)),
    }


def execute_seq(maximum):
    return parse_seq(run([str(SEQ_EXE), "--max", str(maximum)]))


def execute_mpi(mpirun, processes, maximum, tasks, launcher_args):
    cmd = [
        mpirun,
        *launcher_args,
        "-np",
        str(processes),
        str(MPI_EXE),
        "--max",
        str(maximum),
        "--tarefas",
        str(tasks),
    ]
    return parse_mpi(run(cmd))


def worker_task_string(worker_tasks):
    return " ".join(f"{key}:{worker_tasks[key]}" for key in sorted(worker_tasks))


def write_csv(rows):
    OUT_DIR.mkdir(exist_ok=True)
    fields = [
        "rep",
        "max",
        "tasks",
        "processes",
        "workers",
        "primes",
        "seq_time",
        "elapsed",
        "speedup",
        "efficiency",
        "worker_tasks",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV salvo em: {CSV_FILE}")


def best_by_group(rows):
    best = {}
    for row in rows:
        key = (row["max"], row["tasks"], row["processes"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["max"], row["tasks"], row["processes"]))


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    best = best_by_group(rows)
    max_values = sorted({row["max"] for row in rows})
    task_values = sorted({row["tasks"] for row in rows})

    for maximum in max_values:
        plt.figure(figsize=(8, 5))
        for tasks in task_values:
            data = [
                row for row in best
                if row["max"] == maximum and row["tasks"] == tasks
            ]
            plt.plot(
                [row["workers"] for row in data],
                [row["speedup"] for row in data],
                marker="o",
                label=f"{tasks} tarefas",
            )
        plt.xlabel("Trabalhadores")
        plt.ylabel("Speedup")
        plt.title(f"Speedup do escalonador - max={maximum}")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"speedup_max{maximum}.png", dpi=160)

    largest = max(max_values)
    plt.figure(figsize=(8, 5))
    for tasks in task_values:
        data = [
            row for row in best
            if row["max"] == largest and row["tasks"] == tasks
        ]
        plt.plot(
            [row["workers"] for row in data],
            [row["efficiency"] for row in data],
            marker="o",
            label=f"{tasks} tarefas",
        )
    plt.xlabel("Trabalhadores")
    plt.ylabel("Eficiencia")
    plt.title(f"Eficiencia do escalonador - max={largest}")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "eficiencia.png", dpi=160)
    print(f"Graficos salvos em: {OUT_DIR}")


def collect(args):
    cc = require_tool(args.cc)
    mpicc = require_tool(args.mpicc)
    mpirun = require_tool(args.mpirun)
    compile_programs(cc, mpicc)

    seq_by_max = {}
    for maximum in args.maximums:
        seq = execute_seq(maximum)
        seq_by_max[maximum] = seq
        print(f"seq max={maximum} tempo={seq['elapsed']:.6f}s primos={seq['primes']}")

    rows = []
    for maximum in args.maximums:
        for tasks in args.tasks:
            for processes in args.processes:
                for rep in range(1, args.repeats + 1):
                    result = execute_mpi(mpirun, processes, maximum, tasks, args.launcher_arg)
                    if result["primes"] != seq_by_max[maximum]["primes"]:
                        raise ValueError(
                            f"Resultado incorreto: MPI={result['primes']} "
                            f"SEQ={seq_by_max[maximum]['primes']}"
                        )
                    speedup = seq_by_max[maximum]["elapsed"] / result["elapsed"]
                    efficiency = speedup / result["workers"]
                    row = {
                        "rep": rep,
                        "max": maximum,
                        "tasks": tasks,
                        "processes": result["processes"],
                        "workers": result["workers"],
                        "primes": result["primes"],
                        "seq_time": seq_by_max[maximum]["elapsed"],
                        "elapsed": result["elapsed"],
                        "speedup": speedup,
                        "efficiency": efficiency,
                        "worker_tasks": worker_task_string(result["worker_tasks"]),
                    }
                    rows.append(row)
                    print(
                        f"mpi max={maximum} tarefas={tasks} processos={processes} rep={rep} "
                        f"tempo={result['elapsed']:.6f}s speedup={speedup:.2f}"
                    )

    write_csv(rows)
    make_plots(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", default=os.environ.get("CC", "gcc"))
    parser.add_argument("--mpicc", default=os.environ.get("MPICC", "mpicc"))
    parser.add_argument("--mpirun", default=os.environ.get("MPIRUN", "mpirun"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--maximums", nargs="+", type=int, default=[300000, 1000000])
    parser.add_argument("--tasks", nargs="+", type=int, default=[8, 32, 128])
    parser.add_argument("--processes", nargs="+", type=int, default=[2, 4])
    parser.add_argument("--launcher-arg", action="append", default=[])
    return parser.parse_args()


def main():
    args = parse_args()
    collect(args)


if __name__ == "__main__":
    main()
