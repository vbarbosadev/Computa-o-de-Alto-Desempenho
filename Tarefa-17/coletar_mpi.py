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
CSV_FILE = OUT_DIR / "tarefa17_resultados.csv"

SEQ_SRC = ROOT / "matvec_seq.c"
MPI_SRC = ROOT / "matvec_collective.c"
SEQ_EXE = BUILD_DIR / "matvec_seq"
MPI_EXE = BUILD_DIR / "matvec_collective"

SEQ_RE = re.compile(r"RESULT versao=seq m=(\d+) n=(\d+) tempo=([0-9.eE+-]+) checksum=([0-9.eE+-]+)")
MPI_RE = re.compile(
    r"RESULT versao=mpi_collective processos=(\d+) m=(\d+) n=(\d+) "
    r"linhas_por_processo=(\d+) tempo=([0-9.eE+-]+) checksum=([0-9.eE+-]+)"
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
    run([cc, "-O3", "-Wall", "-Wextra", str(SEQ_SRC), "-o", str(SEQ_EXE)])
    run([mpicc, "-O3", "-Wall", "-Wextra", str(MPI_SRC), "-o", str(MPI_EXE)])


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


def parse_mpi(output):
    match = MPI_RE.search(output)
    if match is None:
        raise ValueError("Saida MPI inesperada:\n" + output)
    return {
        "processes": int(match.group(1)),
        "m": int(match.group(2)),
        "n": int(match.group(3)),
        "rows_per_process": int(match.group(4)),
        "elapsed": float(match.group(5)),
        "checksum": float(match.group(6)),
    }


def execute_seq(m, n):
    return parse_seq(run([str(SEQ_EXE), "--m", str(m), "--n", str(n)]))


def execute_mpi(mpirun, processes, m, n, launcher_args):
    cmd = [
        mpirun,
        *launcher_args,
        "-np",
        str(processes),
        str(MPI_EXE),
        "--m",
        str(m),
        "--n",
        str(n),
    ]
    return parse_mpi(run(cmd))


def write_csv(rows):
    OUT_DIR.mkdir(exist_ok=True)
    fields = [
        "rep",
        "m",
        "n",
        "processes",
        "rows_per_process",
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
        key = (row["m"], row["n"], row["processes"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["m"], row["n"], row["processes"]))


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
            [row["processes"] for row in data],
            [row["speedup"] for row in data],
            marker="o",
            label=f"{m}x{n}",
        )
    plt.xlabel("Processos MPI")
    plt.ylabel("Speedup")
    plt.title("Speedup - produto matriz-vetor")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "speedup.png", dpi=160)

    plt.figure(figsize=(8, 5))
    for m, n in sizes:
        data = [row for row in best if row["m"] == m and row["n"] == n]
        plt.plot(
            [row["processes"] for row in data],
            [row["efficiency"] for row in data],
            marker="o",
            label=f"{m}x{n}",
        )
    plt.xlabel("Processos MPI")
    plt.ylabel("Eficiencia")
    plt.title("Eficiencia - produto matriz-vetor")
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

    seq_by_size = {}
    for size_text in args.sizes:
        m, n = parse_size(size_text)
        seq = execute_seq(m, n)
        seq_by_size[(m, n)] = seq
        print(f"seq {m}x{n} tempo={seq['elapsed']:.6f}s checksum={seq['checksum']:.6f}")

    rows = []
    for size_text in args.sizes:
        m, n = parse_size(size_text)
        seq = seq_by_size[(m, n)]
        for processes in args.processes:
            if m % processes != 0:
                print(f"Ignorando {m}x{n} com {processes} processos: M nao divisivel.")
                continue
            for rep in range(1, args.repeats + 1):
                result = execute_mpi(mpirun, processes, m, n, args.launcher_arg)
                checksum_error = abs(result["checksum"] - seq["checksum"])
                checksum_tolerance = max(1e-6, abs(seq["checksum"]) * 1e-9)
                if checksum_error > checksum_tolerance:
                    raise ValueError(
                        f"Checksum divergente: MPI={result['checksum']} SEQ={seq['checksum']}"
                    )
                speedup = seq["elapsed"] / result["elapsed"]
                efficiency = speedup / processes
                row = {
                    "rep": rep,
                    "m": m,
                    "n": n,
                    "processes": processes,
                    "rows_per_process": result["rows_per_process"],
                    "seq_time": seq["elapsed"],
                    "elapsed": result["elapsed"],
                    "speedup": speedup,
                    "efficiency": efficiency,
                    "checksum": result["checksum"],
                }
                rows.append(row)
                print(
                    f"mpi {m}x{n} processos={processes} rep={rep} "
                    f"tempo={result['elapsed']:.6f}s speedup={speedup:.2f}"
                )

    write_csv(rows)
    make_plots(rows)


def parse_size(value):
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Use o formato MxN, por exemplo 2000x2000.")
    return int(parts[0]), int(parts[1])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cc", default=os.environ.get("CC", "gcc"))
    parser.add_argument("--mpicc", default=os.environ.get("MPICC", "mpicc"))
    parser.add_argument("--mpirun", default=os.environ.get("MPIRUN", "mpirun"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--sizes", nargs="+", default=["1000x1000", "2000x2000", "4000x2000"])
    parser.add_argument("--processes", nargs="+", type=int, default=[1, 2, 4])
    parser.add_argument("--launcher-arg", action="append", default=[])
    return parser.parse_args()


def main():
    args = parse_args()
    collect(args)


if __name__ == "__main__":
    main()
