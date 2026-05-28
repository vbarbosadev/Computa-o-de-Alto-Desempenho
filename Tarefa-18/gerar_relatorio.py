import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CSV_FILE = ROOT / "resultados" / "tarefa18_resultados.csv"
T17_CSV = REPO / "Tarefa-17" / "resultados" / "tarefa17_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa18.md"
CODE_FILES = ["matvec_cols_vector.c", "matvec_cols_resized.c"]


def load_rows(path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if "version" not in row:
                row["version"] = "mpi_collective"
            for key in ["rep", "m", "n", "processes"]:
                row[key] = int(row[key])
            for key in ["seq_time", "elapsed", "speedup", "efficiency", "checksum"]:
                row[key] = float(row[key])
            if "cols_per_process" in row:
                row["cols_per_process"] = int(row["cols_per_process"])
            if "rows_per_process" in row:
                row["rows_per_process"] = int(row["rows_per_process"])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["version"], row["m"], row["n"], row["processes"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        elapsed = [row["elapsed"] for row in values]
        speedups = [row["speedup"] for row in values]
        efficiencies = [row["efficiency"] for row in values]
        summary.append({
            "version": key[0],
            "m": key[1],
            "n": key[2],
            "processes": key[3],
            "parts_per_process": values[0].get("cols_per_process", values[0].get("rows_per_process", 0)),
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


def table(summary, label):
    lines = [
        f"|Versao|M|N|Processos|{label}/processo|Rodadas|Tempo seq (s)|Media MPI (s)|Speedup|Eficiencia|Checksum|",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['version']}|{row['m']}|{row['n']}|{row['processes']}|{row['parts_per_process']}|"
            f"{row['runs']}|{row['seq_time']:.6f}|{row['mean']:.6f}|"
            f"{row['speedup']:.2f}|{row['efficiency']:.2f}|{row['checksum']:.2f}|"
        )
    return "\n".join(lines)


def best_lines(summary):
    groups = defaultdict(list)
    for row in summary:
        groups[(row["m"], row["n"], row["version"])].append(row)

    lines = []
    for key in sorted(groups):
        best = min(groups[key], key=lambda row: row["mean"])
        lines.append(
            f"- {key[2]} {key[0]}x{key[1]}: melhor tempo com {best['processes']} processos, "
            f"media {best['mean']:.6f}s, speedup {best['speedup']:.2f}."
        )
    return "\n".join(lines)


def comparison_table(t17_summary, t18_summary):
    if not t17_summary:
        return "Resultados da Tarefa 17 nao encontrados para comparacao automatica."

    best = {}
    for row in t17_summary + t18_summary:
        key = (row["m"], row["n"], row["processes"])
        best.setdefault(key, {})[row["version"]] = row["mean"]

    lines = [
        "|M|N|Processos|T17 linhas (s)|T18 vector (s)|T18 resized (s)|",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for key in sorted(best):
        if "mpi_collective" in best[key] and "cols_vector" in best[key] and "cols_resized" in best[key]:
            lines.append(
                f"|{key[0]}|{key[1]}|{key[2]}|"
                f"{best[key]['mpi_collective']:.6f}|{best[key]['cols_vector']:.6f}|{best[key]['cols_resized']:.6f}|"
            )
    return "\n".join(lines)


def code_sections():
    sections = []
    for filename in CODE_FILES:
        code = (ROOT / filename).read_text(encoding="utf-8").rstrip()
        sections.append(f"### `{filename}`\n\n```c\n{code}\n```")
    return "\n\n".join(sections)


def generate_report(rows, summary, t17_summary):
    sizes = sorted({(row["m"], row["n"]) for row in rows})
    processes = sorted({row["processes"] for row in rows})
    size_text = ", ".join(f"{m}x{n}" for m, n in sizes)
    time_images = "\n\n".join(f"![Tempo {m}x{n}](tempo_{m}x{n}.png)" for m, n in sizes)

    report = f"""# Tarefa 18 - Produto matriz-vetor com tipos derivados MPI

## Objetivo

Reimplementar o produto `y = A * x` da Tarefa 17, mas agora distribuindo colunas da
matriz entre os processos. Cada processo recebe um bloco de colunas de `A` e o
segmento correspondente de `x`, calcula uma contribuicao parcial para todos os
elementos de `y`, e o processo `0` recebe a soma final com `MPI_Reduce` e `MPI_SUM`.

Foram feitas duas versoes:

- `cols_vector`: usa `MPI_Type_vector` para representar um bloco de colunas.
- `cols_resized`: usa `MPI_Type_vector` e depois `MPI_Type_create_resized` para
  ajustar a extensao do tipo derivado.

## Funcoes MPI usadas

- `MPI_Type_vector`: cria um tipo derivado para selecionar, em cada linha, um bloco
  de colunas. O parametro `count` representa o numero de linhas, `blocklength`
  representa o numero de colunas locais e `stride` e o tamanho total da linha `N`.
- `MPI_Type_create_resized`: altera a extensao do tipo derivado para que o proximo
  bloco enviado por `MPI_Scatter` comece logo na proxima coluna do bloco anterior.
- `MPI_Type_commit`: registra o tipo derivado antes do uso.
- `MPI_Type_free`: libera os tipos derivados ao final.
- `MPI_Scatter`: distribui os blocos de colunas da matriz e os segmentos do vetor
  `x`.
- `MPI_Reduce` com `MPI_SUM`: soma os vetores parciais `y_parcial` e forma o vetor
  final `y` no processo `0`.
- `MPI_Barrier`: alinha os processos antes do trecho medido.

## Configuracao

- Tamanhos de matriz testados: `{size_text}`
- Processos MPI testados: `{", ".join(str(p) for p in processes)}`
- Rodadas por configuracao: `{max(row['rep'] for row in rows)}`
- Compilacao sequencial: `gcc -O3 -Wall -Wextra`
- Compilacao MPI: `mpicc -O3 -Wall -Wextra`
- Medicao de tempo: `MPI_Wtime` nas versoes MPI e `gettimeofday` na versao
  sequencial da Tarefa 17

Os valores de `N` foram escolhidos divisiveis por `1`, `2` e `4`, pois a divisao por
colunas usa `MPI_Scatter` simples. O checksum foi comparado com a versao sequencial
para validar o resultado.

## Resultados da Tarefa 18

{table(summary, "Colunas")}

## Comparacao com a Tarefa 17

{comparison_table(t17_summary, summary)}

## Graficos

![Speedup](speedup.png)

{time_images}

## Melhores casos

{best_lines(summary)}

## Analise

Na Tarefa 17, a matriz foi distribuida por linhas. Esse caso combina bem com o layout
padrao de matrizes em C, que armazena os elementos em ordem por linhas. Assim, cada
processo recebe linhas completas e contiguas de memoria, calcula diretamente os
elementos correspondentes de `y` e depois usa `MPI_Gather` para reunir o resultado.

Na Tarefa 18, a divisao e por colunas. Como as colunas nao ficam contiguas em uma
matriz `M x N` armazenada por linhas, foi necessario usar tipo derivado. O
`MPI_Type_vector` descreve esse padrao nao contiguo: em cada linha, ele seleciona
`colunas_por_processo` elementos e pula `N` posicoes para chegar ao proximo bloco da
linha seguinte.

A versao `cols_vector` mostra uma limitacao importante. O tipo criado por
`MPI_Type_vector` tem uma extensao natural que vai do primeiro elemento do bloco ate
o final do ultimo bloco, incluindo os espacos entre as linhas. Quando esse tipo e
usado diretamente em `MPI_Scatter`, o MPI avanca de um processo para o proximo usando
essa extensao. Por isso, o processo `0` precisa preparar um buffer com espacamento
entre os blocos de cada processo. A comunicacao ainda usa o tipo derivado, mas ha
custo extra de memoria e preparacao. Essa preparacao ocorre antes do trecho medido
no script de testes, mas ainda e uma diferenca importante da implementacao.

A versao `cols_resized` corrige esse problema. Depois de criar o tipo com
`MPI_Type_vector`, `MPI_Type_create_resized` define a extensao como
`colunas_por_processo * sizeof(double)`. Com isso, no `MPI_Scatter`, o bloco do
processo seguinte comeca na proxima coluna do bloco anterior. Essa versao consegue
usar a matriz em seu layout normal no processo `0`, sem criar um buffer artificial
com lacunas.

Mesmo com `resized`, a distribuicao por colunas tende a ter desempenho diferente da
distribuicao por linhas. Cada processo calcula uma contribuicao parcial para todos os
elementos de `y`, entao cada processo escreve um vetor parcial de tamanho `M`. No
fim, `MPI_Reduce` soma esses vetores parciais. Isso contrasta com a Tarefa 17, em
que cada processo calcula apenas algumas linhas finais de `y` e o processo `0`
apenas junta os blocos com `MPI_Gather`.

O acesso a memoria local tambem muda. Depois do recebimento, os blocos locais foram
guardados em memoria contigua para simplificar o calculo. Ainda assim, a etapa de
envio a partir do processo `0` precisa ler a matriz em padrao de colunas, ou seja,
com saltos entre linhas. Esse padrao costuma ser menos favoravel para cache do que
enviar linhas contiguas.

Nos resultados medidos, `cols_vector` e `cols_resized` ficaram proximas. Isso ocorre
porque as duas usam o mesmo padrao de comunicacao principal: `MPI_Scatter` para a
matriz, `MPI_Scatter` para o segmento de `x` e `MPI_Reduce` para somar `y`. A
diferenca principal entre elas esta na organizacao do buffer no processo `0`, nao no
calculo local. A versao com `resized` e mais direta e representa melhor o layout real
da matriz, mesmo quando o tempo medido fica parecido.

Comparando com a Tarefa 17, os tempos ficaram na mesma ordem de grandeza. Em alguns
casos com 2 e 4 processos, as versoes por colunas ficaram levemente mais rapidas que
a versao por linhas medida na Tarefa 17. Isso nao significa que colunas sejam sempre
melhores; neste ambiente local, o custo das coletivas e a variacao de execucao podem
pesar bastante. A diferenca estrutural continua sendo que a Tarefa 17 distribui
partes finais de `y`, enquanto a Tarefa 18 exige uma reducao completa de um vetor de
tamanho `M`.

## Conclusao

A Tarefa 18 evidencia por que tipos derivados sao uteis em MPI. Eles permitem
descrever blocos nao contiguos da matriz sem empacotar manualmente cada elemento.
`MPI_Type_vector` e suficiente para representar o desenho das colunas, mas sua
extensao natural atrapalha o uso direto com multiplos blocos em `MPI_Scatter`.

`MPI_Type_create_resized` resolve esse ponto ao redefinir a extensao do tipo
derivado. Por isso, a versao `cols_resized` representa melhor a solucao esperada para
espalhar blocos de colunas de uma matriz armazenada por linhas.

Comparada com a Tarefa 17, a divisao por colunas tem uma comunicacao final mais
pesada, pois usa `MPI_Reduce` em um vetor de tamanho `M`, e nao apenas uma reuniao
dos pedacos finais de `y`. Ela tambem exige acesso nao contiguo na matriz original.
Assim, a distribuicao por linhas tende a ser mais natural para o produto
matriz-vetor em C, enquanto a distribuicao por colunas serve para demonstrar bem o
uso de tipos derivados.

## Codigos

{code_sections()}

## Artefatos

- Codigo com `MPI_Type_vector`: `Tarefa-18/matvec_cols_vector.c`
- Codigo com `MPI_Type_create_resized`: `Tarefa-18/matvec_cols_resized.c`
- Coleta: `Tarefa-18/coletar_mpi.py`
- CSV: `Tarefa-18/resultados/tarefa18_resultados.csv`
- Graficos: `Tarefa-18/resultados/speedup.png` e `Tarefa-18/resultados/tempo_*.png`
- Relatorio: `Tarefa-18/resultados/relatorio_tarefa18.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows(CSV_FILE)
    summary = aggregate(rows)
    t17_summary = aggregate(load_rows(T17_CSV)) if T17_CSV.exists() else []
    generate_report(rows, summary, t17_summary)


if __name__ == "__main__":
    main()
