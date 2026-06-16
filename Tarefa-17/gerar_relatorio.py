import csv
import statistics
import textwrap
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "resultados" / "tarefa17_resultados.csv"
REPORT_FILE = ROOT / "resultados" / "relatorio_tarefa17.md"
PDF_FILE = ROOT / "resultados" / "relatorio_tarefa17.pdf"
CODE_FILES = ["matvec_seq.c", "matvec_collective.c"]
COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]


def load_rows():
    rows = []
    with CSV_FILE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for key in ["rep", "m", "n", "processes", "rows_per_process"]:
                row[key] = int(row[key])
            for key in [
                "seq_time",
                "total_time",
                "bcast_time",
                "scatter_time",
                "compute_time",
                "gather_time",
                "reduce_time",
                "speedup_seq",
                "efficiency_seq",
                "speedup_mpi",
                "efficiency_mpi",
                "checksum",
            ]:
                row[key] = float(row[key])
            rows.append(row)
    return rows


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["m"], row["n"], row["processes"])].append(row)

    summary = []
    for key, values in sorted(groups.items()):
        total_times = [row["total_time"] for row in values]
        summary.append({
            "m": key[0],
            "n": key[1],
            "processes": key[2],
            "rows_per_process": values[0]["rows_per_process"],
            "runs": len(values),
            "seq_time": values[0]["seq_time"],
            "mean_total": statistics.mean(total_times),
            "min_total": min(total_times),
            "max_total": max(total_times),
            "bcast_time": statistics.mean(row["bcast_time"] for row in values),
            "scatter_time": statistics.mean(row["scatter_time"] for row in values),
            "compute_time": statistics.mean(row["compute_time"] for row in values),
            "gather_time": statistics.mean(row["gather_time"] for row in values),
            "reduce_time": statistics.mean(row["reduce_time"] for row in values),
            "speedup_seq": statistics.mean(row["speedup_seq"] for row in values),
            "efficiency_seq": statistics.mean(row["efficiency_seq"] for row in values),
            "speedup_mpi": statistics.mean(row["speedup_mpi"] for row in values),
            "efficiency_mpi": statistics.mean(row["efficiency_mpi"] for row in values),
            "checksum": values[0]["checksum"],
        })
    return summary


