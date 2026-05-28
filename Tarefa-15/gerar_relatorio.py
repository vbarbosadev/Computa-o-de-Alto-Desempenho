import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa15_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa15.md"
CODE_FILES = [
    "heat_send_recv.c",
    "heat_isend_irecv_wait.c",
    "heat_isend_irecv_test.c",
]


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "processes", "n", "steps", "rank", "local_n"]:
                row[key] = int(row[key])
            for key in ["elapsed_max", "elapsed_mean", "sum_total", "rank_time", "local_sum"]:
                row[key] = float(row[key])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["rank"] == 0:
            groups[(row["version"], row["processes"], row["n"], row["steps"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed_max"] for row in values]
        sums = [row["sum_total"] for row in values]
        summary.append({
            "version": key[0],
            "processes": key[1],
            "n": key[2],
            "steps": key[3],
            "runs": len(values),
            "mean": statistics.mean(elapsed),
            "min": min(elapsed),
            "max": max(elapsed),
            "sum_mean": statistics.mean(sums),
        })
    return summary


def table(summary):
    lines = [
        "|Versao|Processos|N|Passos|Rodadas|Media (s)|Min (s)|Max (s)|Soma final|",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['version']}|{row['processes']}|{row['n']}|{row['steps']}|"
            f"{row['runs']}|{row['mean']:.6f}|{row['min']:.6f}|"
            f"{row['max']:.6f}|{row['sum_mean']:.6f}|"
        )
    return "\n".join(lines)


def best_lines(summary):
    groups = defaultdict(list)
    for row in summary:
        groups[(row["processes"], row["n"])].append(row)

    lines = []
    for key in sorted(groups):
        best = min(groups[key], key=lambda row: row["mean"])
        lines.append(
            f"- {key[0]} processos, N={key[1]}: `{best['version']}` com media "
            f"{best['mean']:.6f}s."
        )
    return "\n".join(lines)


def code_sections():
    sections = []
    for filename in CODE_FILES:
        code = (ROOT / filename).read_text(encoding="utf-8").rstrip()
        sections.append(f"### `{filename}`\n\n```c\n{code}\n```")
    return "\n\n".join(sections)


def generate_report(rows, summary):
    process_values = sorted({row["processes"] for row in rows})
    sizes = sorted({row["n"] for row in rows})
    steps = sorted({row["steps"] for row in rows})
    report = f"""# Tarefa 15 - Difusao de calor 1D com MPI

## Objetivo

Implementar uma simulacao de difusao de calor em uma barra 1D dividida entre dois
ou mais processos MPI. Cada processo calcula um trecho da barra e mantem duas celulas
extras: uma borda fantasma a esquerda e outra a direita. Essas celulas recebem os
valores dos vizinhos por troca de mensagens.

Foram implementadas tres versoes:

- `send_recv`: comunicacao bloqueante com `MPI_Send` e `MPI_Recv`.
- `isend_irecv_wait`: comunicacao nao bloqueante com `MPI_Isend`, `MPI_Irecv` e
  espera explicita com `MPI_Wait`.
- `isend_irecv_test`: comunicacao nao bloqueante com `MPI_Isend`, `MPI_Irecv` e
  consultas com `MPI_Test`, atualizando pontos internos enquanto a comunicacao das
  bordas ainda pode estar em andamento.

## Modelo numerico

A barra 1D usa a atualizacao explicita:

```c
novo[i] = u[i] + alpha * (u[i - 1] - 2.0 * u[i] + u[i + 1]);
```

Foi usado `alpha = 0.25`, valor estavel para este esquema simples. A condicao inicial
coloca uma regiao quente no inicio global da barra, entre as posicoes `45` e `55`,
com temperatura `100.0`; o restante inicia com `0.0`.

## Configuracao

- Processos testados: `{", ".join(str(value) for value in process_values)}`
- Tamanhos da barra: `{", ".join(str(value) for value in sizes)}`
- Passos de tempo: `{", ".join(str(value) for value in steps)}`
- Rodadas por configuracao: `{max(row['rep'] for row in rows)}`
- Compilacao: `mpicc -O3 -Wall -Wextra -lm`
- Medicao de tempo: `MPI_Wtime`

O codigo usa apenas recursos vistos nos materiais das aulas 21 e 22: `MPI_Init`,
`MPI_Comm_rank`, `MPI_Comm_size`, `MPI_Send`, `MPI_Recv`, `MPI_Isend`, `MPI_Irecv`,
`MPI_Wait`, `MPI_Test`, `MPI_Wtime` e `MPI_Finalize`. Nao foram usadas rotinas
coletivas.

Cada processo imprime seu proprio tempo. O script de coleta calcula, fora do programa
MPI, o maior tempo entre os ranks de uma execucao. Esse valor representa o tempo
efetivo da simulacao, pois a execucao termina quando o processo mais lento termina.

## Resultados

{table(summary)}

## Graficos

![Tempo N=100000](tempo_n100000.png)

![Tempo N=1000000](tempo_n1000000.png)

![Speedup relativo](speedup_relativo.png)

## Melhores casos

{best_lines(summary)}

## Analise

Na versao `send_recv`, a troca de bordas e bloqueante. O processo fica parado enquanto
espera receber valores dos vizinhos e so depois atualiza seus pontos. Essa versao e a
mais simples para entender a comunicacao, mas tende a expor mais o custo de espera.

Na versao `isend_irecv_wait`, as operacoes de envio e recebimento sao iniciadas com
`MPI_Isend` e `MPI_Irecv`. Em seguida, o programa usa `MPI_Wait` para garantir que as
mensagens chegaram antes de atualizar a barra. Essa versao evita algumas esperas de
envio e recebimento bloqueantes, mas ainda nao sobrepoe muito calculo e comunicacao,
pois espera pelas bordas antes de calcular os pontos.

Na versao `isend_irecv_test`, as mensagens tambem sao iniciadas de forma nao
bloqueante, mas os pontos internos da barra sao calculados enquanto o programa chama
`MPI_Test` para verificar se as bordas chegaram. Os pontos internos nao dependem das
celulas fantasmas, portanto podem ser atualizados antes da conclusao da comunicacao.
Depois que as bordas chegam, os pontos das extremidades locais sao atualizados.

O ganho esperado com sobreposicao aparece quando ha trabalho interno suficiente para
ocupar o tempo em que as mensagens de borda trafegam. Por isso, tamanhos maiores de
barra tendem a favorecer mais a versao com `MPI_Test`. Em problemas pequenos, o custo
de iniciar as mensagens e testar requisicoes pode ser parecido ou maior do que o ganho
da sobreposicao.

Nos dados coletados nesta maquina, a versao `isend_irecv_test` ficou mais lenta que
as outras. Isso ocorreu porque o programa chama `MPI_Test` repetidamente enquanto
atualiza os pontos internos. Como cada processo troca apenas dois valores de borda por
passo, a comunicacao e pequena; assim, o custo extra de testar as requisicoes muitas
vezes ficou maior que o beneficio da sobreposicao. O melhor resultado para `N=1000000`
com 4 processos foi `isend_irecv_wait`, enquanto `send_recv` foi melhor nos casos
menores.

## Conclusao

A Tarefa 15 mostra a evolucao natural da comunicacao MPI. A versao com `MPI_Send` e
`MPI_Recv` e adequada como primeira implementacao, pois deixa clara a troca de bordas.
A versao com `MPI_Isend`, `MPI_Irecv` e `MPI_Wait` introduz comunicacao nao bloqueante,
mas ainda espera explicitamente pelas mensagens antes do calculo completo. A versao
com `MPI_Test` explora melhor a ideia da aula 22: enquanto a comunicacao nao termina,
o processo pode atualizar os pontos internos que nao dependem das bordas.

Assim, a principal vantagem da comunicacao nao bloqueante nao e apenas trocar a funcao
de envio ou recepcao, mas reorganizar o algoritmo para sobrepor comunicacao e
computacao.

## Codigos

{code_sections()}

## Artefatos

- Codigos: `Tarefa-15/heat_send_recv.c`, `Tarefa-15/heat_isend_irecv_wait.c` e
  `Tarefa-15/heat_isend_irecv_test.c`
- Coleta: `Tarefa-15/coletar_mpi.py`
- CSV: `Tarefa-15/resultados/tarefa15_resultados.csv`
- Graficos: `Tarefa-15/resultados/tempo_n100000.png`,
  `Tarefa-15/resultados/tempo_n1000000.png` e
  `Tarefa-15/resultados/speedup_relativo.png`
- Relatorio: `Tarefa-15/resultados/relatorio_tarefa15.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
