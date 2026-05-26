import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa14_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa14.md"


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["rep"] = int(row["rep"])
            row["bytes"] = int(row["bytes"])
            row["iterations"] = int(row["iterations"])
            for key in [
                "total_seconds",
                "avg_roundtrip_seconds",
                "one_way_latency_seconds",
                "bandwidth_mib_s",
            ]:
                row[key] = float(row[key])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["method"], row["bytes"], row["iterations"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        roundtrip = [row["avg_roundtrip_seconds"] for row in values]
        latency = [row["one_way_latency_seconds"] for row in values]
        bandwidth = [row["bandwidth_mib_s"] for row in values]
        summary.append({
            "method": key[0],
            "bytes": key[1],
            "iterations": key[2],
            "runs": len(values),
            "mean_roundtrip": statistics.mean(roundtrip),
            "min_roundtrip": min(roundtrip),
            "max_roundtrip": max(roundtrip),
            "mean_latency": statistics.mean(latency),
            "mean_bandwidth": statistics.mean(bandwidth),
        })
    return summary


def table(summary):
    lines = [
        "|Funcao|Bytes|Iteracoes|Rodadas|Ida e volta medio (us)|Latencia estimada (us)|Banda efetiva (MiB/s)|",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['method']}|{row['bytes']}|{row['iterations']}|{row['runs']}|"
            f"{row['mean_roundtrip'] * 1e6:.3f}|"
            f"{row['mean_latency'] * 1e6:.3f}|"
            f"{row['mean_bandwidth']:.2f}|"
        )
    return "\n".join(lines)


def method_extremes(summary):
    lines = []
    methods = sorted({row["method"] for row in summary})
    for method in methods:
        data = [row for row in summary if row["method"] == method]
        small = min(data, key=lambda row: row["bytes"])
        large = max(data, key=lambda row: row["bytes"])
        lines.append(
            f"- `{method}`: menor mensagem {small['bytes']} bytes com "
            f"{small['mean_roundtrip'] * 1e6:.3f} us de ida e volta; maior mensagem "
            f"{large['bytes']} bytes com banda efetiva de {large['mean_bandwidth']:.2f} MiB/s."
        )
    return "\n".join(lines)


def best_large_message(summary):
    largest = max(row["bytes"] for row in summary)
    candidates = [row for row in summary if row["bytes"] == largest]
    return max(candidates, key=lambda row: row["mean_bandwidth"])


def generate_report(rows, summary):
    sizes = sorted({row["bytes"] for row in rows})
    largest_best = best_large_message(summary)
    report = f"""# Tarefa 14 - Comunicacao MPI

## Objetivo

Implementar quatro benchmarks MPI com exatamente dois processos. O processo 0 envia
uma mensagem ao processo 1 e o processo 1 devolve imediatamente a mesma mensagem. O
tempo e medido com `MPI_Wtime` durante varias trocas consecutivas.

## Implementacoes

- `MPI_Send`: envio bloqueante padrao. A chamada pode completar quando a mensagem foi
  copiada para um buffer interno do MPI ou quando o recebimento correspondente avancou.
- `MPI_Bsend`: envio bloqueante com buffer anexado pelo usuario por `MPI_Buffer_attach`.
  A chamada depende de haver espaco no buffer fornecido para armazenar a mensagem.
- `MPI_Rsend`: envio em modo ready. Ele so e correto se o recebimento correspondente
  ja tiver sido iniciado. Nesta versao introdutoria, foram usadas mensagens simples
  de controle com `MPI_Send` e `MPI_Recv` para indicar que o processo receptor esta
  pronto para a troca.
- `MPI_Ssend`: envio bloqueante sincrono. A chamada so completa quando o processo
  receptor iniciou o recebimento correspondente, expondo melhor o custo de sincronizacao.

Todos os programas usam `MPI_Recv` para receber a mensagem de ida e a resposta. O
tempo e medido no processo 0, que participa de todas as trocas completas.

## Configuracao

- Processos MPI: `2`
- Tamanhos testados: `{", ".join(str(size) for size in sizes)} bytes`
- Repeticoes por tamanho e funcao: `{max(row['rep'] for row in rows)}`
- Metrica principal: tempo medio de ida e volta por mensagem
- Latencia estimada: metade do tempo medio de ida e volta
- Largura de banda efetiva: bytes enviados na ida e na volta divididos pelo tempo total

O codigo foi mantido propositalmente simples, usando comunicacao ponto a ponto:
`MPI_Send`, `MPI_Bsend`, `MPI_Rsend`, `MPI_Ssend`, `MPI_Recv` e `MPI_Wtime`. Nao foram
usadas rotinas coletivas.

## Resultados

{table(summary)}

## Graficos

![Tempo por tamanho](tempo_por_tamanho.png)

![Largura de banda](largura_banda.png)

## Analise

Para mensagens pequenas, o tempo varia pouco com o tamanho da mensagem. Esse e o
regime dominado por latencia: custo de chamada MPI, sincronizacao entre processos,
progresso do runtime e passagem pelos buffers internos pesam mais do que copiar os
bytes da mensagem.

Quando o tamanho cresce, a curva de tempo passa a aumentar de forma mais clara. Esse
e o regime dominado por largura de banda: a transferencia de dados e as copias de
memoria passam a representar a maior parte do custo. Nesse regime, a comparacao mais
importante deixa de ser apenas o tempo absoluto e passa a ser a banda efetiva obtida.

Nos dados coletados, para a maior mensagem testada o melhor caso de banda foi
`{largest_best['method']}`, com `{largest_best['mean_bandwidth']:.2f} MiB/s` em
mensagens de `{largest_best['bytes']}` bytes.

Resumo por funcao:

{method_extremes(summary)}

## Artefatos

- Codigos: `Tarefa-14/mpi_send.c`, `Tarefa-14/mpi_bsend.c`,
  `Tarefa-14/mpi_rsend.c` e `Tarefa-14/mpi_ssend.c`
- Coleta: `Tarefa-14/coletar_mpi.py`
- CSV: `Tarefa-14/resultados/tarefa14_resultados.csv`
- Graficos: `Tarefa-14/resultados/tempo_por_tamanho.png` e
  `Tarefa-14/resultados/largura_banda.png`
- Relatorio: `Tarefa-14/resultados/relatorio_tarefa14.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Relatorio salvo em: {REPORT_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
