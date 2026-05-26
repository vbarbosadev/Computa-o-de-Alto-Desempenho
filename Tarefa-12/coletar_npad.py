import argparse
import csv
import math
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "navier_scaling.c"
EXE = ROOT / "navier_scaling"
OUT_DIR = ROOT / "resultados"
CSV_FILE = OUT_DIR / "tarefa12_resultados.csv"


def run(cmd, env=None):
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout


def compile_program(cc):
    cmd = [cc, "-O3", "-march=native", "-fopenmp", str(SRC), "-lm", "-o", str(EXE)]
    print("Compilando:", " ".join(cmd))
    run(cmd)


def parse_output(output):
    config = re.search(
        r"CONFIG mode=(\S+) nx=(\d+) ny=(\d+) steps=(\d+) nu=([0-9.eE+-]+) "
        r"dt=([0-9.eE+-]+) init=(\S+) u0=([0-9.eE+-]+) schedule=(\S+) "
        r"chunk=(\d+) collapse=(\d+) threads=(\d+) stable=(\S+)",
        output,
    )
    initial = re.search(
        r"INITIAL min=([0-9.eE+-]+) max=([0-9.eE+-]+) "
        r"l2=([0-9.eE+-]+) sum=([0-9.eE+-]+)",
        output,
    )
    result = re.search(
        r"RESULT elapsed=([0-9.eE+-]+) min=([0-9.eE+-]+) max=([0-9.eE+-]+) "
        r"l2=([0-9.eE+-]+) sum=([0-9.eE+-]+)",
        output,
    )
    if not config or not initial or not result:
        raise ValueError("Saida inesperada:\n" + output)

    return {
        "mode": config.group(1),
        "nx": int(config.group(2)),
        "ny": int(config.group(3)),
        "steps": int(config.group(4)),
        "nu": float(config.group(5)),
        "dt": float(config.group(6)),
        "init": config.group(7),
        "u0": float(config.group(8)),
        "schedule": config.group(9),
        "chunk": int(config.group(10)),
        "collapse": int(config.group(11)),
        "threads": int(config.group(12)),
        "stable": config.group(13),
        "initial_min": float(initial.group(1)),
        "initial_max": float(initial.group(2)),
        "initial_l2": float(initial.group(3)),
        "initial_sum": float(initial.group(4)),
        "elapsed": float(result.group(1)),
        "final_min": float(result.group(2)),
        "final_max": float(result.group(3)),
        "final_l2": float(result.group(4)),
        "final_sum": float(result.group(5)),
    }


def execute(args, threads):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env.setdefault("OMP_PROC_BIND", "close")
    env.setdefault("OMP_PLACES", "cores")
    output = run([str(EXE), *args], env=env)
    return parse_output(output)


def thread_list(max_threads):
    values = []
    t = 1
    while t <= max_threads:
        values.append(t)
        t *= 2
    if values[-1] != max_threads:
        values.append(max_threads)
    return values


def weak_size(base_n, threads):
    n = int(round(base_n * math.sqrt(threads)))
    return max(3, n)


def collect(args):
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    threads_values = thread_list(args.max_threads)

    base_common = [
        "--steps", str(args.steps),
        "--nu", "0.1",
        "--dt", "0.1",
        "--init", "perturb",
        "--schedule", args.schedule,
        "--chunk", str(args.chunk),
        "--collapse", str(args.collapse),
    ]

    print("\nEscalabilidade forte: problema fixo")
    for mode in args.modes:
        for threads in threads_values:
            for rep in range(1, args.repeats + 1):
                cmd_args = [
                    "--mode", mode,
                    "--nx", str(args.strong_n),
                    "--ny", str(args.strong_n),
                    *base_common,
                ]
                row = execute(cmd_args, threads)
                row["experiment"] = "strong"
                row["rep"] = rep
                row["cells_per_thread"] = (row["nx"] * row["ny"]) / threads
                rows.append(row)
                print(
                    f"strong mode={mode} threads={threads} rep={rep} "
                    f"n={row['nx']} elapsed={row['elapsed']:.6f}"
                )

    print("\nEscalabilidade fraca: celulas por thread aproximadamente constantes")
    for mode in args.modes:
        for threads in threads_values:
            n = weak_size(args.weak_base_n, threads)
            for rep in range(1, args.repeats + 1):
                cmd_args = [
                    "--mode", mode,
                    "--nx", str(n),
                    "--ny", str(n),
                    *base_common,
                ]
                row = execute(cmd_args, threads)
                row["experiment"] = "weak"
                row["rep"] = rep
                row["cells_per_thread"] = (row["nx"] * row["ny"]) / threads
                rows.append(row)
                print(
                    f"weak mode={mode} threads={threads} rep={rep} "
                    f"n={row['nx']} cells/thread={row['cells_per_thread']:.0f} "
                    f"elapsed={row['elapsed']:.6f}"
                )

    add_metrics(rows)
    write_csv(rows)
    make_plots(rows)


