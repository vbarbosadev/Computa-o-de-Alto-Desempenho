import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa13_afinidade.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa13.md"


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "threads", "nx", "ny", "steps", "chunk", "collapse"]:
                row[key] = int(row[key])
            for key in [
                "cells_per_thread", "elapsed", "speedup", "efficiency",
                "relative_to_best_1t", "initial_max", "final_max", "initial_l2",
                "final_l2", "initial_sum", "final_sum",
            ]:
                row[key] = float(row[key])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        key = (
            row["affinity"], row["affinity_description"], row["mode"],
            row["threads"], row["nx"], row["ny"], row["schedule"],
            row["chunk"], row["collapse"], row["omp_proc_bind"],
            row["omp_places"], row["gomp_cpu_affinity"],
        )
        groups[key].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed"] for row in values]
        speedups = [row["speedup"] for row in values]
        efficiencies = [row["efficiency"] for row in values]
        relatives = [row["relative_to_best_1t"] for row in values]
        summary.append({
            "affinity": key[0],
            "affinity_description": key[1],
            "mode": key[2],
            "threads": key[3],
            "nx": key[4],
            "ny": key[5],
            "schedule": key[6],
            "chunk": key[7],
            "collapse": key[8],
            "omp_proc_bind": key[9],
            "omp_places": key[10],
            "gomp_cpu_affinity": key[11],
            "runs": len(values),
            "mean": statistics.mean(elapsed),
            "min": min(elapsed),
            "max": max(elapsed),
            "speedup": statistics.mean(speedups),
            "efficiency": statistics.mean(efficiencies),
            "relative_to_best_1t": statistics.mean(relatives),
            "initial_max": values[0]["initial_max"],
            "final_max": values[0]["final_max"],
            "initial_l2": values[0]["initial_l2"],
            "final_l2": values[0]["final_l2"],
        })
    return summary


def table_affinity(summary):
    lines = [
        "|Afinidade|Threads|OMP_PROC_BIND|OMP_PLACES|Rodadas|Media (s)|Min (s)|Max (s)|Speedup|Eficiencia|",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['affinity']}|{row['threads']}|{row['omp_proc_bind'] or '-'}|"
            f"{row['omp_places'] or '-'}|{row['runs']}|{row['mean']:.6f}|"
            f"{row['min']:.6f}|{row['max']:.6f}|{row['speedup']:.2f}|"
            f"{row['efficiency']:.2f}|"
        )
    return "\n".join(lines)


def ranking_by_threads(summary):
    by_threads = defaultdict(list)
    for row in summary:
        by_threads[row["threads"]].append(row)

    lines = []
    for threads in sorted(by_threads):
        best = sorted(by_threads[threads], key=lambda row: row["mean"])[0]
        worst = sorted(by_threads[threads], key=lambda row: row["mean"])[-1]
        gap = ((worst["mean"] / best["mean"]) - 1.0) * 100.0
        lines.append(
            f"- {threads} threads: melhor `{best['affinity']}` com media "
            f"{best['mean']:.6f}s; pior `{worst['affinity']}` com media "
            f"{worst['mean']:.6f}s; diferenca de {gap:.1f}%."
        )
    return "\n".join(lines)


def best_overall(summary):
    return sorted(summary, key=lambda row: row["mean"])[0]


