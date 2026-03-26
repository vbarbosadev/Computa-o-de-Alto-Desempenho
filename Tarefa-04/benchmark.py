#!/usr/bin/env python3
"""
Benchmark: Memory-Bound vs Compute-Bound com OpenMP
Compila os programas C, executa com diferentes contagens de threads,
coleta métricas e gera gráficos comparativos.
"""

import subprocess
import os
import re
import sys
import multiprocessing
from pathlib import Path

# ─── dependência opcional ────────────────────────────────────────────────────
try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[AVISO] matplotlib não encontrado. Execute: pip install matplotlib")
    print("        Os resultados textuais ainda serão exibidos.\n")

# ─── configuração ─────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
MEMORY_SRC   = SCRIPT_DIR / "memory_bound.c"
COMPUTE_SRC  = SCRIPT_DIR / "compute_bound.c"
MEMORY_BIN   = SCRIPT_DIR / "memory_bound"
COMPUTE_BIN  = SCRIPT_DIR / "compute_bound"
REPEATS      = 3          # repetições por configuração (usa a mediana)
MAX_CPUS     = multiprocessing.cpu_count()

# threads a testar: potências de 2 até MAX_CPUS, mais MAX_CPUS se não for pot. de 2
def thread_counts():
    counts, t = [1], 2
    while t <= MAX_CPUS:
        counts.append(t)
        t *= 2
    if MAX_CPUS not in counts:
        counts.append(MAX_CPUS)
    return counts

