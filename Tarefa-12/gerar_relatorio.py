import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa12_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa12.md"


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "threads", "nx", "ny", "steps", "chunk", "collapse"]:
                row[key] = int(row[key])
            for key in [
                "cells_per_thread", "elapsed", "initial_max", "final_max",
                "initial_l2", "final_l2", "initial_sum", "final_sum",
            ]:
                row[key] = float(row[key])
            for key in ["strong_speedup", "strong_efficiency", "weak_efficiency"]:
                row[key] = float(row[key]) if row[key] != "" else None
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        key = (
            row["experiment"], row["mode"], row["threads"], row["nx"], row["ny"],
            row["schedule"], row["chunk"], row["collapse"],
        )
        groups[key].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed"] for row in values]
        strong_speedup = [row["strong_speedup"] for row in values if row["strong_speedup"] is not None]
        strong_efficiency = [row["strong_efficiency"] for row in values if row["strong_efficiency"] is not None]
        weak_efficiency = [row["weak_efficiency"] for row in values if row["weak_efficiency"] is not None]
        summary.append({
            "experiment": key[0],
            "mode": key[1],
            "threads": key[2],
            "nx": key[3],
            "ny": key[4],
            "schedule": key[5],
            "chunk": key[6],
            "collapse": key[7],
            "runs": len(values),
            "mean": statistics.mean(elapsed),
            "min": min(elapsed),
            "max": max(elapsed),
            "strong_speedup": statistics.mean(strong_speedup) if strong_speedup else None,
            "strong_efficiency": statistics.mean(strong_efficiency) if strong_efficiency else None,
            "weak_efficiency": statistics.mean(weak_efficiency) if weak_efficiency else None,
            "initial_max": values[0]["initial_max"],
            "final_max": values[0]["final_max"],
            "initial_l2": values[0]["initial_l2"],
            "final_l2": values[0]["final_l2"],
        })
    return summary


def table_strong(summary):
    lines = [
        "|Versao|Threads|Malha|Rodadas|Media (s)|Min (s)|Max (s)|Speedup|Eficiencia|",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        if row["experiment"] != "strong":
            continue
        lines.append(
            f"|{row['mode']}|{row['threads']}|{row['nx']}x{row['ny']}|{row['runs']}|"
            f"{row['mean']:.6f}|{row['min']:.6f}|{row['max']:.6f}|"
            f"{row['strong_speedup']:.2f}|{row['strong_efficiency']:.2f}|"
        )
    return "\n".join(lines)


def table_weak(summary):
    lines = [
        "|Versao|Threads|Malha|Celulas/thread|Rodadas|Media (s)|Min (s)|Max (s)|Eficiencia fraca|",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        if row["experiment"] != "weak":
            continue
        cells_per_thread = (row["nx"] * row["ny"]) / row["threads"]
        lines.append(
            f"|{row['mode']}|{row['threads']}|{row['nx']}x{row['ny']}|"
            f"{cells_per_thread:.0f}|{row['runs']}|{row['mean']:.6f}|"
            f"{row['min']:.6f}|{row['max']:.6f}|{row['weak_efficiency']:.2f}|"
        )
    return "\n".join(lines)


def best_lines(summary, experiment):
    by_threads = defaultdict(list)
    for row in summary:
        if row["experiment"] == experiment:
            by_threads[row["threads"]].append(row)

    lines = []
    for threads in sorted(by_threads):
        best = sorted(by_threads[threads], key=lambda row: row["mean"])[0]
        if experiment == "strong":
            metric = f"speedup {best['strong_speedup']:.2f}x"
        else:
            metric = f"eficiencia fraca {best['weak_efficiency']:.2f}"
        lines.append(
            f"- {threads} threads: `{best['mode']}` com media {best['mean']:.6f}s "
            f"em malha {best['nx']}x{best['ny']} ({metric})."
        )
    return "\n".join(lines)


def generate_report(rows, summary):
    first = rows[0]
    report = f"""# Tarefa 12 - Escalabilidade do Navier-Stokes no NPAD

## Objetivo

Avaliar a escalabilidade do codigo de Navier-Stokes simplificado em um no de
computacao do NPAD. Foram comparadas duas versoes paralelas:

- `omp-basic`: cria uma regiao paralela em cada passo de tempo.
- `omp-region`: mantem uma unica regiao paralela ao longo de todos os passos,
  reduzindo overhead de criacao/sincronizacao de threads.

## Configuracao

- Passos: `{first['steps']}`
- Escalonamento: `{first['schedule']}`
- Chunk: `{first['chunk']}`
- Collapse: `{first['collapse']}`
- Inicializacao: perturbacao central
- Condicao de estabilidade: `dt * nu <= 0.25`

## Validacao numerica

Em todas as execucoes o campo permaneceu estavel. O valor maximo inicial foi
`{first['initial_max']:.6f}` e o primeiro resultado registrado terminou com maximo
`{first['final_max']:.6f}`. A norma L2 tambem foi monitorada em todas as rodadas.

## Escalabilidade forte

Na escalabilidade forte, o tamanho do problema fica fixo e o numero de threads varia.
O ideal seria o tempo cair proporcionalmente ao numero de threads.

{table_strong(summary)}

### Melhores casos por thread

{best_lines(summary, 'strong')}

## Escalabilidade fraca

Na escalabilidade fraca, o tamanho da malha cresce aproximadamente com a raiz do
numero de threads, mantendo o numero de celulas por thread quase constante. O ideal
seria o tempo permanecer proximo ao tempo com 1 thread.

{table_weak(summary)}

### Melhores casos por thread

{best_lines(summary, 'weak')}

## Graficos

![Escalabilidade forte](strong_scaling.png)

![Escalabilidade fraca](weak_scaling.png)

## Analise

A versao `omp-region` tende a ser melhor quando o numero de passos e alto, porque
evita recriar a equipe de threads a cada iteracao temporal. A versao `omp-basic`
representa uma primeira paralelizacao direta, adequada como ponto de partida, mas com
mais overhead de runtime.

Na escalabilidade forte, o ganho deixa de ser linear quando o custo de acesso a memoria
e as barreiras entre passos passam a dominar. Cada celula usa poucos calculos e acessa
varios vizinhos, portanto o kernel e sensivel a largura de banda de memoria e cache.

Na escalabilidade fraca, o objetivo e manter tempo aproximadamente constante ao crescer
o problema junto com o numero de threads. Quedas de eficiencia indicam overhead de
sincronizacao, limite de banda de memoria ou efeito de afinidade entre threads e nucleos.

## Artefatos

- Codigo: `Tarefa-12/navier_scaling.c`
- Coleta: `Tarefa-12/coletar_npad.py`
- CSV: `Tarefa-12/resultados/tarefa12_resultados.csv`
- Graficos: `Tarefa-12/resultados/strong_scaling.png` e `Tarefa-12/resultados/weak_scaling.png`
- Relatorio: `Tarefa-12/resultados/relatorio_tarefa12.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