def table(summary):
    lines = [
        "|M|N|Versao|Proc.|Linhas/proc.|Rodadas|Tempo medio (s)|Speedup seq|Efic. seq|Speedup MPI|Efic. MPI|Checksum|",
        "|---:|---:|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    current_size = None
    for row in summary:
        size = (row["m"], row["n"])
        if size != current_size:
            lines.append(
                f"|{row['m']}|{row['n']}|Sequencial|-|-|1|{row['seq_time']:.6f}|"
                f"1.00|1.00|-|-|{row['checksum']:.2f}|"
            )
            current_size = size
        lines.append(
            f"|{row['m']}|{row['n']}|MPI|{row['processes']}|{row['rows_per_process']}|"
            f"{row['runs']}|{row['mean_total']:.6f}|"
            f"{row['speedup_seq']:.2f}|{row['efficiency_seq']:.2f}|"
            f"{row['speedup_mpi']:.2f}|{row['efficiency_mpi']:.2f}|{row['checksum']:.2f}|"
        )
    return "\n".join(lines)


def timing_table(summary):
    lines = [
        "|M|N|Proc.|Bcast (s)|Scatter (s)|Calculo (s)|Gather (s)|Reduce (s)|",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"|{row['m']}|{row['n']}|{row['processes']}|"
            f"{row['bcast_time']:.6f}|{row['scatter_time']:.6f}|"
            f"{row['compute_time']:.6f}|{row['gather_time']:.6f}|"
            f"{row['reduce_time']:.6f}|"
        )
    return "\n".join(lines)


def best_lines(summary):
    groups = defaultdict(list)
    for row in summary:
        groups[(row["m"], row["n"])].append(row)

    lines = []
    for key in sorted(groups):
        best = min(groups[key], key=lambda row: row["mean_total"])
        seq_time = best["seq_time"]
        seq_factor = best["mean_total"] / seq_time
        lines.append(
            f"- Matriz {key[0]}x{key[1]}: melhor tempo MPI com {best['processes']} processos, "
            f"media {best['mean_total']:.6f}s, speedup seq {best['speedup_seq']:.2f}, "
            f"speedup MPI {best['speedup_mpi']:.2f}. A base sequencial foi {seq_time:.6f}s "
            f"(speedup 1.00), ficando {seq_factor:.2f}x mais rapida que esse melhor MPI."
        )
    return "\n".join(lines)


def write_svg_chart(summary, filename, metric, ylabel, title):
    width = 900
    height = 560
    margin_left = 82
    margin_right = 190
    margin_top = 62
    margin_bottom = 76
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    sizes = sorted({(row["m"], row["n"]) for row in summary})
    processes = sorted({row["processes"] for row in summary})
    values = [row[metric] for row in summary]
    show_seq_reference = metric in {"speedup_seq", "efficiency_seq"}
    max_value = max(values) if values else 1.0
    y_max = max(1.15 if show_seq_reference else 1.0, max_value * 1.15)

    def x_pos(process):
        if len(processes) == 1:
            return margin_left + plot_w / 2
        return margin_left + (processes.index(process) / (len(processes) - 1)) * plot_w

    def y_pos(value):
        return margin_top + plot_h - (value / y_max) * plot_h

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" font-weight="700">{title}</text>',
        f'<text x="{width / 2}" y="{height - 22}" text-anchor="middle" font-family="Arial, sans-serif" font-size="15">Processos MPI</text>',
        f'<text x="22" y="{margin_top + plot_h / 2}" text-anchor="middle" transform="rotate(-90 22 {margin_top + plot_h / 2})" font-family="Arial, sans-serif" font-size="15">{ylabel}</text>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#222" stroke-width="1.5"/>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#222" stroke-width="1.5"/>',
    ]

    for i in range(6):
        value = y_max * i / 5
        y = y_pos(value)
        elements.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_w}" y2="{y:.2f}" stroke="#ddd" stroke-width="1"/>')
        elements.append(f'<text x="{margin_left - 10}" y="{y + 5:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12">{value:.2f}</text>')

    for process in processes:
        x = x_pos(process)
        elements.append(f'<line x1="{x:.2f}" y1="{margin_top + plot_h}" x2="{x:.2f}" y2="{margin_top + plot_h + 6}" stroke="#222" stroke-width="1"/>')
        elements.append(f'<text x="{x:.2f}" y="{margin_top + plot_h + 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13">{process}</text>')

    if show_seq_reference:
        y = y_pos(1.0)
        elements.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_w}" y2="{y:.2f}" stroke="#555" stroke-width="2" stroke-dasharray="6 5"/>')
        elements.append(f'<text x="{margin_left + plot_w - 8}" y="{y - 8:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#333">Sequencial = 1,00</text>')

    for idx, size in enumerate(sizes):
        color = COLORS[idx % len(COLORS)]
        rows = [row for row in summary if row["m"] == size[0] and row["n"] == size[1]]
        rows = sorted(rows, key=lambda row: row["processes"])
        points = " ".join(f'{x_pos(row["processes"]):.2f},{y_pos(row[metric]):.2f}' for row in rows)
        elements.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{points}"/>')
        for row in rows:
            elements.append(f'<circle cx="{x_pos(row["processes"]):.2f}" cy="{y_pos(row[metric]):.2f}" r="4.5" fill="{color}"/>')
        legend_y = margin_top + 24 + idx * 24
        elements.append(f'<rect x="{margin_left + plot_w + 34}" y="{legend_y - 12}" width="15" height="15" fill="{color}"/>')
        elements.append(f'<text x="{margin_left + plot_w + 58}" y="{legend_y}" font-family="Arial, sans-serif" font-size="13">{size[0]}x{size[1]}</text>')

    elements.append("</svg>")
    (ROOT / "resultados" / filename).write_text("\n".join(elements), encoding="utf-8")


def write_charts(summary):
    write_svg_chart(summary, "speedup.svg", "speedup_seq", "Speedup contra sequencial", "Speedup seq - produto matriz-vetor")
    write_svg_chart(summary, "eficiencia.svg", "efficiency_seq", "Eficiencia contra sequencial", "Eficiencia seq - produto matriz-vetor")
    write_svg_chart(summary, "speedup_mpi.svg", "speedup_mpi", "Speedup interno MPI", "Speedup MPI - produto matriz-vetor")
    write_svg_chart(summary, "eficiencia_mpi.svg", "efficiency_mpi", "Eficiencia interna MPI", "Eficiencia MPI - produto matriz-vetor")


def code_sections():
    sections = []
    for filename in CODE_FILES:
        code = (ROOT / filename).read_text(encoding="utf-8").rstrip()
        sections.append(f"### `{filename}`\n\n```c\n{code}\n```")
    return "\n\n".join(sections)


def pdf_escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(text):
    page_width = 595
    page_height = 842
    left = 40
    top = 805
    font_size = 8
    line_height = 10
    max_chars = 108
    max_lines = int((top - 45) / line_height)

    lines = []
    for original in text.splitlines():
        if original == "":
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            original,
            width=max_chars,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        lines.extend(wrapped or [""])

    pages = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
    objects = []

    def add_object(content):
        objects.append(content)
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object("")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    page_ids = []

    for page_lines in pages:
        stream_lines = ["BT", f"/F1 {font_size} Tf", f"{left} {top} Td"]
        for idx, line in enumerate(page_lines):
            if idx > 0:
                stream_lines.append(f"0 -{line_height} Td")
            stream_lines.append(f"({pdf_escape(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        stream_id = add_object(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")
        page_id = add_object(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {stream_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    )

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_id, content in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{obj_id} 0 obj\n{content}\nendobj\n".encode("latin-1"))

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
    )
    PDF_FILE.write_bytes(output)


