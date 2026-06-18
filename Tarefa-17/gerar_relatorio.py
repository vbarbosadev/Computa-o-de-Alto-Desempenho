import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa17_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa17.md"
CODE_FILES = ["matvec_seq.c", "matvec_collective.c"]


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "m", "n", "processes", "rows_per_process"]:
                row[key] = int(row[key])
            for key in [
                "seq_time",
                "elapsed",
                "speedup",
                "efficiency",
                "speedup_seq",
                "efficiency_seq",
                "speedup_mpi",
                "efficiency_mpi",
                "bcast_time",
                "scatter_time",
                "compute_time",
                "gather_time",
                "validation_time",
                "checksum",
            ]:
                if key in row and row[key] != "":
                    row[key] = float(row[key])
                elif key in row:
                    row[key] = None
            row.setdefault("speedup_seq", row["speedup"])
            row.setdefault("efficiency_seq", row["efficiency"])
            for key in [
                "speedup_mpi",
                "efficiency_mpi",
                "bcast_time",
                "scatter_time",
                "compute_time",
                "gather_time",
                "validation_time",
            ]:
                row.setdefault(key, None)
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["m"], row["n"], row["processes"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed"] for row in values]
        speedups_seq = [row["speedup_seq"] for row in values]
        efficiencies_seq = [row["efficiency_seq"] for row in values]
        speedups_mpi = [row["speedup_mpi"] for row in values if row["speedup_mpi"] is not None]
        efficiencies_mpi = [row["efficiency_mpi"] for row in values if row["efficiency_mpi"] is not None]
        summary.append({
            "m": key[0],
            "n": key[1],
            "processes": key[2],
            "rows_per_process": values[0]["rows_per_process"],
            "runs": len(values),
            "seq_time": values[0]["seq_time"],
            "mean": statistics.mean(elapsed),
            "min": min(elapsed),
            "max": max(elapsed),
            "speedup_seq": statistics.mean(speedups_seq),
            "efficiency_seq": statistics.mean(efficiencies_seq),
            "speedup_mpi": statistics.mean(speedups_mpi) if speedups_mpi else None,
            "efficiency_mpi": statistics.mean(efficiencies_mpi) if efficiencies_mpi else None,
            "bcast_time": mean_optional(values, "bcast_time"),
            "scatter_time": mean_optional(values, "scatter_time"),
            "compute_time": mean_optional(values, "compute_time"),
            "gather_time": mean_optional(values, "gather_time"),
            "validation_time": mean_optional(values, "validation_time"),
            "checksum": values[0]["checksum"],
        })
    return summary


def mean_optional(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    if not values:
        return None
    return statistics.mean(values)


def fmt_optional(value, digits=6):
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def table(summary):
    lines = [
        "|M|N|Proc.|Linhas/proc.|Rodadas|Seq calc. (s)|MPI total max (s)|Bcast|Scatter|Calc. local|Gather|Validacao|Speedup seq|Speedup MPI|Ef. MPI|",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['m']}|{row['n']}|{row['processes']}|{row['rows_per_process']}|"
            f"{row['runs']}|{row['seq_time']:.6f}|{row['mean']:.6f}|"
            f"{fmt_optional(row['bcast_time'])}|{fmt_optional(row['scatter_time'])}|"
            f"{fmt_optional(row['compute_time'])}|{fmt_optional(row['gather_time'])}|"
            f"{fmt_optional(row['validation_time'])}|{row['speedup_seq']:.2f}|"
            f"{fmt_optional(row['speedup_mpi'], 2)}|{fmt_optional(row['efficiency_mpi'], 2)}|"
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
            f"- Matriz {key[0]}x{key[1]}: melhor tempo com {best['processes']} processos, "
            f"media {best['mean']:.6f}s, speedup sequencial {best['speedup_seq']:.2f} "
            f"e speedup MPI interno {fmt_optional(best['speedup_mpi'], 2)}."
        )
    return "\n".join(lines)


def code_sections():
    sections = []
    for filename in CODE_FILES:
        code = (ROOT / filename).read_text(encoding="utf-8").rstrip()
        sections.append(f"### `{filename}`\n\n```c\n{code}\n```")
    return "\n\n".join(sections)


def generate_report(rows, summary):
    sizes = sorted({(row["m"], row["n"]) for row in rows})
    processes = sorted({row["processes"] for row in rows})
    size_text = ", ".join(f"{m}x{n}" for m, n in sizes)
    speedup_mpi_graph = ""
    if (ROOT / "resultados" / "speedup_mpi.png").exists():
        speedup_mpi_graph = "\n![Speedup MPI interno](speedup_mpi.png)\n"
    report = f"""# Tarefa 17 - Multiplicacao matriz-vetor com MPI coletivo

## Objetivo

Implementar o produto `y = A * x`, onde `A` e uma matriz `M x N` e `x` e um vetor de
tamanho `N`. A matriz e dividida por linhas entre os processos com `MPI_Scatter`, o
vetor completo e distribuido com `MPI_Bcast`, e os trechos de `y` sao reunidos no
processo `0` com `MPI_Gather`.

## Funcoes MPI usadas

A implementacao usa as rotinas de comunicacao coletiva apresentadas no conteudo 24:

- `MPI_Bcast`: envia o vetor `x` completo do processo `0` para todos os processos.
- `MPI_Scatter`: divide a matriz `A` por blocos de linhas, enviando um bloco para
  cada processo.
- `MPI_Gather`: junta os blocos locais de `y` calculados por cada processo no
  processo `0`.
- `MPI_Barrier`: faz todos os processos chegarem ao mesmo ponto antes do inicio da
  medicao de tempo.
- `MPI_Reduce`: soma os checksums locais e tambem calcula os tempos maximos entre
  ranks com `MPI_MAX`.

Tambem foram usadas as rotinas basicas ja vistas antes: `MPI_Init`,
`MPI_Comm_rank`, `MPI_Comm_size`, `MPI_Wtime` e `MPI_Finalize`.

Como o enunciado pede `MPI_Scatter`, foi usada a divisao simples em que `M` deve ser
divisivel pelo numero de processos. Os testes foram escolhidos respeitando essa
condicao.

## Configuracao

- Tamanhos de matriz testados: `{size_text}`
- Processos MPI testados: `{", ".join(str(p) for p in processes)}`
- Rodadas por configuracao: `{max(row['rep'] for row in rows)}`
- Compilacao sequencial: `gcc -O3 -Wall -Wextra`
- Compilacao MPI: `mpicc -O3 -Wall -Wextra`
- Medicao de tempo: `MPI_Wtime` na versao MPI e `gettimeofday` na versao sequencial

Na versao sequencial, o tempo medido comeca depois da inicializacao de `A` e `x` e
mede apenas o laco de calculo de `y = A*x`. Na versao MPI, o tempo total mede a
estrategia paralela completa: `MPI_Bcast`, `MPI_Scatter`, calculo local,
`MPI_Gather` e validacao por checksum. Por isso a tabela separa dois indicadores:

- `Speedup seq`: `tempo_sequencial_de_calculo / tempo_total_MPI`.
- `Speedup MPI`: `tempo_MPI_com_1_processo / tempo_MPI_com_P_processos`.

O tempo total MPI e os tempos parciais sao reduzidos com `MPI_Reduce(MPI_MAX)`,
reportando o rank mais lento. O checksum do vetor `y` foi comparado entre as versoes
para validar os resultados. Os tempos parciais ajudam a identificar gargalos, mas
nao devem ser somados para reconstruir o total, pois o maximo de cada fase pode vir
de ranks diferentes.

## Resultados

{table(summary)}

## Graficos

![Speedup](speedup.png)

{speedup_mpi_graph}

![Eficiencia](eficiencia.png)

## Melhores casos

{best_lines(summary)}

## Analise

O custo principal do calculo local e proporcional ao numero de linhas recebidas por
cada processo multiplicado por `N`. Ao aumentar a quantidade de processos, cada
processo recebe menos linhas de `A`, reduzindo o trabalho local.

Nos resultados, o tempo da versao MPI diminuiu quando foram usados mais processos,
principalmente nas matrizes maiores. Nas matrizes pequenas, a diferenca entre 1, 2 e
4 processos foi pequena, porque o custo de comunicacao e preparacao dos dados ficou
parecido com o custo do proprio calculo. Nas matrizes maiores, a reducao de tempo
ficou mais visivel, pois cada processo recebeu uma parte relevante do trabalho e o
calculo local passou a compensar melhor o custo das coletivas.

Mesmo assim, o speedup em relacao ao programa sequencial ficou menor que 1 em todos
os casos. Isso significa que a versao MPI ficou mais lenta que a sequencial usada
como base. Essa comparacao e intencionalmente conservadora: o sequencial mede so o
calculo, enquanto o tempo MPI total inclui comunicacao, reuniao do resultado e
validacao. O speedup MPI interno, por outro lado, isola melhor a escalabilidade da
implementacao coletiva ao comparar a propria versao MPI com 1 processo contra 2 e 4
processos. Para esses tamanhos e nesse ambiente local, o custo das etapas extras foi
maior que o ganho obtido ao dividir o calculo.

### Efeito de cada funcao coletiva

`MPI_Barrier` foi usado antes da medicao. Ele nao acelera o programa; pelo contrario,
pode adicionar um pequeno custo. Sua funcao aqui e deixar a medicao mais justa,
garantindo que nenhum processo comece a cronometrar a parte principal antes dos
outros estarem prontos. Assim, o tempo medido representa melhor a execucao coletiva
do trecho paralelo.

`MPI_Bcast` distribui o vetor `x` inteiro para todos os processos. Esse custo depende
principalmente de `N` e da quantidade de processos. Como todos os processos precisam
do vetor completo para calcular suas linhas, essa etapa e necessaria. Ela pesa mais
quando a matriz tem poucas linhas por processo, porque o tempo gasto enviando `x`
fica grande em relacao ao tempo de multiplicacao local.

`MPI_Scatter` divide a matriz `A` em blocos de linhas. Essa foi a comunicacao mais
pesada da implementacao, pois a matriz tem `M * N` elementos e apenas o processo `0`
possui a matriz completa antes da divisao. Quando o numero de processos aumenta, cada
processo recebe menos linhas, o que ajuda no calculo local. Ao mesmo tempo, o processo
`0` precisa enviar blocos para mais processos. Por isso, o ganho aparece melhor nas
matrizes maiores: ha mais calculo para cada bloco recebido.

`MPI_Gather` recolhe os pedacos do vetor `y`. O custo dessa etapa e menor que o do
`MPI_Scatter`, porque `y` tem apenas `M` elementos, enquanto `A` tem `M * N`.
Mesmo assim, ela adiciona uma sincronizacao natural ao final: o processo `0` so tem o
resultado completo depois que todos os processos terminam seus calculos locais e
enviam suas partes.

`MPI_Reduce` foi usado de duas formas. Para validar o resultado, cada processo
calcula um checksum local somando os valores do seu bloco de `y`; em seguida,
`MPI_Reduce(MPI_SUM)` entrega o checksum global ao processo `0`. Para medir tempo,
cada rank calcula suas duracoes locais e `MPI_Reduce(MPI_MAX)` reporta o maior valor,
isto e, o tempo observado pelo rank mais lento. Essa escolha evita que a analise
dependa apenas do tempo do rank `0`.

A eficiencia mede quanto do ganho teorico foi aproveitado. Ela caiu quando o numero
de processos aumentou porque o trabalho local por processo diminuiu, mas os custos de
`MPI_Barrier`, `MPI_Bcast`, `MPI_Scatter`, `MPI_Gather` e `MPI_Reduce` continuaram
existindo. Em geral, usar mais processos reduz o trabalho de multiplicacao por
processo, mas aumenta o peso relativo da comunicacao. Por isso, uma configuracao pode
ter melhor tempo absoluto e, ao mesmo tempo, baixa eficiencia em relacao ao ganho
ideal.

## Conclusao

A Tarefa 17 mostra o uso direto das coletivas `MPI_Bcast`, `MPI_Scatter`,
`MPI_Gather`, `MPI_Barrier` e `MPI_Reduce` em um problema regular. A divisao por
linhas e natural para o produto matriz-vetor: cada processo recebe algumas linhas
completas de `A`, usa o mesmo vetor `x` e calcula uma parte independente de `y`.

O programa evita comunicacao ponto a ponto manual e deixa a distribuicao/reuniao dos
dados sob responsabilidade das rotinas coletivas apresentadas no material. O ganho de
desempenho depende do equilibrio entre quantidade de calculo local e custo das
coletivas.

Pelos testes, a paralelizacao com MPI trouxe melhora interna quando comparamos 1, 2 e
4 processos MPI na mesma matriz, mas ainda nao superou a versao sequencial. A perda
contra o sequencial acontece porque as coletivas acrescentam comunicacao,
sincronizacao e copia de dados. O aumento de desempenho aparece quando o calculo
local fica grande o suficiente para compensar parte desse custo.

Assim, a implementacao esta correta para demonstrar comunicacao coletiva basica: o
vetor e transmitido uma vez para todos, a matriz e dividida por linhas, cada processo
calcula sua parte independente, o resultado final volta para o processo `0`, e o
checksum global e obtido por reducao. Para obter speedup maior em execucoes reais,
seria necessario aumentar mais o tamanho do problema, reduzir custos de distribuicao
ou usar uma organizacao em que os dados ja estejam distribuidos entre os processos
antes da medicao.

## Codigos

{code_sections()}

## Artefatos

- Codigo sequencial: `Tarefa-17/matvec_seq.c`
- Codigo MPI: `Tarefa-17/matvec_collective.c`
- Coleta: `Tarefa-17/coletar_mpi.py`
- CSV: `Tarefa-17/resultados/tarefa17_resultados.csv`
- Graficos: `Tarefa-17/resultados/speedup.png` e
  `Tarefa-17/resultados/eficiencia.png`
- Relatorio: `Tarefa-17/resultados/relatorio_tarefa17.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
