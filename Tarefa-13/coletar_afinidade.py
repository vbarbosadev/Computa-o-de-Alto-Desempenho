import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "navier_scaling.c"
EXE = ROOT / "navier_affinity"
OUT_DIR = ROOT / "resultados"
CSV_FILE = OUT_DIR / "tarefa13_afinidade.csv"


AFFINITIES = {
    "sem_bind": {
        "description": "Sem fixacao explicita pelo OpenMP",
        "env": {"OMP_PROC_BIND": "false"},
        "unset": ["OMP_PLACES", "GOMP_CPU_AFFINITY"],
    },
    "close_cores": {
        "description": "Threads proximas em nucleos",
        "env": {"OMP_PROC_BIND": "close", "OMP_PLACES": "cores"},
        "unset": ["GOMP_CPU_AFFINITY"],
    },
    "spread_cores": {
        "description": "Threads espalhadas entre nucleos",
        "env": {"OMP_PROC_BIND": "spread", "OMP_PLACES": "cores"},
        "unset": ["GOMP_CPU_AFFINITY"],
    },
    "close_threads": {
        "description": "Threads proximas em hardware threads",
        "env": {"OMP_PROC_BIND": "close", "OMP_PLACES": "threads"},
        "unset": ["GOMP_CPU_AFFINITY"],
    },
    "spread_threads": {
        "description": "Threads espalhadas entre hardware threads",
        "env": {"OMP_PROC_BIND": "spread", "OMP_PLACES": "threads"},
        "unset": ["GOMP_CPU_AFFINITY"],
    },
    "gomp_cpu_affinity": {
        "description": "Afinidade explicita do GNU OpenMP por lista de CPUs",
        "env": {},
        "unset": ["OMP_PROC_BIND", "OMP_PLACES"],
        "uses_gomp": True,
    },
}


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
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
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


def thread_list(max_threads):
    values = []
    t = 1
    while t <= max_threads:
        values.append(t)
        t *= 2
    if values[-1] != max_threads:
        values.append(max_threads)
    return values


def current_cpus(max_threads):
    try:
        cpus = sorted(os.sched_getaffinity(0))
    except AttributeError:
        cpus = list(range(max_threads))
    return cpus[:max_threads]


def gomp_cpu_list(cpus, threads):
    selected = cpus[:threads]
    return " ".join(str(cpu) for cpu in selected)


def affinity_env(base_env, affinity_name, threads, cpus):
    config = AFFINITIES[affinity_name]
    env = base_env.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    for key in config.get("unset", []):
        env.pop(key, None)
    for key, value in config.get("env", {}).items():
        env[key] = value
    if config.get("uses_gomp"):
        env["GOMP_CPU_AFFINITY"] = gomp_cpu_list(cpus, threads)
    return env


def execute(args, affinity_name, threads, cpus):
    env = affinity_env(os.environ, affinity_name, threads, cpus)
    cmd_args = [
        str(EXE),
        "--mode", args.mode,
        "--nx", str(args.n),
        "--ny", str(args.n),
        "--steps", str(args.steps),
        "--nu", "0.1",
        "--dt", "0.1",
        "--init", "perturb",
        "--schedule", args.schedule,
        "--chunk", str(args.chunk),
        "--collapse", str(args.collapse),
    ]
    row = parse_output(run(cmd_args, env=env))
    row["affinity"] = affinity_name
    row["affinity_description"] = AFFINITIES[affinity_name]["description"]
    row["omp_proc_bind"] = env.get("OMP_PROC_BIND", "")
    row["omp_places"] = env.get("OMP_PLACES", "")
    row["gomp_cpu_affinity"] = env.get("GOMP_CPU_AFFINITY", "")
    row["allowed_cpus"] = " ".join(str(cpu) for cpu in cpus)
    row["cells_per_thread"] = (row["nx"] * row["ny"]) / threads
    return row