def add_metrics(rows):
    best_strong_seq = {}
    best_weak_base = {}

    for row in rows:
        key = row["mode"]
        if row["experiment"] == "strong" and row["threads"] == 1:
            best_strong_seq[key] = min(best_strong_seq.get(key, float("inf")), row["elapsed"])
        if row["experiment"] == "weak" and row["threads"] == 1:
            best_weak_base[key] = min(best_weak_base.get(key, float("inf")), row["elapsed"])

    for row in rows:
        mode = row["mode"]
        if row["experiment"] == "strong":
            base = best_strong_seq[mode]
            row["strong_speedup"] = base / row["elapsed"]
            row["strong_efficiency"] = row["strong_speedup"] / row["threads"]
            row["weak_efficiency"] = ""
        else:
            base = best_weak_base[mode]
            row["weak_efficiency"] = base / row["elapsed"]
            row["strong_speedup"] = ""
            row["strong_efficiency"] = ""


def write_csv(rows):
    fields = [
        "experiment", "rep", "mode", "threads", "nx", "ny", "steps",
        "cells_per_thread", "nu", "dt", "init", "u0",
        "schedule", "chunk", "collapse", "elapsed",
        "strong_speedup", "strong_efficiency", "weak_efficiency",
        "stable", "initial_min", "initial_max", "final_min", "final_max",
        "initial_l2", "final_l2", "initial_sum", "final_sum",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV salvo em: {CSV_FILE}")


def best_by_group(rows, experiment, metric_key):
    best = {}
    for row in rows:
        if row["experiment"] != experiment:
            continue
        key = (row["mode"], row["threads"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["mode"], row["threads"]))


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    strong = best_by_group(rows, "strong", "strong_speedup")
    weak = best_by_group(rows, "weak", "weak_efficiency")
    modes = sorted({row["mode"] for row in rows})

    plt.figure(figsize=(8, 5))
    for mode in modes:
        data = [row for row in strong if row["mode"] == mode]
        plt.plot(
            [row["threads"] for row in data],
            [float(row["strong_speedup"]) for row in data],
            marker="o",
            label=mode,
        )
    plt.xlabel("Threads")
    plt.ylabel("Speedup forte")
    plt.title("Escalabilidade forte - Navier-Stokes")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "strong_scaling.png", dpi=160)

    plt.figure(figsize=(8, 5))
    for mode in modes:
        data = [row for row in weak if row["mode"] == mode]
        plt.plot(
            [row["threads"] for row in data],
            [float(row["weak_efficiency"]) for row in data],
            marker="o",
            label=mode,
        )
    plt.xlabel("Threads")
    plt.ylabel("Eficiencia fraca")
    plt.title("Escalabilidade fraca - Navier-Stokes")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "weak_scaling.png", dpi=160)

    print(f"Graficos salvos em: {OUT_DIR}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", default=os.environ.get("CC", "gcc"))
    parser.add_argument("--max-threads", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "8")))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--strong-n", type=int, default=2048)
    parser.add_argument("--weak-base-n", type=int, default=1024)
    parser.add_argument("--schedule", default="static")
    parser.add_argument("--chunk", type=int, default=0)
    parser.add_argument("--collapse", type=int, default=1)
    parser.add_argument("--modes", nargs="+", default=["omp-basic", "omp-region"])
    args = parser.parse_args()

    compile_program(args.cc)
    collect(args)


if __name__ == "__main__":
    main()