THREADS = thread_counts()

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
    """Extrai campos do formato: RESULT threads=N time=T key=V"""
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
    results = []
    for _ in range(REPEATS):
        r = subprocess.run([str(binary), str(threads)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            print(f"[ERRO] {binary.name} com {threads} threads: {r.stderr.strip()}")
            return None
        parsed = parse_result(r.stdout)
        if parsed:
            results.append(parsed)
    if not results:
        return None
    # mediana do tempo
    results.sort(key=lambda x: x["time"])
    return results[len(results) // 2]

def collect_data():
    print("=== Executando benchmarks ===")
    print(f"  CPUs disponíveis: {MAX_CPUS}")
    print(f"  Threads testadas: {THREADS}")
    print(f"  Repetições por config: {REPEATS}\n")

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

# ─── análise textual ──────────────────────────────────────────────────────────
def print_analysis(mem_data, cpu_data):
    def speedup(data):
        t1 = next((d["time"] for d in data if d["threads"] == 1), None)
        if t1 is None:
            return []
        return [(d["threads"], t1 / d["time"]) for d in data]

    print("=" * 60)
    print("ANÁLISE: Memory-Bound")
    print("=" * 60)
    if mem_data:
        t1 = mem_data[0]["time"]
        print(f"{'Threads':>8} {'Tempo(s)':>10} {'Speedup':>8} {'BW(GB/s)':>10} {'Efic.%':>8}")
        print("-" * 50)
        for d in mem_data:
            sp = t1 / d["time"]
            eff = sp / d["threads"] * 100
            print(f"{d['threads']:>8} {d['time']:>10.4f} {sp:>8.2f}x {d.get('bandwidth_gbs',0):>10.2f} {eff:>7.1f}%")

    print()
    print("=" * 60)
    print("ANÁLISE: Compute-Bound")
    print("=" * 60)
    if cpu_data:
        t1 = cpu_data[0]["time"]
        print(f"{'Threads':>8} {'Tempo(s)':>10} {'Speedup':>8} {'GFLOPS':>8} {'Efic.%':>8}")
        print("-" * 46)
        for d in cpu_data:
            sp = t1 / d["time"]
            eff = sp / d["threads"] * 100
            print(f"{d['threads']:>8} {d['time']:>10.4f} {sp:>8.2f}x {d.get('gflops',0):>8.3f} {eff:>7.1f}%")

    print()
    print("=" * 60)
    print("REFLEXÃO")
    print("=" * 60)
    print("""
Memory-Bound (soma de vetores):
  • Métrica principal: Largura de banda de memória (GB/s)
  • O gargalo é a velocidade de leitura/escrita da RAM.
  • Com múltiplos núcleos físicos, cada núcleo possui seu próprio
    caminho para a memória, podendo agregar banda → speedup real.
  • Hyperthreading (SMT) pouco ajuda: os 2 threads lógicos de um
    mesmo núcleo físico compartilham as unidades de memória cache/bus,
    não aumentando a banda disponível.
  • Saturação do barramento é atingida rapidamente; adicionar mais
    threads além desse ponto não melhora (e pode piorar por overhead).

Compute-Bound (sin/cos intensivo):
  • Métrica principal: GFLOPS (operações de ponto flutuante / segundo)
  • O gargalo é a capacidade de cálculo das FPUs do processador.
  • Cada núcleo físico adicional agrega poder de cálculo → speedup
    quase linear até atingir todos os núcleos físicos.
  • Hyperthreading pode ATRAPALHAR: dois threads lógicos competem pelas
    mesmas unidades de execução (FPU/ALU) do núcleo físico, causando
    contenção e reduzindo o speedup por thread adicional.
  • A eficiência costuma cair abruptamente ao cruzar o limite de
    núcleos físicos (ex.: 8 físicos → 16 lógicos).

Métricas recomendadas:
  - Memory-Bound: GB/s, tempo de execução (padrão: STREAM benchmark)
  - Compute-Bound: GFLOPS, speedup, eficiência paralela (Sn/n)
""")

# ─── gráficos ─────────────────────────────────────────────────────────────────
def plot_results(mem_data, cpu_data):
    if not HAS_MATPLOTLIB:
        return

    threads_m   = [d["threads"] for d in mem_data]
    times_m     = [d["time"]    for d in mem_data]
    bw_m        = [d.get("bandwidth_gbs", 0) for d in mem_data]
    speedup_m   = [mem_data[0]["time"] / t for t in times_m]
    eff_m       = [s / t * 100 for s, t in zip(speedup_m, threads_m)]

    threads_c   = [d["threads"] for d in cpu_data]
    times_c     = [d["time"]    for d in cpu_data]
    gflops_c    = [d.get("gflops", 0) for d in cpu_data]
    speedup_c   = [cpu_data[0]["time"] / t for t in times_c]
    eff_c       = [s / t * 100 for s, t in zip(speedup_c, threads_c)]

    # speedup ideal
    ideal_x = list(range(1, max(THREADS) + 1))
    ideal_y = ideal_x  # speedup = threads

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("Memory-Bound vs Compute-Bound — Análise de Paralelismo OpenMP",
                 fontsize=14, fontweight="bold")
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ── 1. Tempo de execução ──────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(threads_m, times_m, "bo-", label="Memory-bound", linewidth=2, markersize=7)
    ax1.plot(threads_c, times_c, "rs-", label="Compute-bound", linewidth=2, markersize=7)
    ax1.set_xlabel("Número de Threads")
    ax1.set_ylabel("Tempo (s)")
    ax1.set_title("Tempo de Execução")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale("log", base=2)

    # ── 2. Speedup ────────────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(ideal_x, ideal_y, "k--", label="Ideal (linear)", alpha=0.5)
    ax2.plot(threads_m, speedup_m, "bo-", label="Memory-bound", linewidth=2, markersize=7)
    ax2.plot(threads_c, speedup_c, "rs-", label="Compute-bound", linewidth=2, markersize=7)
    ax2.axvline(x=MAX_CPUS // 2, color="gray", linestyle=":", alpha=0.7,
                label=f"Núcleos físicos (~{MAX_CPUS//2})")
    ax2.set_xlabel("Número de Threads")
    ax2.set_ylabel("Speedup (S = T₁ / Tₙ)")
    ax2.set_title("Speedup vs Ideal")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.set_xscale("log", base=2)

    # ── 3. Eficiência paralela ────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(threads_m, eff_m, "bo-", label="Memory-bound", linewidth=2, markersize=7)
    ax3.plot(threads_c, eff_c, "rs-", label="Compute-bound", linewidth=2, markersize=7)
    ax3.axhline(y=100, color="k", linestyle="--", alpha=0.4, label="100%")
    ax3.set_xlabel("Número de Threads")
    ax3.set_ylabel("Eficiência (%)")
    ax3.set_title("Eficiência Paralela (Sₙ/n × 100%)")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_xscale("log", base=2)
    ax3.set_ylim(0, 110)

    # ── 4. Largura de banda (memory-bound) ───────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    bars = ax4.bar([str(t) for t in threads_m], bw_m,
                   color=["steelblue" if t <= MAX_CPUS // 2 else "orange"
                          for t in threads_m])
    ax4.set_xlabel("Threads")
    ax4.set_ylabel("Largura de Banda (GB/s)")
    ax4.set_title("Memory-Bound: Banda de Memória\n(azul=físicos, laranja=SMT)")
    ax4.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, bw_m):
        ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    # ── 5. GFLOPS (compute-bound) ─────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    bars = ax5.bar([str(t) for t in threads_c], gflops_c,
                   color=["tomato" if t <= MAX_CPUS // 2 else "salmon"
                          for t in threads_c])
    ax5.set_xlabel("Threads")
    ax5.set_ylabel("GFLOPS")
    ax5.set_title("Compute-Bound: GFLOPS\n(vermelho=físicos, rosa=SMT)")
    ax5.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, gflops_c):
        ax5.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=8)

    # ── 6. Comparativo de eficiência em texto ─────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")
    lines = [
        "Métricas por tipo de programa",
        "",
        "MEMORY-BOUND",
        "  Gargalo: barramento RAM",
        "  Métrica: GB/s (largura de banda)",
        "  SMT: pouco ganho (mesma banda)",
        "  Ideal: núcleos físicos distintos",
        "",
        "COMPUTE-BOUND",
        "  Gargalo: unidades FPU/ALU",
        "  Métrica: GFLOPS / speedup",
        "  SMT: pode causar contenção",
        "  Ideal: escala com núcleos físicos",
        "",
        f"Sistema: {MAX_CPUS} threads lógicos",
    ]
    ax6.text(0.05, 0.95, "\n".join(lines), transform=ax6.transAxes,
             fontsize=9, verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    out = SCRIPT_DIR / "benchmark_results.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[Gráfico salvo em: {out}]")
    plt.show()

# ─── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    compile_programs()
    mem_data, cpu_data = collect_data()
    print_analysis(mem_data, cpu_data)
    if HAS_MATPLOTLIB:
        plot_results(mem_data, cpu_data)
    else:
        print("[Para gerar gráficos]: pip install matplotlib && python benchmark.py")
