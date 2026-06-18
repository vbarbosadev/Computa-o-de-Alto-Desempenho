import csv
import statistics
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa13_afinidade.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa13.md"
RESULTS_DIR = ROOT / "resultados"


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


def color_for_affinity(name):
    palette = {
        "sem_bind": "#2563eb",
        "close_cores": "#16a34a",
        "spread_cores": "#f97316",
        "close_threads": "#7c3aed",
        "spread_threads": "#dc2626",
        "gomp_cpu_affinity": "#0891b2",
    }
    return palette.get(name, "#111827")


def draw_line_chart(summary, metric, ylabel, title, output):
    width = 1100
    height = 680
    margin_left = 90
    margin_right = 260
    margin_top = 70
    margin_bottom = 90
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    by_affinity = defaultdict(list)
    for row in summary:
        by_affinity[row["affinity"]].append(row)
    for values in by_affinity.values():
        values.sort(key=lambda row: row["threads"])

    threads = sorted({row["threads"] for row in summary})
    values = [row[metric] for row in summary]
    min_value = min(values)
    max_value = max(values)
    if metric == "mean":
        min_value = 0.0
    if max_value == min_value:
        max_value = min_value + 1.0

    def x_for(thread):
        if len(threads) == 1:
            return margin_left + plot_w / 2
        idx = threads.index(thread)
        return margin_left + idx * plot_w / (len(threads) - 1)

    def y_for(value):
        return margin_top + (max_value - value) * plot_h / (max_value - min_value)

    draw.text((margin_left, 24), title, fill="#111827", font=font)
    draw.line((margin_left, margin_top, margin_left, margin_top + plot_h), fill="#111827", width=2)
    draw.line((margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h), fill="#111827", width=2)

    for i in range(6):
        value = min_value + (max_value - min_value) * i / 5
        y = y_for(value)
        draw.line((margin_left, y, margin_left + plot_w, y), fill="#e5e7eb", width=1)
        draw.text((12, y - 6), f"{value:.2f}", fill="#374151", font=font)

    for thread in threads:
        x = x_for(thread)
        draw.line((x, margin_top + plot_h, x, margin_top + plot_h + 6), fill="#111827", width=1)
        draw.text((x - 10, margin_top + plot_h + 16), str(thread), fill="#374151", font=font)

    draw.text((margin_left + plot_w / 2 - 35, height - 38), "Threads", fill="#111827", font=font)
    draw.text((12, 48), ylabel, fill="#111827", font=font)

    for affinity, rows in sorted(by_affinity.items()):
        color = color_for_affinity(affinity)
        points = [(x_for(row["threads"]), y_for(row[metric])) for row in rows]
        if len(points) > 1:
            draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color, outline="white", width=1)

    legend_x = margin_left + plot_w + 35
    legend_y = margin_top
    draw.text((legend_x, legend_y - 24), "Afinidade", fill="#111827", font=font)
    for i, affinity in enumerate(sorted(by_affinity)):
        y = legend_y + i * 26
        color = color_for_affinity(affinity)
        draw.rectangle((legend_x, y, legend_x + 14, y + 14), fill=color)
        draw.text((legend_x + 22, y), affinity, fill="#374151", font=font)

    image.save(output)


def generate_charts(summary):
    elapsed = RESULTS_DIR / "affinity_elapsed.png"
    speedup = RESULTS_DIR / "affinity_speedup.png"
    draw_line_chart(summary, "mean", "Tempo medio (s)", "Tarefa 13 - Tempo por afinidade", elapsed)
    draw_line_chart(summary, "speedup", "Speedup", "Tarefa 13 - Speedup por afinidade", speedup)
    print(f"Grafico salvo em: {elapsed}")
    print(f"Grafico salvo em: {speedup}")


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
    generate_charts(summary)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