def generate_report(rows, summary):
    sizes = sorted({(row["m"], row["n"]) for row in rows})
    processes = sorted({row["processes"] for row in rows})
    size_text = ", ".join(f"{m}x{n}" for m, n in sizes)
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
- `MPI_Reduce`: soma os checksums locais e tambem agrega os tempos locais com
  `MPI_MAX` para representar o processo mais lento.

Tambem foram usadas as rotinas basicas ja vistas antes: `MPI_Init`,
`MPI_Comm_rank`, `MPI_Comm_size`, `MPI_Wtime` e `MPI_Finalize`.

Como o enunciado pede `MPI_Scatter`, foi usada a divisao simples em que `M` deve ser
divisivel pelo numero de processos. Os testes foram escolhidos respeitando essa
condicao.

## Configuracao

- Tamanhos de matriz testados: `{size_text}`
- Processos MPI testados: `{", ".join(str(p) for p in processes)}`
- Rodadas por configuracao: `{max(row['rep'] for row in rows)}`
- Compilacao sequencial: `gcc -O3 -Wall -Wextra -fopenmp`
- Compilacao MPI: `mpicc -O3 -Wall -Wextra`
- Medicao de tempo: `MPI_Wtime` na versao MPI e `omp_get_wtime` na versao sequencial

O checksum do vetor `y` foi comparado entre as versoes para validar os resultados.
O tempo MPI reportado e o maior tempo local entre os processos, calculado com
`MPI_Reduce` e `MPI_MAX`.

Foram calculados dois tipos de speedup:

- A linha `Sequencial` e a base da comparacao, portanto tem `speedup_seq = 1.00` e
  `eficiencia_seq = 1.00`.
- `speedup_seq = tempo_sequencial / tempo_mpi_total`
- `speedup_mpi = tempo_mpi_1_processo / tempo_mpi_p_processos`

## Resultados

{table(summary)}

## Tempos parciais medios

{timing_table(summary)}

## Graficos

![Speedup contra sequencial](speedup.svg)

![Eficiencia contra sequencial](eficiencia.svg)

![Speedup interno MPI](speedup_mpi.svg)

![Eficiencia interna MPI](eficiencia_mpi.svg)

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

O `speedup_seq` compara a estrategia MPI completa contra o programa sequencial, que
aparece na tabela como a base `1.00`. Se uma linha MPI fica menor que 1, isso
significa que a versao MPI completa ficou mais lenta que a sequencial. O motivo
principal e que o programa sequencial mede apenas a multiplicacao local, enquanto a
versao MPI tambem precisa distribuir o vetor, distribuir a matriz, reunir o
resultado e sincronizar os processos.

O `speedup_mpi` compara a propria implementacao MPI com 1 processo contra a mesma
implementacao com mais processos. Esse valor mostra a escalabilidade interna da
versao paralela, separada da comparacao com o programa sequencial.

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

`MPI_Reduce` foi usado para validar o resultado. Cada processo calcula um checksum
local somando os valores do seu bloco de `y`. Em seguida, `MPI_Reduce` aplica a soma
e entrega o checksum global ao processo `0`. Essa chamada movimenta apenas um valor
por processo, entao seu custo e bem menor que o de distribuir a matriz com
`MPI_Scatter`. Mesmo assim, ela tambem e uma coletiva e acrescenta sincronizacao no
fim da execucao medida.

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

Pelos testes, a paralelizacao com MPI deve ser analisada em duas camadas. A primeira
e a comparacao contra a versao sequencial (`speedup_seq`), que inclui todo o custo da
estrategia MPI. A segunda e a escalabilidade interna da propria versao paralela
(`speedup_mpi`), que mostra o efeito de aumentar o numero de processos mantendo a
mesma organizacao MPI.

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
- Graficos: `Tarefa-17/resultados/speedup.svg` e
  `Tarefa-17/resultados/eficiencia.svg`
- Graficos MPI: `Tarefa-17/resultados/speedup_mpi.svg` e
  `Tarefa-17/resultados/eficiencia_mpi.svg`
- Relatorio: `Tarefa-17/resultados/relatorio_tarefa17.md`
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    write_simple_pdf(report)
    print(f"Relatorio salvo em: {REPORT_FILE}")
    print(f"PDF salvo em: {PDF_FILE}")


def main():
    rows = load_rows()
    summary = aggregate(rows)
    write_charts(summary)
    generate_report(rows, summary)


if __name__ == "__main__":
    main()