def generate_report(rows, summary):
    first = rows[0]
    best = best_overall(summary)
    affinity_count = len({row["affinity"] for row in rows})
    thread_values = sorted({row["threads"] for row in rows})
    run_count = len(rows)

    report = f"""# Tarefa 13 - Afinidade de Threads no Navier-Stokes

## Objetivo

Avaliar como a escalabilidade do codigo de Navier-Stokes da Tarefa 12 muda quando
alteramos a afinidade das threads no mesmo no de computacao do NPAD.

Como a Tarefa 12 mostrou que `omp-region` foi a versao mais consistente na
escalabilidade forte, a Tarefa 13 usa essa versao como base e varia apenas a politica
de afinidade. Isso isola melhor o efeito de `OMP_PROC_BIND`, `OMP_PLACES` e
`GOMP_CPU_AFFINITY`.

## Configuracao

- Modo do codigo: `{first['mode']}`
- Malha fixa: `{first['nx']} x {first['ny']}`
- Passos de tempo: `{first['steps']}`
- Escalonamento: `schedule({first['schedule']})`
- Chunk: `{first['chunk']}`
- Collapse: `{first['collapse']}`
- Threads testadas: `{', '.join(str(t) for t in thread_values)}`
- Afinidades testadas: `{affinity_count}`
- Rodadas coletadas: `{run_count}`
- Compilacao: `gcc -O3 -march=native -fopenmp`

## Politicas de afinidade

- `sem_bind`: `OMP_PROC_BIND=false`, sem `OMP_PLACES` explicito.
- `close_cores`: `OMP_PROC_BIND=close` e `OMP_PLACES=cores`.
- `spread_cores`: `OMP_PROC_BIND=spread` e `OMP_PLACES=cores`.
- `close_threads`: `OMP_PROC_BIND=close` e `OMP_PLACES=threads`.
- `spread_threads`: `OMP_PROC_BIND=spread` e `OMP_PLACES=threads`.
- `gomp_cpu_affinity`: usa `GOMP_CPU_AFFINITY` para listar explicitamente as CPUs
  disponiveis ao processo, uma extensao do runtime GNU OpenMP.

## Validacao numerica

O mesmo criterio numerico da Tarefa 12 foi mantido: `dt * nu <= 0.25`. A execucao
registrada iniciou com maximo `{first['initial_max']:.6f}` e terminou com maximo
`{first['final_max']:.6f}` no primeiro caso coletado. A norma L2 tambem foi registrada
em todas as rodadas para confirmar que a mudanca de afinidade nao altera o resultado
fisico, apenas o tempo de execucao.

## Resultados

{table_affinity(summary)}

![Tempo por afinidade](affinity_elapsed.png)

![Speedup por afinidade](affinity_speedup.png)

## Ranking por numero de threads

{ranking_by_threads(summary)}

## Analise

O melhor caso agregado foi `{best['affinity']}` com `{best['threads']}` threads,
media de `{best['mean']:.6f}s` e speedup de `{best['speedup']:.2f}x` dentro da propria
politica de afinidade.

As politicas `close` tendem a favorecer localidade de cache, porque mantem threads em
posicoes proximas. Isso pode ajudar quando o trabalho compartilha dados proximos na
memoria. As politicas `spread` tendem a distribuir threads pelo no, o que pode reduzir
competicao local por recursos de um mesmo nucleo fisico ou socket. Para este stencil
2D, que faz poucos calculos por celula e muitos acessos a memoria, o resultado tende
a depender fortemente da largura de banda de memoria e da topologia do no.

Na Tarefa 12, o desempenho saturou depois de 8 a 16 threads. A Tarefa 13 verifica se
essa saturacao muda quando o runtime fixa as threads em nucleos proximos, espalha as
threads pelo no ou deixa o sistema operacional migrar threads. Se `sem_bind` for pior,
isso indica custo de migracao e perda de localidade. Se `spread_cores` for melhor em
altas contagens de threads, isso sugere que distribuir o acesso a memoria e aos caches
do no foi mais importante que manter as threads proximas.

## Artefatos

- Codigo: `Tarefa-13/navier_scaling.c`
- Coleta: `Tarefa-13/coletar_afinidade.py`
- CSV: `Tarefa-13/resultados/tarefa13_afinidade.csv`
- Graficos: `Tarefa-13/resultados/affinity_elapsed.png` e
  `Tarefa-13/resultados/affinity_speedup.png`
- Relatorio: `Tarefa-13/resultados/relatorio_tarefa13.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
