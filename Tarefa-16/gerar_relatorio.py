import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa16_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa16.md"
CODE_FILES = ["primos_seq.c", "leader_worker_primes.c"]


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "max", "tasks", "processes", "workers", "primes"]:
                row[key] = int(row[key])
            for key in ["seq_time", "elapsed", "speedup", "efficiency"]:
                row[key] = float(row[key])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["max"], row["tasks"], row["processes"], row["workers"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed"] for row in values]
        speedups = [row["speedup"] for row in values]
        efficiencies = [row["efficiency"] for row in values]
        summary.append({
            "max": key[0],
            "tasks": key[1],
            "processes": key[2],
            "workers": key[3],
            "runs": len(values),
            "primes": values[0]["primes"],
            "seq_time": values[0]["seq_time"],
            "mean": statistics.mean(elapsed),
            "min": min(elapsed),
            "max_time": max(elapsed),
            "speedup": statistics.mean(speedups),
            "efficiency": statistics.mean(efficiencies),
            "worker_tasks": values[0]["worker_tasks"],
        })
    return summary


def table(summary):
    lines = [
        "|Max|Tarefas|Processos|Trabalhadores|Rodadas|Tempo seq (s)|Media MPI (s)|Speedup|Eficiencia|Primos|",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['max']}|{row['tasks']}|{row['processes']}|{row['workers']}|"
            f"{row['runs']}|{row['seq_time']:.6f}|{row['mean']:.6f}|"
            f"{row['speedup']:.2f}|{row['efficiency']:.2f}|{row['primes']}|"
        )
    return "\n".join(lines)


def best_lines(summary):
    groups = defaultdict(list)
    for row in summary:
        groups[(row["max"], row["workers"])].append(row)

    lines = []
    for key in sorted(groups):
        best = min(groups[key], key=lambda row: row["mean"])
        lines.append(
            f"- Max={key[0]}, {key[1]} trabalhadores: {best['tasks']} tarefas, "
            f"media {best['mean']:.6f}s, speedup {best['speedup']:.2f}, "
            f"eficiencia {best['efficiency']:.2f}."
        )
    return "\n".join(lines)


def code_sections():
    sections = []
    for filename in CODE_FILES:
        code = (ROOT / filename).read_text(encoding="utf-8").rstrip()
        sections.append(f"### `{filename}`\n\n```c\n{code}\n```")
    return "\n\n".join(sections)


