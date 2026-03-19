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
    laco3 = df[df["laco"] == "laco3"].set_index("otimizacao")["tempo"]

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
    csv = os.path.join(DADOS_DIR, "tarefa3.csv")
    if not os.path.exists(csv):
        print("[Tarefa 3] arquivo não encontrado, pulando.")
        return

    df = pd.read_csv(csv)

    # erro pode vir como string científica ("0.00e+00") — converter
    df["erro"] = pd.to_numeric(df["erro"], errors="coerce")
    # substituir zeros por valor mínimo representável para escala log
    df["erro_plot"] = df["erro"].replace(0, 1e-16)

    print("\n=== Tarefa 3 — Gauss-Legendre: convergência para π ===")
    print(df[["iteracoes", "segundos", "pi_aprox", "erro"]].to_string(index=False))

    # ── Gráfico 5: Erro × iterações ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(df["iteracoes"], df["erro_plot"], marker="o", color="darkorange", label="Erro absoluto")
    ax.axhline(1e-15, color="blue", linestyle="--", linewidth=1.2, label="Limite precisão double (~1e-15)")

    ax.set_yscale("log")
    ax.set_xlabel("Número de iterações")
    ax.set_ylabel("Erro absoluto |π_aprox − π|  (escala log)")
    ax.set_title("Gauss-Legendre — Convergência para π")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.tight_layout()
    salvar(fig, "tarefa3_erro.png")

    # ── Gráfico 6: Tempo × iterações ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df["iteracoes"].astype(str), df["segundos"], color="cadetblue")

    ax.set_xlabel("Número de iterações")
    ax.set_ylabel("Tempo (s)")
    ax.set_title("Gauss-Legendre — Tempo por número de iterações")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    salvar(fig, "tarefa3_tempo.png")

    convergiu = df[df["erro"] < 1e-15]
    print(f"\n  Converge abaixo de 1e-15 a partir de: {convergiu['iteracoes'].min() if not convergiu.empty else 'nunca'} iterações")
    print(f"  Tempo total acumulado: {df['segundos'].sum():.6f} s")


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Analisando dados das tarefas...\n")
    analise_tarefa1()
    analise_tarefa2()
    analise_tarefa3()
    print(f"\nGráficos salvos em: {os.path.abspath(GRAFICOS_DIR)}")
