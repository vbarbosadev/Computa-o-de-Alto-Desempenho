import csv
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "navier_stokes_viscosidade.c"
EXE = ROOT / ("navier.exe" if os.name == "nt" else "navier")
OUT_DIR = ROOT / "resultados"
CSV_FILE = OUT_DIR / "resultados.csv"


def run(cmd, env=None):
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed.stdout


def compile_program():
    cmd = ["gcc", "-O3", "-fopenmp", str(SRC), "-lm", "-o", str(EXE)]
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
    output = run([str(EXE), *args], env=env)
    return parse_output(output)


def collect():
    OUT_DIR.mkdir(exist_ok=True)

    base_args = [
        "--nx", "1024",
        "--ny", "1024",
        "--steps", "1000",
        "--nu", "0.1",
        "--dt", "0.1",
        "--init", "perturb",
    ]
    thread_counts = [1, 2, 4, 8]
    schedules = [("static", 0), ("static", 64), ("dynamic", 64), ("guided", 64)]
    collapses = [1, 2]
    repeats = 3

    rows = []

    print("Executando baseline sequencial...")
    seq_times = []
    for rep in range(1, repeats + 1):
        row = execute(["--mode", "seq", *base_args], threads=1)
        row["rep"] = rep
        row["case"] = "seq"
        rows.append(row)
        seq_times.append(row["elapsed"])

    seq_best = min(seq_times)

    print("Executando combinacoes OpenMP...")
    for threads in thread_counts:
        for collapse in collapses:
            for schedule, chunk in schedules:
                for rep in range(1, repeats + 1):
                    args = [
                        "--mode", "omp",
                        "--schedule", schedule,
                        "--chunk", str(chunk),
                        "--collapse", str(collapse),
                        *base_args,
                    ]
                    row = execute(args, threads=threads)
                    row["rep"] = rep
                    row["case"] = "omp"
                    row["speedup"] = seq_best / row["elapsed"]
                    row["efficiency"] = row["speedup"] / threads
                    rows.append(row)
                    print(
                        f"threads={threads} schedule={schedule} chunk={chunk} "
                        f"collapse={collapse} rep={rep} elapsed={row['elapsed']:.6f}"
                    )

    for row in rows:
        row.setdefault("speedup", seq_best / row["elapsed"])
        row.setdefault("efficiency", row["speedup"] / max(row["threads"], 1))

    fields = [
        "case", "rep", "mode", "threads", "schedule", "chunk", "collapse",
        "nx", "ny", "steps", "nu", "dt", "init", "u0", "stable",
        "elapsed", "speedup", "efficiency",
        "initial_min", "initial_max", "initial_l2", "initial_sum",
        "final_min", "final_max", "final_l2", "final_sum",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV salvo em: {CSV_FILE}")
    return rows


def plot(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; apenas o CSV foi gerado.")
        print("Para graficos: python3 -m pip install matplotlib")
        return

    best = {}
    for row in rows:
        if row["case"] != "omp":
            continue
        key = (row["threads"], row["schedule"], row["chunk"], row["collapse"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row

    static_c2 = [
        row for key, row in best.items()
        if row["schedule"] == "static" and row["chunk"] == 0 and row["collapse"] == 2
    ]
    static_c2.sort(key=lambda row: row["threads"])

    plt.figure(figsize=(8, 5))
    plt.plot(
        [row["threads"] for row in static_c2],
        [row["speedup"] for row in static_c2],
        marker="o",
        label="static, collapse(2)",
    )
    plt.xlabel("Threads")
    plt.ylabel("Speedup")
    plt.title("Speedup OpenMP - Navier-Stokes simplificada")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "speedup_static_collapse2.png", dpi=160)

    rows_8 = [
        row for key, row in best.items()
        if row["threads"] == 8 and row["collapse"] == 2
    ]
    labels = [f"{row['schedule']},{row['chunk']}" for row in rows_8]
    times = [row["elapsed"] for row in rows_8]

    plt.figure(figsize=(8, 5))
    plt.bar(labels, times)
    plt.xlabel("schedule,chunk")
    plt.ylabel("Tempo (s)")
    plt.title("Comparacao de escalonamento - 8 threads, collapse(2)")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "schedules_8threads.png", dpi=160)

    print(f"Graficos salvos em: {OUT_DIR}")


def main():
    compile_program()
    rows = collect()
    plot(rows)


if __name__ == "__main__":
    main()
