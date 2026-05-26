import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "navier_stokes_viscosidade.c"
EXE = ROOT / ("navier.exe" if os.name == "nt" else "navier")


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
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode == 0:
        return True

    print(completed.stdout, end="")
    print(completed.stderr, end="", file=sys.stderr)
    print("\nAviso: falha ao compilar com OpenMP. Tentando fallback sequencial sem -fopenmp.")
    print("Esse fallback valida a simulacao, mas nao mede paralelismo.")

    fallback_cmd = ["gcc", "-O3", str(SRC), "-lm", "-o", str(EXE)]
    print("Compilando:", " ".join(fallback_cmd))
    run(fallback_cmd)
    return False


def parse_result(output):
    elapsed_match = re.search(r"RESULT elapsed=([0-9.]+)", output)
    max_match = re.search(r"RESULT .* max=([0-9.+\-eE]+)", output)
    l2_match = re.search(r"RESULT .* l2=([0-9.+\-eE]+)", output)
    if not elapsed_match or not max_match or not l2_match:
        raise ValueError("Saida inesperada:\n" + output)
    return {
        "elapsed": float(elapsed_match.group(1)),
        "max": float(max_match.group(1)),
        "l2": float(l2_match.group(1)),
    }


def execute(args, threads=1):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    output = run([str(EXE), *args], env=env)
    return output, parse_result(output)


def validate():
    common = ["--nx", "128", "--ny", "128", "--steps", "200", "--nu", "0.1", "--dt", "0.1"]

    print("\nValidacao fisica")
    zero_out, zero = execute(["--mode", "seq", "--init", "zero", *common])
    uniform_out, uniform = execute(["--mode", "seq", "--init", "uniform", "--u0", "2.0", *common])
    perturb_out, perturb = execute(["--mode", "seq", "--init", "perturb", *common])

    print(zero_out.strip())
    print(uniform_out.strip())
    print(perturb_out.strip())

    if abs(zero["max"]) > 1e-12 or abs(zero["l2"]) > 1e-12:
        raise SystemExit("Falha: campo zero nao permaneceu zero.")
    if abs(uniform["max"] - 2.0) > 1e-12:
        raise SystemExit("Falha: campo uniforme nao permaneceu constante.")
    if perturb["max"] >= 1.0:
        raise SystemExit("Falha: perturbacao nao se difundiu.")


def benchmark():
    base_args = [
        "--nx", "512",
        "--ny", "512",
        "--steps", "600",
        "--nu", "0.1",
        "--dt", "0.1",
        "--init", "perturb",
    ]
    thread_counts = [1, 2, 4, 8]
    schedules = [("static", 0), ("static", 64), ("dynamic", 64), ("guided", 64)]
    collapses = [1, 2]

    print("\nBenchmark")
    _, seq = execute(["--mode", "seq", *base_args], threads=1)
    seq_time = seq["elapsed"]
    print(f"seq threads=1 elapsed={seq_time:.6f} speedup=1.00")

    for threads in thread_counts:
        for collapse in collapses:
            for schedule, chunk in schedules:
                args = [
                    "--mode", "omp",
                    "--schedule", schedule,
                    "--chunk", str(chunk),
                    "--collapse", str(collapse),
                    *base_args,
                ]
                _, result = execute(args, threads=threads)
                speedup = seq_time / result["elapsed"]
                efficiency = speedup / threads
                print(
                    f"omp threads={threads} schedule={schedule:<7} chunk={chunk:<3} "
                    f"collapse={collapse} elapsed={result['elapsed']:.6f} "
                    f"speedup={speedup:.2f} efficiency={efficiency:.2f}"
                )


def main():
    openmp_enabled = compile_program()
    validate()
    if openmp_enabled:
        benchmark()
    else:
        print("\nBenchmark OpenMP ignorado: compilador local nao conseguiu linkar -fopenmp.")


if __name__ == "__main__":
    main()
