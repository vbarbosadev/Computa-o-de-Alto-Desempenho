"""
Script de análise e comparação das Tarefas 1, 2 e 3.
Lê CSVs de dados/ e gera gráficos em analise/graficos/.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

DADOS_DIR = os.path.join(os.path.dirname(__file__), "..", "dados")
GRAFICOS_DIR = os.path.join(os.path.dirname(__file__), "graficos")

os.makedirs(GRAFICOS_DIR, exist_ok=True)


def salvar(fig, nome):
    caminho = os.path.join(GRAFICOS_DIR, nome)
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> salvo: {caminho}")


# ─── TAREFA 1 ────────────────────────────────────────────────────────────────

def analise_tarefa1():
    csv = os.path.join(DADOS_DIR, "tarefa1.csv")
    if not os.path.exists(csv):
        print("[Tarefa 1] arquivo não encontrado, pulando.")
        return

    df = pd.read_csv(csv)
    print("\n=== Tarefa 1 — MxV: acesso linha vs coluna ===")
    print(df.to_string(index=False))

    # ── Gráfico 1: Tempo × N ─────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(df["N"], df["tempo_linha"],  marker="o", label="Acesso por Linha (row-major)")
    ax.plot(df["N"], df["tempo_coluna"], marker="s", label="Acesso por Coluna (column-major)")

    # Ponto de maior divergência
    diff = (df["tempo_coluna"] - df["tempo_linha"]).abs()
    idx_div = diff.idxmax()
    n_div = df.loc[idx_div, "N"]
    t_div = df.loc[idx_div, "tempo_coluna"]
    ax.annotate(
        f"Divergência\nN={n_div}",
        xy=(n_div, t_div),
        xytext=(n_div * 0.75, t_div * 1.1),
        arrowprops=dict(arrowstyle="->", color="gray"),
        fontsize=8,
        color="gray",
    )

    ax.set_xlabel("N (tamanho da matriz)")
    ax.set_ylabel("Tempo (s)")
    ax.set_title("MxV — Impacto do padrão de acesso à cache")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa1_tempo.png")

    # ── Gráfico 2: Speedup × N ───────────────────────────────────────────────
    df["speedup"] = df["tempo_coluna"] / df["tempo_linha"]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df["N"].astype(str), df["speedup"], color="steelblue", width=0.5)
    ax.axhline(1.0, color="red", linestyle="--", linewidth=1.2, label="Speedup = 1 (equivalente)")

    ax.set_xlabel("N (tamanho da matriz)")
    ax.set_ylabel("Speedup (tempo_coluna / tempo_linha)")
    ax.set_title("MxV — Speedup do acesso por linha sobre acesso por coluna")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa1_speedup.png")

    # Resumo
    print(f"\n  Speedup máximo : {df['speedup'].max():.2f}x  (N={df.loc[df['speedup'].idxmax(), 'N']})")
    print(f"  Speedup mínimo : {df['speedup'].min():.2f}x  (N={df.loc[df['speedup'].idxmin(), 'N']})")


# ─── TAREFA 2 ────────────────────────────────────────────────────────────────

def analise_tarefa2():
    csv = os.path.join(DADOS_DIR, "tarefa2.csv")
    if not os.path.exists(csv):
        print("[Tarefa 2] arquivo não encontrado, pulando.")
        return

    df = pd.read_csv(csv)
    print("\n=== Tarefa 2 — ILP: loop unrolling ===")
    print(df.to_string(index=False))

    otimizacoes = ["O0", "O2", "O3"]
    lacos_ordem = ["laco_soma", "laco_unroll_2", "laco_unroll_4", "laco_unroll_8", "laco_unroll_12"]
    labels_lacos = ["soma\n(base)", "unroll×2", "unroll×4", "unroll×8", "unroll×12"]

    df["otimizacao"] = pd.Categorical(df["otimizacao"], categories=otimizacoes, ordered=True)
    df["laco"] = pd.Categorical(df["laco"], categories=lacos_ordem, ordered=True)
    df = df.sort_values(["otimizacao", "laco"])

    cores_opt = {"O0": "tomato", "O2": "steelblue", "O3": "mediumseagreen"}
    x = np.arange(len(lacos_ordem))
    n_opt = len(otimizacoes)
    width = 0.22

    # ── Gráfico 3: Barras agrupadas — tempo por laço para cada otimização ────
    fig, ax = plt.subplots(figsize=(11, 5))

    for i, opt in enumerate(otimizacoes):
        tempos = (
            df[df["otimizacao"] == opt]
            .set_index("laco")["tempo"]
            .reindex(lacos_ordem)
        )
        offset = (i - n_opt / 2 + 0.5) * width
        bars = ax.bar(x + offset, tempos, width, label=f"-{opt}", color=cores_opt[opt])
        for bar, val in zip(bars, tempos):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                        f"{val:.3f}", ha="center", va="bottom", fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(labels_lacos)
    ax.set_xlabel("Variante do laço")
    ax.set_ylabel("Tempo (s)")
    ax.set_title("ILP — Loop Unrolling: tempo por variante e nível de otimização")
    ax.legend(title="Otimização")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa2_barras.png")

    # ── Gráfico 4: Speedup como linha — tendência conforme fator de unrolling ─
    fig, ax = plt.subplots(figsize=(10, 5))

    unroll_fatores = [1, 2, 4, 8, 12]   # eixo X numérico para linha contínua

    for opt in otimizacoes:
        grupo = df[df["otimizacao"] == opt].set_index("laco")["tempo"].reindex(lacos_ordem)
        base = grupo["laco_soma"]
        speedup = (base / grupo).values
        ax.plot(unroll_fatores, speedup, marker="o", label=f"-{opt}", color=cores_opt[opt], linewidth=2)
        for fator, val in zip(unroll_fatores, speedup):
            if not np.isnan(val):
                ax.annotate(f"{val:.2f}x", xy=(fator, val),
                            xytext=(0, 6), textcoords="offset points",
                            ha="center", fontsize=8, color=cores_opt[opt])

    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.2, label="Speedup = 1 (base)")
    ax.set_xticks(unroll_fatores)
    ax.set_xticklabels(["base\n(×1)", "×2", "×4", "×8", "×12"])
    ax.set_xlabel("Fator de unrolling")
    ax.set_ylabel("Speedup (tempo_soma / tempo_variante)")
    ax.set_title("ILP — Speedup do loop unrolling em relação ao laço simples")
    ax.legend(title="Otimização")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa2_speedup.png")

    # Resumo
    print()
    for opt in otimizacoes:
        grupo = df[df["otimizacao"] == opt].set_index("laco")["tempo"].reindex(lacos_ordem)
        base = grupo["laco_soma"]
        melhor_laco = (base / grupo).idxmax()
        melhor_sp = (base / grupo).max()
        print(f"  -{opt}: melhor variante = {melhor_laco}  ({melhor_sp:.2f}x vs laco_soma)")


# ─── TAREFA 3 ────────────────────────────────────────────────────────────────

def analise_tarefa3():
    csv_seq = os.path.join(DADOS_DIR, "tarefa3_seq.csv")
    csv_omp = os.path.join(DADOS_DIR, "tarefa3_omp.csv")

    if not os.path.exists(csv_seq) or not os.path.exists(csv_omp):
        print("[Tarefa 3] arquivos não encontrados, pulando.")
        return

    seq = pd.read_csv(csv_seq)
    omp = pd.read_csv(csv_omp)

    seq["erro"] = pd.to_numeric(seq["erro"], errors="coerce")
    omp["erro"] = pd.to_numeric(omp["erro"], errors="coerce")

    print("\n=== Tarefa 3 -- Leibniz: convergencia para pi ===")
    print("\n-- Sequencial --")
    print(seq[["iteracoes", "segundos", "pi_aprox", "erro"]].to_string(index=False))
    print("\n-- Paralelo --")
    print(omp[["iteracoes", "threads", "segundos", "pi_aprox", "erro"]].to_string(index=False))

    # ── Gráfico 5: Erro × iterações (sequencial, escala log/log) ─────────────
    seq_plot = seq.copy()
    seq_plot["erro_plot"] = seq_plot["erro"].replace(0, 1e-17)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(seq_plot["iteracoes"], seq_plot["erro_plot"],
            marker="o", color="darkorange", label="Erro absoluto")
    ax.axhline(1e-7, color="blue", linestyle="--", linewidth=1, label="1e-7 (7 casas)")
    ax.axhline(1e-15, color="green", linestyle="--", linewidth=1, label="Limite double (~1e-15)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Número de termos (escala log)")
    ax.set_ylabel("Erro absoluto |pi_aprox - pi|  (escala log)")
    ax.set_title("Leibniz -- Convergencia para pi (sequencial)")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.tight_layout()
    salvar(fig, "tarefa3_erro.png")

    # ── Gráfico 6: Tempo × iterações (sequencial, escala log) ────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(seq["iteracoes"], seq["segundos"],
            marker="s", color="cadetblue", label="Tempo sequencial")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Número de termos (escala log)")
    ax.set_ylabel("Tempo (s)  (escala log)")
    ax.set_title("Leibniz — Crescimento do tempo de execução (sequencial)")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.tight_layout()
    salvar(fig, "tarefa3_tempo.png")

    # ── Gráfico 7: Speedup × threads (paralelo) ───────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = plt.cm.tab10.colors

    for idx, (n_it, grupo) in enumerate(omp.groupby("iteracoes")):
        grupo = grupo.sort_values("threads")
        t1 = grupo.loc[grupo["threads"] == 1, "segundos"].values
        if len(t1) == 0:
            continue
        grupo = grupo.copy()
        grupo["speedup"] = t1[0] / grupo["segundos"]
        label = f"{n_it:,} termos"
        ax.plot(grupo["threads"], grupo["speedup"],
                marker="o", label=label, color=colors[idx % len(colors)])

    max_threads = omp["threads"].max()
    ax.plot([1, max_threads], [1, max_threads],
            linestyle="--", color="gray", linewidth=1, label="Speedup ideal")

    ax.set_xlabel("Número de threads")
    ax.set_ylabel("Speedup (T₁ / Tₙ)")
    ax.set_title("Leibniz — Speedup com OpenMP")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    salvar(fig, "tarefa3_speedup.png")

    # ── Gráfico 8: Tempo × threads para cada carga (paralelo) ────────────────
    fig, ax = plt.subplots(figsize=(9, 5))

    for idx, (n_it, grupo) in enumerate(omp.groupby("iteracoes")):
        grupo = grupo.sort_values("threads")
        label = f"{n_it:,} termos"
        ax.plot(grupo["threads"], grupo["segundos"],
                marker="s", label=label, color=colors[idx % len(colors)])

    ax.set_xlabel("Número de threads")
    ax.set_ylabel("Tempo (s)")
    ax.set_title("Leibniz — Tempo de execução por número de threads")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    salvar(fig, "tarefa3_tempo_omp.png")

    # Resumo
    melhor = omp.loc[omp["segundos"].idxmin()]
    print(f"\n  Melhor tempo paralelo: {melhor['segundos']:.4f}s"
          f"  ({int(melhor['threads'])} threads, {int(melhor['iteracoes']):,} termos)")

    for n_it, grupo in omp.groupby("iteracoes"):
        t1 = grupo.loc[grupo["threads"] == 1, "segundos"].values
        tmax = grupo.loc[grupo["threads"] == grupo["threads"].max(), "segundos"].values
        if len(t1) and len(tmax):
            print(f"  Speedup máximo ({n_it:,} termos): {t1[0]/tmax[0]:.2f}x"
                  f"  ({int(grupo['threads'].max())} threads)")


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Analisando dados das tarefas...\n")
    analise_tarefa1()
    analise_tarefa2()
    analise_tarefa3()
    print(f"\nGráficos salvos em: {os.path.abspath(GRAFICOS_DIR)}")
