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
    print("\n=== Tarefa 2 — ILP: laços com e sem dependência ===")
    print(df.to_string(index=False))

    otimizacoes = ["O0", "O2", "O3"]
    df["otimizacao"] = pd.Categorical(df["otimizacao"], categories=otimizacoes, ordered=True)
    df = df.sort_values(["otimizacao", "laco"])

    laco2 = df[df["laco"] == "laco2"].set_index("otimizacao")["tempo"]
    laco3 = df[df["laco"] == "laco3_2"].set_index("otimizacao")["tempo"]

    x = np.arange(len(otimizacoes))
    width = 0.35

    # ── Gráfico 3: Barras agrupadas ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))

    bars2 = ax.bar(x - width / 2, laco2.reindex(otimizacoes), width, label="Laço 2 (com dependência)",    color="tomato")
    bars3 = ax.bar(x + width / 2, laco3.reindex(otimizacoes), width, label="Laço 3 (sem dependência)", color="mediumseagreen")

    # Escala log se a diferença for grande
    max_t = df["tempo"].max()
    min_t = df["tempo"].min()
    if max_t / max(min_t, 1e-12) > 100:
        ax.set_yscale("log")
        ax.set_ylabel("Tempo (s) — escala log")
    else:
        ax.set_ylabel("Tempo (s)")

    ax.set_xticks(x)
    ax.set_xticklabels([f"-{o}" for o in otimizacoes])
    ax.set_xlabel("Nível de otimização")
    ax.set_title("ILP — Efeito das dependências e nível de otimização")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa2_barras.png")

    # ── Gráfico 4: Speedup por nível de otimização ───────────────────────────
    speedup = laco2.reindex(otimizacoes) / laco3.reindex(otimizacoes)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([f"-{o}" for o in otimizacoes], speedup, color="mediumpurple")
    ax.axhline(1.0, color="red", linestyle="--", linewidth=1.2, label="Speedup = 1")

    ax.set_xlabel("Nível de otimização")
    ax.set_ylabel("Speedup (tempo_laco2 / tempo_laco3)")
    ax.set_title("Ganho ao quebrar dependência de dados")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa2_speedup.png")

    print(f"\n  Speedup laco3 vs laco2:")
    for opt in otimizacoes:
        print(f"    -{opt}: {speedup.get(opt, float('nan')):.2f}x")


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

    print("\n=== Tarefa 3 — Leibniz: convergência para π ===")
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
    ax.set_ylabel("Erro absoluto |π_aprox − π|  (escala log)")
    ax.set_title("Leibniz — Convergência para π (sequencial)")
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
