# Tarefa 19 - Adicao de vetores com OpenMP em CPU e GPU

## Objetivo

O objetivo foi reproduzir os exercicios `vadd.c` indicados no tutorial
`conteudos/omp_GPGPU_prog_SC23.pdf`: primeiro a versao paralela em CPU,
com `#pragma omp parallel for`, e depois a versao com offload para GPU,
com `#pragma omp target` seguido de `#pragma omp loop`.

## Implementacao

Foram criados dois programas:

- `vadd_cpu.c`: inicializa tres vetores no host, executa a soma
  `c[i] = a[i] + b[i]` com `#pragma omp parallel for` e valida o
  resultado.
- `vadd_gpu.c`: usa a mesma inicializacao e validacao, mas executa a soma
  em uma regiao `target`. Como os vetores sao alocados dinamicamente, foram
  adicionadas clausulas `map(to: a[0:n], b[0:n])` e `map(from: c[0:n])`.

A mudanca para alocacao dinamica evita estouro de pilha para valores grandes
de `N` e permite variar o tamanho do problema sem recompilar.

## Como executar no NPAD

```bash
sbatch Tarefa-19/run_npad.sbatch
```

O script `run_npad.sbatch` usa:

- particao: `gpu-8-v100`;
- GPU por no: `1`;
- compilador: `compilers/nvidia/nvhpc/24.11`;
- CPU: `nvc -fast -mp`;
- GPU: `nvc -fast -mp=gpu`;
- variavel: `OMP_TARGET_OFFLOAD=MANDATORY`.

O uso de `OMP_TARGET_OFFLOAD=MANDATORY` foi adotado para impedir que a
execucao GPU caia silenciosamente para CPU quando o dispositivo ou o suporte
de offload nao estiverem disponiveis.

## Comparacao de tempos

A execucao foi realizada no NPAD e os dados foram registrados em
`Tarefa-19/resultados/tarefa19_resultados_1858301.csv`. Nos dois programas ha uma
execucao de aquecimento antes das repeticoes medidas. Na versao GPU, o tempo da soma
inclui a entrada e saida da regiao `target` e as transferencias determinadas pelas
clausulas `map`.

| Variante | Dispositivo | N | Repeticoes | Melhor soma (s) | Media soma (s) | Inicializacao (s) | Validacao (s) | Erros | Threads | Devices |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CPU | host | 100000000 | 5 | 0.107329130 | 0.108146763 | 0.501634121 | 0.103204966 | 0 | 1 | 0 |
| GPU | openmp-target | 100000000 | 5 | 0.125133038 | 0.125197220 | 0.494171143 | 0.101060152 | 0 | 1 | 1 |

Com base no tempo medio da soma, o speedup GPU em relacao a CPU foi:

```text
speedup = 0.108146763 / 0.125197220 = 0.864x
```

Portanto, neste caso a GPU ficou aproximadamente 15,8% mais lenta que a CPU de
referencia. Isso nao indica erro de implementacao: todas as execucoes terminaram com
`errors = 0`. O resultado mostra que, para essa versao simples do exercicio, o custo
de entrada/saida da regiao `target` e das copias associadas ao `map` ainda pesa
bastante. A linha CPU foi medida com `OMP_NUM_THREADS=1`, entao ela representa uma
CPU com uma thread OpenMP, nao uma comparacao contra toda a capacidade multicore do
no.

## Graficos

Os graficos gerados a partir do CSV estao abaixo.

![Tempo de computacao](resultados/tempo_computacao.png)

![Speedup GPU vs CPU](resultados/speedup_gpu_vs_cpu.png)

![Componentes do tempo total](resultados/componentes_tempo_total.png)

## Progresso, problemas e solucoes

1. O enunciado referencia os slides 27 e 48, mas a numeracao fisica do PDF
   nao coincide diretamente com os slides. O texto do PDF foi pesquisado por
   `vadd.c`, identificando os exercicios "Simple vector add in OpenMP on CPU"
   e "Parallel vector addition on a GPU".
2. A solucao do slide usa arrays automaticos. Para `N` grande, isso pode
   exceder a pilha. A solucao adotada usa `malloc` e libera a memoria ao fim.
3. Com arrays alocados no heap, o offload precisa de mapeamento explicito de
   secoes dos vetores. Por isso a versao GPU usa `map(to: a[0:n], b[0:n])`
   e `map(from: c[0:n])`.
4. Para garantir que a execucao realmente use GPU, o script SLURM exporta
   `OMP_TARGET_OFFLOAD=MANDATORY`.
5. A execucao no NPAD produziu `omp_devices = 1` para a variante GPU, confirmando
   que havia dispositivo OpenMP alvo disponivel.
6. A GPU nao superou a CPU nesta medicao porque a versao do exercicio ainda inclui
   overhead de offload e transferencias. Uma evolucao natural e manter dados
   residentes na GPU, como proposto na tarefa seguinte sobre otimizacao de
   transferencia.
