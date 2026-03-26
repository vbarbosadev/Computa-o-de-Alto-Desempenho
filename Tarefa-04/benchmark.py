#!/usr/bin/env python3
"""
Benchmark: Memory-Bound vs Compute-Bound com OpenMP
Compila os programas C, executa com diferentes contagens de threads,
salva resultados em CSV + JSON e gera gráficos comparativos.
"""

import subprocess
import os
import re
import sys
import csv
import json
import platform
import multiprocessing
from datetime import datetime
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[AVISO] matplotlib não encontrado. Execute: pip install matplotlib")
    print("        Os resultados textuais/CSV ainda serão salvos.\n")

# ─── configuração ─────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
MEMORY_SRC  = SCRIPT_DIR / "memory_bound.c"
COMPUTE_SRC = SCRIPT_DIR / "compute_bound.c"
MEMORY_BIN  = SCRIPT_DIR / "memory_bound"
COMPUTE_BIN = SCRIPT_DIR / "compute_bound"
REPEATS     = 3
MAX_CPUS    = multiprocessing.cpu_count()

TIMESTAMP   = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_CSV     = SCRIPT_DIR / f"results_{TIMESTAMP}.csv"
OUT_JSON    = SCRIPT_DIR / f"results_{TIMESTAMP}.json"
OUT_PNG     = SCRIPT_DIR / f"benchmark_{TIMESTAMP}.png"

def thread_counts():
    counts, t = [1], 2
    while t <= MAX_CPUS:
        counts.append(t)
        t *= 2
    if MAX_CPUS not in counts:
        counts.append(MAX_CPUS)
    return counts

THREADS = thread_counts()

# ─── info do sistema ──────────────────────────────────────────────────────────
def system_info() -> dict:
    info = {
        "os":          platform.system(),
        "os_version":  platform.version(),
        "machine":     platform.machine(),
        "cpu_threads": MAX_CPUS,
        "timestamp":   TIMESTAMP,
    }
    # tenta ler /proc/cpuinfo no Linux
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    info["cpu_model"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        info["cpu_model"] = platform.processor() or "desconhecido"
    return info

# ─── compilação ───────────────────────────────────────────────────────────────
def compile_programs():
    print("=== Compilando programas C ===")
    cmds = [
        (["gcc", "-O2", "-fopenmp", str(MEMORY_SRC), "-o", str(MEMORY_BIN)],
         "memory_bound"),
        (["gcc", "-O2", "-fopenmp", str(COMPUTE_SRC), "-o", str(COMPUTE_BIN), "-lm"],
         "compute_bound"),
    ]
    for cmd, name in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERRO] Falha ao compilar {name}:\n{result.stderr}")
            sys.exit(1)
        print(f"  ✓ {name} compilado")
    print()

# ─── execução e coleta ────────────────────────────────────────────────────────
def parse_result(output: str) -> dict | None:
    m = re.search(r"RESULT\s+threads=(\d+)\s+time=([\d.]+)\s+(\w+)=([\d.]+)", output)
    if not m:
        return None
    return {
        "threads": int(m.group(1)),
        "time":    float(m.group(2)),
        m.group(3): float(m.group(4)),
    }

