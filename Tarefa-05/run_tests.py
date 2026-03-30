import subprocess
import re
import statistics
import matplotlib.pyplot as plt

PROGRAMS = [
    ("seq",    "primo_sequencial.c",      ["-fopenmp"], "Sequencial"),
    ("par_rc", "primos_parallel.c",       ["-fopenmp"], "Paralelo (Race Condition)"),
    ("par_at", "primos_parallel_atomic.c",["-fopenmp"], "Paralelo (Atomic)"),
]

def compile_code():
    print("Compilando arquivos C...")
    for exe, src, flags, _ in PROGRAMS:
        subprocess.run(["gcc", "-o", exe, src] + flags, check=True)
        print(f"  {src} -> {exe}")
    print("Compilacao concluida com sucesso.\n")

def run_test(executable, label, num_runs=10):
    times = []
    counts = []
    print(f"Executando '{label}' {num_runs} vezes...")
    for i in range(num_runs):
        result = subprocess.run([f"./{executable}"], capture_output=True, text=True)

        match_time  = re.search(r"Tempo de execucao:\s*([\d\.]+)\s*segundos", result.stdout)
        match_count = re.search(r"Total de numeros primos entre 1 e \d+:\s*(\d+)", result.stdout)

        if match_time and match_count:
            t = float(match_time.group(1))
            c = int(match_count.group(1))
            times.append(t)
            counts.append(c)
            print(f"  [Rodada {i+1}] Tempo: {t:.4f}s | Primos encontrados: {c}")
        else:
            print(f"  [Rodada {i+1}] Erro ao ler a saida:\n{result.stdout}")

    if times:
        print(f"-> Media '{label}': {statistics.mean(times):.4f}s | "
              f"Contagem (min/max): {min(counts)}/{max(counts)}\n")
    return times, counts

def main():
    try:
        compile_code()
    except Exception as e:
        print(f"Falha ao compilar: {e}")
        return

    runs = 10
    results = {}
    for exe, _, _, label in PROGRAMS:
        times, counts = run_test(exe, label, runs)
        results[label] = {"times": times, "counts": counts}

    # --- Comparacao de contagens ---
    print("=" * 55)
    print("COMPARACAO DE RESULTADOS (contagem de primos)")
    print("=" * 55)
    ref_label, ref_data = list(results.items())[0]
    ref_count = statistics.mode(ref_data["counts"])
    print(f"Referencia ({ref_label}): {ref_count} primos\n")
    for label, data in results.items():
        counts = data["counts"]
        unique = set(counts)
        correto = all(c == ref_count for c in counts)
        status = "OK" if correto else "INCORRETO (race condition detectada!)"
        print(f"  {label}:")
        print(f"    Contagens obtidas: {sorted(unique)}")
        print(f"    Status: {status}")
    print()

    # --- Grafico de tempos ---
    lbl_seq = "Sequencial"
    lbl_rc  = "Paralelo (Race Condition)"
    lbl_at  = "Paralelo (Atomic)"

    mean_seq = statistics.mean(results[lbl_seq]["times"])
    mean_rc  = statistics.mean(results[lbl_rc]["times"])
    mean_at  = statistics.mean(results[lbl_at]["times"])

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    def bar_comparison(ax, label_a, mean_a, color_a, label_b, mean_b, color_b, title):
        bars = ax.bar([label_a, label_b], [mean_a, mean_b], color=[color_a, color_b])
        ax.set_ylabel("Tempo Medio de Execucao (segundos)")
        ax.set_title(title)
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2,
                    yval + yval * 0.02,
                    f"{yval:.4f}s", ha="center", va="bottom", fontweight="bold")
        speedup = mean_a / mean_b if mean_b < mean_a else mean_b / mean_a
        faster  = label_b if mean_b < mean_a else label_a
        ax.text(0.5, 0.85, f"Speedup: {speedup:.2f}x\n({faster} mais rapido)",
                transform=ax.transAxes, ha="center", fontsize=10,
                bbox=dict(facecolor="white", alpha=0.7))

    # Subplot 1: Sequencial vs Race Condition
    bar_comparison(axes[0],
                   lbl_seq, mean_seq, "#3498db",
                   lbl_rc,  mean_rc,  "#e74c3c",
                   f"Sequencial vs Race Condition\n(Media de {runs} execucoes)")

    # Subplot 2: Paralelo Atomic vs Race Condition
    bar_comparison(axes[1],
                   lbl_rc, mean_rc, "#e74c3c",
                   lbl_at, mean_at, "#2ecc71",
                   f"Race Condition vs Atomic\n(Media de {runs} execucoes)")

    # Subplot 3: contagem de primos por rodada
    colors = ["#3498db", "#e74c3c", "#2ecc71"]
    for (label, data), color in zip(results.items(), colors):
        axes[2].plot(range(1, runs + 1), data["counts"],
                     marker="o", label=label, color=color)
    axes[2].set_xlabel("Rodada")
    axes[2].set_ylabel("Primos encontrados")
    axes[2].set_title("Contagem de Primos por Rodada")
    axes[2].legend(fontsize=8)
    axes[2].yaxis.get_major_formatter().set_useOffset(False)

    plt.tight_layout()
    plt.savefig("comparacao_tempo.png", format="png", dpi=300)
    print("Grafico salvo como 'comparacao_tempo.png' com sucesso!")

if __name__ == "__main__":
    main()
