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

Nesta sessao local nao foi possivel executar em um no GPU do NPAD. A pasta
foi deixada com o procedimento reprodutivel para gerar os tempos no ambiente
solicitado. Ao final do job, o arquivo
`Tarefa-19/resultados/tarefa19_resultados_<jobid>.csv` trara linhas no formato:

```text
variant,device,n,repeats,best_compute_s,avg_compute_s,init_s,verify_s,errors,omp_threads,omp_devices
cpu,host,...
gpu,openmp-target,...
```

Nos dois programas ha uma execucao de aquecimento antes das repeticoes
medidas. Na versao GPU, o tempo de soma medido inclui a regiao `target` com
as transferencias definidas pelas clausulas `map`.

Depois da execucao no NPAD, a comparacao deve ser preenchida com:

| Variante | Melhor tempo de soma (s) | Tempo medio de soma (s) | Erros |
| --- | ---: | ---: | ---: |
| CPU | a preencher pelo CSV | a preencher pelo CSV | a preencher pelo CSV |
| GPU | a preencher pelo CSV | a preencher pelo CSV | a preencher pelo CSV |

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
5. A comparacao de tempos ainda depende da execucao no no GPU do NPAD, que
   nao esta disponivel neste ambiente local.