def run_binary(binary: Path, threads: int) -> dict | None:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    runs = []
    for _ in range(REPEATS):
        r = subprocess.run([str(binary), str(threads)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            print(f"[ERRO] {binary.name} threads={threads}: {r.stderr.strip()}")
            return None
        parsed = parse_result(r.stdout)
        if parsed:
            runs.append(parsed)
    if not runs:
        return None
    runs.sort(key=lambda x: x["time"])
    median = runs[len(runs) // 2]
    # guarda também min/max para o JSON
    median["time_min"] = runs[0]["time"]
    median["time_max"] = runs[-1]["time"]
    return median

def collect_data():
    print("=== Executando benchmarks ===")
    print(f"  CPUs lógicas: {MAX_CPUS}")
    print(f"  Threads testadas: {THREADS}")
    print(f"  Repetições por config: {REPEATS} (usa mediana)\n")

    mem_data, cpu_data = [], []

    for t in THREADS:
        print(f"  Threads = {t}")
        r = run_binary(MEMORY_BIN, t)
        if r:
            mem_data.append(r)
            print(f"    memory_bound  → {r['time']:.4f}s  |  {r.get('bandwidth_gbs', 0):.2f} GB/s")

        r = run_binary(COMPUTE_BIN, t)
        if r:
            cpu_data.append(r)
            print(f"    compute_bound → {r['time']:.4f}s  |  {r.get('gflops', 0):.3f} GFLOPS")

    print()
    return mem_data, cpu_data

# ─── exportar CSV ─────────────────────────────────────────────────────────────
def save_csv(mem_data, cpu_data, sysinfo):
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)

        # cabeçalho com info do sistema
        writer.writerow(["# Benchmark Memory-Bound vs Compute-Bound"])
        writer.writerow(["# CPU", sysinfo.get("cpu_model", "?")])
        writer.writerow(["# CPUs lógicas", sysinfo["cpu_threads"]])
        writer.writerow(["# Data/hora", sysinfo["timestamp"]])
        writer.writerow([])

        # memory-bound
        writer.writerow(["=== MEMORY-BOUND ==="])
        writer.writerow(["threads", "time_s", "time_min_s", "time_max_s",
                         "bandwidth_gbs", "speedup", "efficiency_pct"])
        t1 = mem_data[0]["time"] if mem_data else 1
        for d in mem_data:
            sp  = t1 / d["time"]
            eff = sp / d["threads"] * 100
            writer.writerow([
                d["threads"], f"{d['time']:.6f}",
                f"{d.get('time_min', d['time']):.6f}",
                f"{d.get('time_max', d['time']):.6f}",
                f"{d.get('bandwidth_gbs', 0):.4f}",
                f"{sp:.4f}", f"{eff:.2f}",
            ])

        writer.writerow([])

        # compute-bound
        writer.writerow(["=== COMPUTE-BOUND ==="])
        writer.writerow(["threads", "time_s", "time_min_s", "time_max_s",
                         "gflops", "speedup", "efficiency_pct"])
        t1 = cpu_data[0]["time"] if cpu_data else 1
        for d in cpu_data:
            sp  = t1 / d["time"]
            eff = sp / d["threads"] * 100
            writer.writerow([
                d["threads"], f"{d['time']:.6f}",
                f"{d.get('time_min', d['time']):.6f}",
                f"{d.get('time_max', d['time']):.6f}",
                f"{d.get('gflops', 0):.6f}",
                f"{sp:.4f}", f"{eff:.2f}",
            ])

    print(f"[CSV salvo em: {OUT_CSV}]")

# ─── exportar JSON ────────────────────────────────────────────────────────────
def save_json(mem_data, cpu_data, sysinfo):
    def enrich(data, t1_key):
        t1 = data[0]["time"] if data else 1
        out = []
        for d in data:
            sp  = t1 / d["time"]
            eff = sp / d["threads"] * 100
            out.append({**d, "speedup": round(sp, 4), "efficiency_pct": round(eff, 2)})
        return out

    payload = {
        "system":       sysinfo,
        "memory_bound": enrich(mem_data, "time"),
        "compute_bound": enrich(cpu_data, "time"),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[JSON salvo em: {OUT_JSON}]")

# ─── análise textual ──────────────────────────────────────────────────────────
def print_analysis(mem_data, cpu_data):
    print("=" * 60)
    print("ANÁLISE: Memory-Bound")
    print("=" * 60)
    if mem_data:
        t1 = mem_data[0]["time"]
        print(f"{'Threads':>8} {'Tempo(s)':>10} {'Speedup':>8} {'BW(GB/s)':>10} {'Efic.%':>8}")
        print("-" * 50)
        for d in mem_data:
            sp  = t1 / d["time"]
            eff = sp / d["threads"] * 100
            print(f"{d['threads']:>8} {d['time']:>10.4f} {sp:>8.2f}x "
                  f"{d.get('bandwidth_gbs',0):>10.2f} {eff:>7.1f}%")

    print()
    print("=" * 60)
    print("ANÁLISE: Compute-Bound")
    print("=" * 60)
    if cpu_data:
        t1 = cpu_data[0]["time"]
        print(f"{'Threads':>8} {'Tempo(s)':>10} {'Speedup':>8} {'GFLOPS':>8} {'Efic.%':>8}")
        print("-" * 46)
        for d in cpu_data:
            sp  = t1 / d["time"]
            eff = sp / d["threads"] * 100
            print(f"{d['threads']:>8} {d['time']:>10.4f} {sp:>8.2f}x "
                  f"{d.get('gflops',0):>8.3f} {eff:>7.1f}%")
    print()

# ─── gráficos ─────────────────────────────────────────────────────────────────
def plot_results(mem_data, cpu_data, sysinfo):
    if not HAS_MATPLOTLIB:
        return

    threads_m  = [d["threads"] for d in mem_data]
    times_m    = [d["time"]    for d in mem_data]
    bw_m       = [d.get("bandwidth_gbs", 0) for d in mem_data]
    speedup_m  = [mem_data[0]["time"] / t for t in times_m]
    eff_m      = [s / t * 100 for s, t in zip(speedup_m, threads_m)]

    threads_c  = [d["threads"] for d in cpu_data]
    times_c    = [d["time"]    for d in cpu_data]
    gflops_c   = [d.get("gflops", 0) for d in cpu_data]
    speedup_c  = [cpu_data[0]["time"] / t for t in times_c]
    eff_c      = [s / t * 100 for s, t in zip(speedup_c, threads_c)]

    ideal_x = list(range(1, max(THREADS) + 1))
    ideal_y = ideal_x

    cpu_model = sysinfo.get("cpu_model", "")
    title = (f"Memory-Bound vs Compute-Bound — OpenMP\n"
             f"{cpu_model}  |  {MAX_CPUS} threads lógicos  |  {TIMESTAMP}")

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(title, fontsize=11, fontweight="bold")
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.48, wspace=0.35)

    # 1. Tempo
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(threads_m, times_m, "bo-", label="Memory-bound", lw=2, ms=7)
    ax1.plot(threads_c, times_c, "rs-", label="Compute-bound", lw=2, ms=7)
    ax1.set_xlabel("Threads"); ax1.set_ylabel("Tempo (s)")
    ax1.set_title("Tempo de Execução")
    ax1.legend(); ax1.grid(True, alpha=0.3); ax1.set_xscale("log", base=2)

    # 2. Speedup
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(ideal_x, ideal_y, "k--", label="Ideal", alpha=0.45)
    ax2.plot(threads_m, speedup_m, "bo-", label="Memory-bound", lw=2, ms=7)
    ax2.plot(threads_c, speedup_c, "rs-", label="Compute-bound", lw=2, ms=7)
    ax2.axvline(x=MAX_CPUS // 2, color="gray", ls=":", alpha=0.7,
                label=f"~{MAX_CPUS//2} núcleos físicos")
    ax2.set_xlabel("Threads"); ax2.set_ylabel("Speedup (T₁/Tₙ)")
    ax2.set_title("Speedup vs Ideal")
    ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3); ax2.set_xscale("log", base=2)

    # 3. Eficiência
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(threads_m, eff_m, "bo-", label="Memory-bound", lw=2, ms=7)
    ax3.plot(threads_c, eff_c, "rs-", label="Compute-bound", lw=2, ms=7)
    ax3.axhline(y=100, color="k", ls="--", alpha=0.35)
    ax3.set_xlabel("Threads"); ax3.set_ylabel("Eficiência (%)")
    ax3.set_title("Eficiência Paralela (Sₙ/n × 100%)")
    ax3.legend(); ax3.grid(True, alpha=0.3)
    ax3.set_xscale("log", base=2); ax3.set_ylim(0, 115)

    # 4. Banda de memória
    ax4 = fig.add_subplot(gs[1, 0])
    colors_m = ["steelblue" if t <= MAX_CPUS // 2 else "orange" for t in threads_m]
    bars = ax4.bar([str(t) for t in threads_m], bw_m, color=colors_m)
    ax4.set_xlabel("Threads"); ax4.set_ylabel("GB/s")
    ax4.set_title("Memory-Bound: Largura de Banda\n(azul=físicos, laranja=SMT)")
    ax4.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, bw_m):
        ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    # 5. GFLOPS
    ax5 = fig.add_subplot(gs[1, 1])
    colors_c = ["tomato" if t <= MAX_CPUS // 2 else "salmon" for t in threads_c]
    bars = ax5.bar([str(t) for t in threads_c], gflops_c, color=colors_c)
    ax5.set_xlabel("Threads"); ax5.set_ylabel("GFLOPS")
    ax5.set_title("Compute-Bound: GFLOPS\n(vermelho=físicos, rosa=SMT)")
    ax5.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, gflops_c):
        ax5.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=8)

    # 6. Legenda de métricas
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")
    lines = [
        "Arquivos gerados:",
        f"  {OUT_CSV.name}",
        f"  {OUT_JSON.name}",
        f"  {OUT_PNG.name}",
        "",
        "Métricas por tipo:",
        "",
        "MEMORY-BOUND",
        "  Gargalo: barramento RAM",
        "  Métrica: GB/s",
        "  SMT: pouco ganho",
        "",
        "COMPUTE-BOUND",
        "  Gargalo: FPU/ALU",
        "  Métrica: GFLOPS",
        "  SMT: pode causar contenção",
    ]
    ax6.text(0.05, 0.97, "\n".join(lines), transform=ax6.transAxes,
             fontsize=9, va="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"[PNG salvo em: {OUT_PNG}]")
    plt.show()

# ─── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    compile_programs()
    sysinfo = system_info()
    print(f"=== Sistema: {sysinfo.get('cpu_model','?')} | {MAX_CPUS} CPUs lógicas ===\n")

    mem_data, cpu_data = collect_data()
    print_analysis(mem_data, cpu_data)

    save_csv(mem_data, cpu_data, sysinfo)
    save_json(mem_data, cpu_data, sysinfo)

    if HAS_MATPLOTLIB:
        plot_results(mem_data, cpu_data, sysinfo)
    else:
        print("[Para gerar gráficos]: pip install matplotlib && python3 benchmark.py")

    print(f"\nArquivos gerados em: {SCRIPT_DIR}")
    print(f"  {OUT_CSV.name}")
    print(f"  {OUT_JSON.name}")
    if HAS_MATPLOTLIB:
        print(f"  {OUT_PNG.name}")
