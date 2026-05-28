import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT_DIR = ROOT / "resultados"
BUILD_DIR = ROOT / "build"
CSV_FILE = OUT_DIR / "tarefa18_openmp_resultados.csv"

SEQ_SRC = REPO / "Tarefa-17" / "matvec_seq.c"
OMP_SRC = ROOT / "matvec_openmp.c"
SEQ_EXE = BUILD_DIR / "matvec_seq"
OMP_EXE = BUILD_DIR / "matvec_openmp"

SEQ_RE = re.compile(r"RESULT versao=seq m=(\d+) n=(\d+) tempo=([0-9.eE+-]+) checksum=([0-9.eE+-]+)")
OMP_RE = re.compile(r"RESULT versao=openmp threads=(\d+) m=(\d+) n=(\d+) tempo=([0-9.eE+-]+) checksum=([0-9.eE+-]+)")


def run(cmd):
    completed = subprocess.run(
        cmd,
        cwd=REPO,
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


def compile_programs(cc):
    BUILD_DIR.mkdir(exist_ok=True)
    run([cc, "-O3", "-Wall", "-Wextra", str(SEQ_SRC), "-o", str(SEQ_EXE)])
    run([cc, "-O3", "-Wall", "-Wextra", "-fopenmp", str(OMP_SRC), "-o", str(OMP_EXE)])


def parse_size(value):
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Use o formato MxN, por exemplo 2000x2000.")
    return int(parts[0]), int(parts[1])


def parse_seq(output):
    match = SEQ_RE.search(output)
    if match is None:
        raise ValueError("Saida sequencial inesperada:\n" + output)
    return {
        "m": int(match.group(1)),
        "n": int(match.group(2)),
        "elapsed": float(match.group(3)),
        "checksum": float(match.group(4)),
    }


def parse_openmp(output):
    match = OMP_RE.search(output)
    if match is None:
        raise ValueError("Saida OpenMP inesperada:\n" + output)
    return {
        "threads": int(match.group(1)),
        "m": int(match.group(2)),
        "n": int(match.group(3)),
        "elapsed": float(match.group(4)),
        "checksum": float(match.group(5)),
    }


def execute_seq(m, n):
    return parse_seq(run([str(SEQ_EXE), "--m", str(m), "--n", str(n)]))


def execute_openmp(m, n, threads):
    env_threads = str(threads)
    return parse_openmp(
        run([
            str(OMP_EXE),
            "--m",
            str(m),
            "--n",
            str(n),
            "--threads",
            env_threads,
        ])
    )


def write_csv(rows):
    OUT_DIR.mkdir(exist_ok=True)
    fields = [
        "rep",
        "m",
        "n",
        "threads",
        "seq_time",
        "elapsed",
        "speedup",
        "efficiency",
        "checksum",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV salvo em: {CSV_FILE}")


def best_by_group(rows):
    best = {}
    for row in rows:
        key = (row["m"], row["n"], row["threads"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["m"], row["n"], row["threads"]))


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    best = best_by_group(rows)
    sizes = sorted({(row["m"], row["n"]) for row in rows})

    plt.figure(figsize=(8, 5))
    for m, n in sizes:
        data = [row for row in best if row["m"] == m and row["n"] == n]
        plt.plot(
            [row["threads"] for row in data],
            [row["speedup"] for row in data],
            marker="o",
            label=f"{m}x{n}",
        )
    plt.xlabel("Threads OpenMP")
    plt.ylabel("Speedup")
    plt.title("Speedup - OpenMP")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "speedup.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    for m, n in sizes:
        data = [row for row in best if row["m"] == m and row["n"] == n]
        plt.plot(
            [row["threads"] for row in data],
            [row["elapsed"] for row in data],
            marker="o",
            label=f"{m}x{n}",
        )
    plt.xlabel("Threads OpenMP")
    plt.ylabel("Tempo (s)")
    plt.title("Tempo - OpenMP")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "tempo.png", dpi=160)
    plt.close()

    print(f"Graficos salvos em: {OUT_DIR}")


def collect(args):
    cc = require_tool(args.cc)
    compile_programs(cc)

    seq_by_size = {}
    for size_text in args.sizes:
        m, n = parse_size(size_text)
        seq_runs = [execute_seq(m, n) for _ in range(args.repeats)]
        seq = {
            "m": m,
            "n": n,
            "elapsed": statistics.mean(row["elapsed"] for row in seq_runs),
            "checksum": seq_runs[0]["checksum"],
        }
        seq_by_size[(m, n)] = seq
        print(f"seq {m}x{n} tempo_medio={seq['elapsed']:.6f}s checksum={seq['checksum']:.6f}")

    rows = []
    for size_text in args.sizes:
        m, n = parse_size(size_text)
        seq = seq_by_size[(m, n)]
        for threads in args.threads:
            for rep in range(1, args.repeats + 1):
                result = execute_openmp(m, n, threads)
                checksum_error = abs(result["checksum"] - seq["checksum"])
                checksum_tolerance = max(1e-6, abs(seq["checksum"]) * 1e-9)
                if checksum_error > checksum_tolerance:
                    raise ValueError(
                        f"Checksum divergente: OpenMP={result['checksum']} SEQ={seq['checksum']}"
                    )
                speedup = seq["elapsed"] / result["elapsed"]
                efficiency = speedup / threads
                row = {
                    "rep": rep,
                    "m": m,
                    "n": n,
                    "threads": threads,
                    "seq_time": seq["elapsed"],
                    "elapsed": result["elapsed"],
                    "speedup": speedup,
                    "efficiency": efficiency,
                    "checksum": result["checksum"],
                }
                rows.append(row)
                print(
                    f"openmp {m}x{n} threads={threads} rep={rep} "
                    f"tempo={result['elapsed']:.6f}s speedup={speedup:.2f}"
                )

    write_csv(rows)
    make_plots(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", default=os.environ.get("CC", "gcc"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--sizes", nargs="+", default=["1000x1000", "2000x2000", "4000x2000"])
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 2, 4, 8])
    return parser.parse_args()


def main():
    args = parse_args()
    collect(args)


if __name__ == "__main__":
    main()