def generate_report(rows, summary):
    max_values = sorted({row["max"] for row in rows})
    task_values = sorted({row["tasks"] for row in rows})
    process_values = sorted({row["processes"] for row in rows})
    largest = max(max_values)
    report = f"""# Tarefa 16 - Escalonador lider-trabalhador com MPI

## Objetivo

Desenvolver um escalonador dinamico de tarefas em MPI no modelo
lider-trabalhador. O processo `0` atua como lider: distribui tarefas, recebe
resultados dos trabalhadores e envia novas tarefas conforme cada trabalhador termina
a anterior.

A aplicacao escolhida foi a contagem de numeros primos no intervalo de `2` ate um
valor maximo. Cada tarefa corresponde a um subintervalo de numeros.

## Funcoes MPI usadas

A implementacao usa apenas os conceitos dos materiais 21, 22 e 23:

- `MPI_Init`, `MPI_Finalize`, `MPI_Comm_rank` e `MPI_Comm_size`;
- `MPI_Send` e `MPI_Recv` para troca ponto a ponto;
- `MPI_ANY_SOURCE`, visto junto com `MPI_Recv`, para o lider receber resultado de
  qualquer trabalhador que terminar primeiro;
- `MPI_ANY_TAG`, usado pelos trabalhadores para receber tarefa ou sinal de parada;
- `MPI_Wtime` para medir o tempo da parte MPI.

Nao foram usadas rotinas coletivas. O speedup e a eficiencia sao calculados no script
Python a partir do tempo sequencial e do tempo MPI.

## Como o escalonador evita deadlock

O fluxo de mensagens foi organizado para evitar espera circular:

1. O lider envia uma tarefa inicial para cada trabalhador.
2. Cada trabalhador recebe uma tarefa, calcula o numero de primos do subintervalo e
   envia o resultado ao lider.
3. O lider fica em `MPI_Recv` com `MPI_ANY_SOURCE`, aceitando o primeiro trabalhador
   que terminar.
4. Ao receber um resultado, o lider envia outra tarefa para o mesmo trabalhador ou
   envia uma mensagem de parada.
5. O trabalhador so espera nova mensagem depois de enviar seu resultado.

Assim, nao ha ciclo em que todos os processos estejam esperando envio uns dos outros.
O lider sempre esta preparado para receber resultados, e os trabalhadores sempre
voltam a receber depois de concluir uma tarefa.

## Configuracao

- Valores maximos testados: `{", ".join(str(value) for value in max_values)}`
- Quantidades de tarefas: `{", ".join(str(value) for value in task_values)}`
- Processos MPI testados: `{", ".join(str(value) for value in process_values)}`
- Trabalhadores: processos MPI menos o lider
- Rodadas por configuracao: `{max(row['rep'] for row in rows)}`
- Compilacao sequencial: `gcc -O3 -Wall -Wextra -lm`
- Compilacao MPI: `mpicc -O3 -Wall -Wextra -lm`

## Resultados

{table(summary)}

## Graficos

![Speedup max {max_values[0]}](tarefa16_speedup_max{max_values[0]}.png)

![Speedup max {largest}](tarefa16_speedup_max{largest}.png)

![Eficiencia](tarefa16_eficiencia.png)

## Melhores casos

{best_lines(summary)}

## Analise

O escalonamento dinamico permite que o lider entregue novas tarefas a trabalhadores
conforme eles terminam. Isso e util para a contagem de primos porque subintervalos
maiores ou com numeros maiores podem custar mais: testar primalidade perto do fim do
intervalo exige mais divisoes do que testar numeros pequenos.

Quando ha poucas tarefas, a distribuicao pode ficar menos equilibrada: um trabalhador
pode receber um bloco mais pesado e atrasar o fim da execucao. Ao aumentar a
quantidade de tarefas, os blocos ficam menores e o lider consegue redistribuir melhor
o trabalho. Por outro lado, tarefas demais tambem aumentam o numero de mensagens e o
overhead de escalonamento.

O speedup compara o tempo sequencial com o tempo MPI. A eficiencia divide esse
speedup pelo numero de trabalhadores. Eficiencia proxima de `1.0` indicaria uso quase
ideal dos trabalhadores; quedas indicam overhead de comunicacao, desequilibrio de
carga ou custo do lider coordenando as tarefas.

Em alguns casos com `3` trabalhadores a eficiencia ficou acima de `1.0`. Isso pode
acontecer em medicoes pequenas por efeito de cache, variacao do sistema e diferenca
entre executar um unico processo sequencial e dividir o intervalo em blocos menores.
Por isso, esses valores devem ser lidos como indicio de bom aproveitamento, nao como
garantia de ganho perfeitamente linear.

## Conclusao

A Tarefa 16 implementa um escalonador lider-trabalhador sem deadlock usando apenas
comunicacao ponto a ponto. O lider nunca fica preso esperando um trabalhador
especifico: ele recebe de qualquer trabalhador que concluir primeiro. Os trabalhadores
tambem seguem um ciclo simples de receber tarefa, calcular, enviar resultado e esperar
nova tarefa ou parada.

Esse modelo e adequado para problemas com tarefas independentes, como contar primos
em subintervalos. A quantidade de tarefas deve ser escolhida com cuidado: tarefas
demais aumentam a comunicacao, enquanto tarefas de menos podem causar desequilibrio
entre trabalhadores.

## Codigos

{code_sections()}

## Artefatos

- Codigo sequencial: `Tarefa-16/primos_seq.c`
- Codigo MPI: `Tarefa-16/leader_worker_primes.c`
- Coleta: `Tarefa-16/coletar_mpi.py`
- CSV: `Tarefa-16/resultados/tarefa16_resultados.csv`
- Graficos: `Tarefa-16/resultados/speedup_max{max_values[0]}.png`,
  `Tarefa-16/resultados/speedup_max{largest}.png` e
  `Tarefa-16/resultados/eficiencia.png`
- Relatorio: `Tarefa-16/resultados/relatorio_tarefa16.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