def add_metrics(rows):
    best_one_thread = {}
    for row in rows:
        if row["threads"] == 1:
            key = row["affinity"]
            best_one_thread[key] = min(best_one_thread.get(key, float("inf")), row["elapsed"])

    baseline = min(best_one_thread.values())
    for row in rows:
        affinity_base = best_one_thread[row["affinity"]]
        row["speedup"] = affinity_base / row["elapsed"]
        row["efficiency"] = row["speedup"] / row["threads"]
        row["relative_to_best_1t"] = baseline / row["elapsed"]


def write_csv(rows):
    fields = [
        "rep", "affinity", "affinity_description", "mode", "threads",
        "nx", "ny", "steps", "cells_per_thread", "nu", "dt", "init", "u0",
        "schedule", "chunk", "collapse", "omp_proc_bind", "omp_places",
        "gomp_cpu_affinity", "allowed_cpus", "elapsed", "speedup",
        "efficiency", "relative_to_best_1t", "stable", "initial_min",
        "initial_max", "final_min", "final_max", "initial_l2", "final_l2",
        "initial_sum", "final_sum",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV salvo em: {CSV_FILE}")


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    best = {}
    for row in rows:
        key = (row["affinity"], row["threads"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row

    affinities = [name for name in AFFINITIES if name in {row["affinity"] for row in rows}]

    plt.figure(figsize=(9, 5))
    for affinity in affinities:
        data = sorted(
            [row for row in best.values() if row["affinity"] == affinity],
            key=lambda row: row["threads"],
        )
        plt.plot(
            [row["threads"] for row in data],
            [float(row["elapsed"]) for row in data],
            marker="o",
            label=affinity,
        )
    plt.xlabel("Threads")
    plt.ylabel("Melhor tempo (s)")
    plt.title("Afinidade de threads - tempo")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "affinity_elapsed.png", dpi=160)

    plt.figure(figsize=(9, 5))
    for affinity in affinities:
        data = sorted(
            [row for row in best.values() if row["affinity"] == affinity],
            key=lambda row: row["threads"],
        )
        plt.plot(
            [row["threads"] for row in data],
            [float(row["speedup"]) for row in data],
            marker="o",
            label=affinity,
        )
    plt.xlabel("Threads")
    plt.ylabel("Speedup forte")
    plt.title("Afinidade de threads - speedup")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "affinity_speedup.png", dpi=160)

    print(f"Graficos salvos em: {OUT_DIR}")


def collect(args):
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    threads_values = thread_list(args.max_threads)
    cpus = current_cpus(args.max_threads)

    if args.affinities == ["all"]:
        affinities = list(AFFINITIES)
    else:
        affinities = args.affinities
    unknown = [name for name in affinities if name not in AFFINITIES]
    if unknown:
        raise SystemExit(f"Afinidades desconhecidas: {', '.join(unknown)}")

    print("CPUs disponiveis para o processo:", " ".join(str(cpu) for cpu in cpus))
    print("Afinidades:", ", ".join(affinities))

    for affinity in affinities:
        print(f"\nAfinidade: {affinity} - {AFFINITIES[affinity]['description']}")
        for threads in threads_values:
            for rep in range(1, args.repeats + 1):
                row = execute(args, affinity, threads, cpus)
                row["rep"] = rep
                rows.append(row)
                print(
                    f"affinity={affinity} threads={threads} rep={rep} "
                    f"n={row['nx']} elapsed={row['elapsed']:.6f}"
                )

    add_metrics(rows)
    write_csv(rows)
    make_plots(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", default=os.environ.get("CC", "gcc"))
    parser.add_argument("--max-threads", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", "8")))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--n", type=int, default=2048)
    parser.add_argument("--mode", default="omp-region")
    parser.add_argument("--schedule", default="static")
    parser.add_argument("--chunk", type=int, default=0)
    parser.add_argument("--collapse", type=int, default=1)
    parser.add_argument("--affinities", nargs="+", default=["all"])
    args = parser.parse_args()

    if not shutil.which(args.cc):
        raise SystemExit(f"Compilador nao encontrado: {args.cc}")

    compile_program(args.cc)
    collect(args)


if __name__ == "__main__":
    main()
