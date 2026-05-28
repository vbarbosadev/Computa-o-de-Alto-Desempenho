import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT_DIR = ROOT / "resultados"
BUILD_DIR = ROOT / "build"
CSV_FILE = OUT_DIR / "tarefa18_resultados.csv"

SEQ_SRC = REPO / "Tarefa-17" / "matvec_seq.c"
SEQ_EXE = BUILD_DIR / "matvec_seq"

VERSIONS = {
    "cols_vector": {
        "src": ROOT / "matvec_cols_vector.c",
        "exe": BUILD_DIR / "matvec_cols_vector",
    },
    "cols_resized": {
        "src": ROOT / "matvec_cols_resized.c",
        "exe": BUILD_DIR / "matvec_cols_resized",
    },
}

SEQ_RE = re.compile(r"RESULT versao=seq m=(\d+) n=(\d+) tempo=([0-9.eE+-]+) checksum=([0-9.eE+-]+)")
MPI_RE = re.compile(
    r"RESULT versao=(cols_vector|cols_resized) processos=(\d+) m=(\d+) n=(\d+) "
    r"colunas_por_processo=(\d+) tempo=([0-9.eE+-]+) checksum=([0-9.eE+-]+)"
)


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


def compile_programs(cc, mpicc):
    BUILD_DIR.mkdir(exist_ok=True)
    run([cc, "-O3", "-Wall", "-Wextra", str(SEQ_SRC), "-o", str(SEQ_EXE)])
    for version in VERSIONS.values():
        run([mpicc, "-O3", "-Wall", "-Wextra", str(version["src"]), "-o", str(version["exe"])])


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


def parse_mpi(output):
    match = MPI_RE.search(output)
    if match is None:
        raise ValueError("Saida MPI inesperada:\n" + output)
    return {
        "version": match.group(1),
        "processes": int(match.group(2)),
        "m": int(match.group(3)),
        "n": int(match.group(4)),
        "cols_per_process": int(match.group(5)),
        "elapsed": float(match.group(6)),
        "checksum": float(match.group(7)),
    }


def execute_seq(m, n):
    return parse_seq(run([str(SEQ_EXE), "--m", str(m), "--n", str(n)]))


def execute_mpi(mpirun, version, processes, m, n, launcher_args):
    cmd = [
        mpirun,
        *launcher_args,
        "-np",
        str(processes),
        str(VERSIONS[version]["exe"]),
        "--m",
        str(m),
        "--n",
        str(n),
    ]
    return parse_mpi(run(cmd))


def write_csv(rows):
    OUT_DIR.mkdir(exist_ok=True)
    fields = [
        "version",
        "rep",
        "m",
        "n",
        "processes",
        "cols_per_process",
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
        key = (row["version"], row["m"], row["n"], row["processes"])
        if key not in best or row["elapsed"] < best[key]["elapsed"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["version"], row["m"], row["n"], row["processes"]))


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    best = best_by_group(rows)
    sizes = sorted({(row["m"], row["n"]) for row in rows})
    versions = ["cols_vector", "cols_resized"]

    for m, n in sizes:
        plt.figure(figsize=(8, 5))
        for version in versions:
            data = [row for row in best if row["version"] == version and row["m"] == m and row["n"] == n]
            plt.plot(
                [row["processes"] for row in data],
                [row["elapsed"] for row in data],
                marker="o",
                label=version,
            )
        plt.xlabel("Processos MPI")
        plt.ylabel("Tempo (s)")
        plt.title(f"Tempo - distribuicao por colunas {m}x{n}")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUT_DIR / f"tempo_{m}x{n}.png", dpi=160)
        plt.close()

    plt.figure(figsize=(8, 5))
    for version in versions:
        for m, n in sizes:
            data = [row for row in best if row["version"] == version and row["m"] == m and row["n"] == n]
            plt.plot(
                [row["processes"] for row in data],
                [row["speedup"] for row in data],
                marker="o",
                label=f"{version} {m}x{n}",
            )
    plt.xlabel("Processos MPI")
    plt.ylabel("Speedup")
    plt.title("Speedup - distribuicao por colunas")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "speedup.png", dpi=160)
    plt.close()

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
            if n % processes != 0:
                print(f"Ignorando {m}x{n} com {processes} processos: N nao divisivel.")
                continue
            for version in ["cols_vector", "cols_resized"]:
                for rep in range(1, args.repeats + 1):
                    result = execute_mpi(mpirun, version, processes, m, n, args.launcher_arg)
                    checksum_error = abs(result["checksum"] - seq["checksum"])
                    checksum_tolerance = max(1e-6, abs(seq["checksum"]) * 1e-9)
                    if checksum_error > checksum_tolerance:
                        raise ValueError(
                            f"Checksum divergente em {version}: MPI={result['checksum']} SEQ={seq['checksum']}"
                        )
                    speedup = seq["elapsed"] / result["elapsed"]
                    efficiency = speedup / processes
                    row = {
                        "version": version,
                        "rep": rep,
                        "m": m,
                        "n": n,
                        "processes": processes,
                        "cols_per_process": result["cols_per_process"],
                        "seq_time": seq["elapsed"],
                        "elapsed": result["elapsed"],
                        "speedup": speedup,
                        "efficiency": efficiency,
                        "checksum": result["checksum"],
                    }
                    rows.append(row)
                    print(
                        f"{version} {m}x{n} processos={processes} rep={rep} "
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
    parser.add_argument("--sizes", nargs="+", default=["1000x1000", "2000x2000", "4000x2000"])
    parser.add_argument("--processes", nargs="+", type=int, default=[1, 2, 4])
    parser.add_argument("--launcher-arg", action="append", default=[])
    return parser.parse_args()


def main():
    args = parse_args()
    collect(args)


if __name__ == "__main__":
    main()
