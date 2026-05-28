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
CSV_FILE = OUT_DIR / "tarefa14_resultados.csv"

PROGRAMS = {
    "MPI_Send": ROOT / "mpi_send.c",
    "MPI_Bsend": ROOT / "mpi_bsend.c",
    "MPI_Rsend": ROOT / "mpi_rsend.c",
    "MPI_Ssend": ROOT / "mpi_ssend.c",
}

RESULT_RE = re.compile(
    r"RESULT metodo=(\S+) bytes=(\d+) iteracoes=(\d+) "
    r"tempo_total=([0-9.eE+-]+) tempo_medio=([0-9.eE+-]+)"
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
    for method, source in PROGRAMS.items():
        exe = BUILD_DIR / method.replace("MPI_", "mpi_").lower()
        cmd = [mpicc, "-O3", "-Wall", "-Wextra", str(source), "-o", str(exe)]
        print("Compilando:", " ".join(cmd))
        run(cmd)
        executables[method] = exe
    return executables


def default_iterations(bytes_count):
    if bytes_count <= 1024:
        return 20000
    if bytes_count <= 65536:
        return 5000
    if bytes_count <= 1048576:
        return 1000
    return 200


def parse_result(output):
    match = RESULT_RE.search(output)
    if match is None:
        raise ValueError("Saida inesperada:\n" + output)
    bytes_count = int(match.group(2))
    iterations = int(match.group(3))
    total_seconds = float(match.group(4))
    avg_roundtrip_seconds = float(match.group(5))
    mib_transferred = (2.0 * bytes_count * iterations) / (1024.0 * 1024.0)
    return {
        "method": match.group(1),
        "bytes": bytes_count,
        "iterations": iterations,
        "total_seconds": total_seconds,
        "avg_roundtrip_seconds": avg_roundtrip_seconds,
        "one_way_latency_seconds": avg_roundtrip_seconds / 2.0,
        "bandwidth_mib_s": mib_transferred / total_seconds,
    }


def execute(mpirun, exe, bytes_count, iterations, launcher_args):
    cmd = [
        mpirun,
        *launcher_args,
        "-np",
        "2",
        str(exe),
        "--bytes",
        str(bytes_count),
        "--iteracoes",
        str(iterations),
    ]
    return parse_result(run(cmd))


def write_csv(rows):
    OUT_DIR.mkdir(exist_ok=True)
    fields = [
        "rep",
        "method",
        "bytes",
        "iterations",
        "total_seconds",
        "avg_roundtrip_seconds",
        "one_way_latency_seconds",
        "bandwidth_mib_s",
    ]
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV salvo em: {CSV_FILE}")


def best_by_group(rows):
    best = {}
    for row in rows:
        key = (row["method"], row["bytes"])
        if key not in best or row["avg_roundtrip_seconds"] < best[key]["avg_roundtrip_seconds"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (row["method"], row["bytes"]))


def make_plots(rows):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib nao instalado; o CSV foi gerado sem graficos.")
        return

    best = best_by_group(rows)
    methods = sorted({row["method"] for row in rows})

    plt.figure(figsize=(8, 5))
    for method in methods:
        data = [row for row in best if row["method"] == method]
        plt.plot(
            [row["bytes"] for row in data],
            [row["avg_roundtrip_seconds"] * 1e6 for row in data],
            marker="o",
            label=method,
        )
    plt.xscale("log", base=2)
    plt.yscale("log")
    plt.xlabel("Tamanho da mensagem (bytes)")
    plt.ylabel("Tempo medio de ida e volta (us)")
    plt.title("Tempo de comunicacao MPI por tamanho de mensagem")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "tempo_por_tamanho.png", dpi=160)

    plt.figure(figsize=(8, 5))
    for method in methods:
        data = [row for row in best if row["method"] == method]
        plt.plot(
            [row["bytes"] for row in data],
            [row["bandwidth_mib_s"] for row in data],
            marker="o",
            label=method,
        )
    plt.xscale("log", base=2)
    plt.xlabel("Tamanho da mensagem (bytes)")
    plt.ylabel("Largura de banda efetiva (MiB/s)")
    plt.title("Largura de banda efetiva no ping-pong MPI")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "largura_banda.png", dpi=160)
    print(f"Graficos salvos em: {OUT_DIR}")


def collect(args):
    mpicc = require_tool(args.mpicc)
    mpirun = require_tool(args.mpirun)
    executables = compile_programs(mpicc)
    rows = []

    for method, exe in executables.items():
        print(f"\nExecutando {method}")
        for bytes_count in args.sizes:
            iterations = args.iterations or default_iterations(bytes_count)
            for rep in range(1, args.repeats + 1):
                row = execute(
                    mpirun,
                    exe,
                    bytes_count,
                    iterations,
                    args.launcher_arg,
                )
                row["rep"] = rep
                rows.append(row)
                print(
                    f"{method} bytes={bytes_count} rep={rep} "
                    f"roundtrip={row['avg_roundtrip_seconds'] * 1e6:.3f}us "
                    f"bandwidth={row['bandwidth_mib_s']:.2f}MiB/s"
                )

    write_csv(rows)
    make_plots(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mpicc", default=os.environ.get("MPICC", "mpicc"))
    parser.add_argument("--mpirun", default=os.environ.get("MPIRUN", "mpirun"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--iteracoes", dest="iterations", type=int, default=None)
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[8, 16, 32, 64, 128, 256, 512, 1024, 4096, 16384, 65536, 262144, 1048576],
    )
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
