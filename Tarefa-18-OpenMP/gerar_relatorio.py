import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa18_openmp_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa18_openmp.md"
CODE_FILE = ROOT / "matvec_openmp.c"


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "m", "n", "threads"]:
                row[key] = int(row[key])
            for key in ["seq_time", "elapsed", "speedup", "efficiency", "checksum"]:
                row[key] = float(row[key])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["m"], row["n"], row["threads"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed"] for row in values]
        speedups = [row["speedup"] for row in values]
        efficiencies = [row["efficiency"] for row in values]
        summary.append({
            "m": key[0],
            "n": key[1],
            "threads": key[2],
            "runs": len(values),
            "seq_time": values[0]["seq_time"],
            "mean": statistics.mean(elapsed),
            "min": min(elapsed),
            "max": max(elapsed),
            "speedup": statistics.mean(speedups),
            "efficiency": statistics.mean(efficiencies),
            "checksum": values[0]["checksum"],
        })
    return summary


def table(summary):
    lines = [
        "|M|N|Threads|Rodadas|Tempo seq (s)|Media OpenMP (s)|Speedup|Eficiencia|Checksum|",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['m']}|{row['n']}|{row['threads']}|{row['runs']}|"
            f"{row['seq_time']:.6f}|{row['mean']:.6f}|{row['speedup']:.2f}|"
            f"{row['efficiency']:.2f}|{row['checksum']:.2f}|"
        )
    return "\n".join(lines)


def best_lines(summary):
    groups = defaultdict(list)
    for row in summary:
        groups[(row["m"], row["n"])].append(row)

    lines = []
    for key in sorted(groups):
        best = min(groups[key], key=lambda row: row["mean"])
        lines.append(
            f"- Matriz {key[0]}x{key[1]}: melhor tempo com {best['threads']} threads, "
            f"media {best['mean']:.6f}s, speedup {best['speedup']:.2f}."
        )
    return "\n".join(lines)


def generate_report(rows, summary):
    sizes = sorted({(row["m"], row["n"]) for row in rows})
    threads = sorted({row["threads"] for row in rows})
    size_text = ", ".join(f"{m}x{n}" for m, n in sizes)
    code = CODE_FILE.read_text(encoding="utf-8").rstrip()

    report = f"""# Tarefa 18 - Versao OpenMP

## Objetivo

Criar uma nova versao paralela do produto `y = A * x` usando OpenMP, mantendo os
resultados MPI atuais em outra pasta. A paralelizacao foi feita no laco externo, em
que cada thread calcula uma faixa de linhas do vetor `y`.

## Implementacao

A matriz em C fica armazenada por linhas. Por isso, paralelizar o laco das linhas e
uma escolha natural: cada thread acessa trechos contiguos de `A` e escreve posicoes
diferentes de `y`. A diretiva usada foi:

```c
#pragma omp parallel for schedule(static)
```

O escalonamento `static` divide as iteracoes entre as threads antes da execucao do
laco. Como cada linha faz aproximadamente a mesma quantidade de trabalho, essa
divisao e adequada e evita overhead desnecessario de escalonamento dinamico.

## Configuracao

- Tamanhos de matriz testados: `{size_text}`
- Threads testadas: `{", ".join(str(t) for t in threads)}`
- Rodadas por configuracao: `{max(row['rep'] for row in rows)}`
- Compilacao sequencial: `gcc -O3 -Wall -Wextra`
- Compilacao OpenMP: `gcc -O3 -Wall -Wextra -fopenmp`

O tempo sequencial usado como base tambem foi medido em varias rodadas e salvo como
media no CSV. Isso reduz o efeito de uma execucao isolada muito lenta ou muito
rapida, que distorce o speedup em problemas pequenos.

## Resultados

{table(summary)}

## Graficos

![Speedup](speedup.png)

![Tempo](tempo.png)

## Melhores casos

{best_lines(summary)}

## Analise

Esta versao evita a comunicacao entre processos que aparece nas implementacoes MPI.
Como as threads compartilham a mesma memoria, nao e necessario usar `MPI_Scatter`,
tipos derivados ou `MPI_Reduce`. O trabalho principal fica concentrado no calculo
das linhas de `y`.

O ganho depende do tamanho da matriz. Em matrizes pequenas, o tempo sequencial ja e
muito baixo, entao a criacao e coordenacao das threads pode reduzir o beneficio. Em
matrizes maiores, ha mais linhas para distribuir e o custo fixo do paralelismo pesa
menos em relacao ao calculo.

Mesmo no OpenMP, o speedup nao cresce indefinidamente. O produto matriz-vetor acessa
muitos dados da matriz `A`, entao o desempenho pode ficar limitado pela largura de
banda de memoria. Ao aumentar o numero de threads, mais nucleos tentam ler dados da
memoria ao mesmo tempo, e o gargalo passa a ser o acesso aos dados, nao apenas a
quantidade de operacoes aritmeticas.

## Conclusao

A versao OpenMP e mais direta para este problema em uma unica maquina, porque a
distribuicao de trabalho por linhas combina com o layout da matriz e nao exige
copias ou comunicacao explicita. Ela serve como comparacao importante com as versoes
MPI: quando todos os dados ja estao na mesma memoria, OpenMP tende a ter overhead
menor.

## Codigo

### `matvec_openmp.c`

```c
{code}
```

## Artefatos

- Codigo OpenMP: `Tarefa-18-OpenMP/matvec_openmp.c`
- Coleta: `Tarefa-18-OpenMP/coletar_openmp.py`
- CSV: `Tarefa-18-OpenMP/resultados/tarefa18_openmp_resultados.csv`
- Graficos: `Tarefa-18-OpenMP/resultados/speedup.png` e
  `Tarefa-18-OpenMP/resultados/tempo.png`
- Relatorio: `Tarefa-18-OpenMP/resultados/relatorio_tarefa18_openmp.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
