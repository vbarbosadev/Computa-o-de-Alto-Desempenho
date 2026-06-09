# Tarefa 19 - Adicao de vetores com OpenMP em GPU

## Objetivo

Executar os exercicios de adicao de vetores `vadd.c` indicados nos slides 27 e 48
do tutorial de programacao de GPUs com OpenMP. A atividade compara duas versoes:

- `vadd_cpu.c`: soma dos vetores somente na CPU, usando `#pragma omp parallel for`.
- `vadd_gpu.c`: soma dos vetores com offload para GPU, usando `#pragma omp target`
  seguido de `#pragma omp loop`.

O objetivo principal foi medir o tempo de execucao da soma em CPU e GPU em um no com
GPU do NPAD e registrar os problemas encontrados durante a adaptacao.

## Implementacao

As duas versoes inicializam tres vetores `a`, `b` e `c`, executam a soma
`c[i] = a[i] + b[i]` e validam o resultado ao final. A validacao compara cada
elemento calculado com o valor esperado e contabiliza erros numericos.

A versao dos slides usa vetores automaticos. Nesta implementacao, os vetores foram
alocados dinamicamente com `malloc`. Essa mudanca evita estouro de pilha para
tamanhos grandes e permite variar `N` pela linha de comando sem recompilar o
programa.

Na versao GPU, como os vetores estao no heap, foram usadas clausulas explicitas de
mapeamento:

```c
#pragma omp target map(to : a[0:n], b[0:n]) map(from : c[0:n])
#pragma omp loop
```

Assim, `a` e `b` sao enviados para o dispositivo e `c` retorna para o host apos a
regiao `target`.

## Configuracao

- Ambiente de execucao: no com GPU do NPAD
- Particao SLURM: `gpu-8-v100`
- GPUs por no: `1`
- Compilador: `compilers/nvidia/nvhpc/24.11`
- Compilacao CPU: `nvc -fast -mp`
- Compilacao GPU: `nvc -fast -mp=gpu`
- Tamanho do vetor: `100000000`
- Repeticoes medidas: `5`
- Threads OpenMP registradas: `1`
- Variavel de ambiente: `OMP_TARGET_OFFLOAD=MANDATORY`

O uso de `OMP_TARGET_OFFLOAD=MANDATORY` impede que a execucao da versao GPU caia
silenciosamente para CPU caso o dispositivo ou o suporte de offload nao estejam
disponiveis. A linha GPU registrou `omp_devices = 1`, confirmando que havia um
dispositivo OpenMP disponivel.

## Resultados

Os dados foram lidos de `Tarefa-19/resultados/tarefa19_resultados_1858301.csv`.

| Variante | Dispositivo | N | Repeticoes | Melhor soma (s) | Media soma (s) | Inicializacao (s) | Validacao (s) | Total aprox. (s) | Erros | Threads | Devices |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CPU | host | 100000000 | 5 | 0.107329130 | 0.108146763 | 0.501634121 | 0.103204966 | 0.712985850 | 0 | 1 | 0 |
| GPU | openmp-target | 100000000 | 5 | 0.125133038 | 0.125197220 | 0.494171143 | 0.101060152 | 0.720428515 | 0 | 1 | 1 |

## Graficos

![Tempo de computacao](tarefa19_tempo_computacao.png)

![Speedup GPU vs CPU](tarefa19_speedup_gpu_vs_cpu.png)

![Componentes do tempo total](tarefa19_componentes_tempo_total.png)

## Analise

A validacao terminou com `errors = 0` nas duas versoes, portanto a soma dos vetores
foi calculada corretamente tanto na CPU quanto na GPU.

Considerando o tempo medio da soma, a CPU levou `0.108146763s`, enquanto a GPU levou
`0.125197220s`. O speedup relativo da GPU em relacao a CPU foi:

```text
speedup = tempo_cpu / tempo_gpu = 0.108146763 / 0.125197220 = 0.864
```

Como o valor ficou abaixo de `1.0`, a GPU foi mais lenta nessa execucao. A diferenca
foi de aproximadamente `15.8%` a mais de tempo para a versao GPU no trecho medido da
soma.

Esse resultado e coerente com a forma como o programa foi medido. Na versao GPU, o
tempo da soma inclui a entrada e saida da regiao `target`, alem das transferencias
definidas pelas clausulas `map`. Para uma operacao simples como adicao de vetores,
cada elemento exige pouco calculo: sao basicamente duas leituras, uma soma e uma
escrita. Assim, o custo de movimentar dados entre host e dispositivo pode ficar maior
que o ganho obtido pela paralelizacao massiva da GPU.

Outro ponto importante e que a execucao registrada usou `OMP_NUM_THREADS=1`. Portanto,
a linha CPU representa a execucao com uma thread OpenMP, nao uma comparacao contra
uma CPU usando todos os nucleos disponiveis. Mesmo assim, para este caso especifico,
a CPU ficou mais rapida que a GPU porque a operacao tem baixa intensidade
aritmetica e a regiao `target` precisa pagar o custo de offload.

O tempo total aproximado tambem ficou muito proximo: `0.712985850s` na CPU e
`0.720428515s` na GPU. Isso mostra que inicializacao e validacao dominaram boa parte
do tempo total do programa, enquanto a diferenca principal analisada ficou no trecho
da soma.

## Progresso, problemas e solucoes

O primeiro problema foi identificar os exercicios corretos no material, pois a
numeracao fisica do PDF nao coincide diretamente com a numeracao dos slides. A busca
por `vadd.c` no tutorial permitiu localizar os exemplos de adicao de vetores em CPU
e GPU.

O segundo problema foi a escalabilidade do exemplo original. Vetores grandes alocados
como variaveis automaticas podem exceder a pilha. A solucao foi usar alocacao
dinamica com `malloc` e liberar a memoria ao final de cada programa.

Com a alocacao dinamica, a versao GPU precisou de mapeamento explicito dos vetores,
pois o OpenMP precisa saber quais secoes devem ser copiadas para o dispositivo e
quais devem retornar ao host. Por isso foram adicionadas as clausulas
`map(to : a[0:n], b[0:n])` e `map(from : c[0:n])`.

Tambem foi necessario garantir que a versao GPU realmente executasse com offload. O
script SLURM define `OMP_TARGET_OFFLOAD=MANDATORY`, fazendo a execucao falhar caso
nao exista suporte de GPU, em vez de continuar silenciosamente na CPU.

## Conclusao

A Tarefa 19 foi executada no NPAD com uma versao CPU e uma versao GPU do exercicio
`vadd.c`. As duas versoes produziram resultado correto, com `errors = 0`.

Nos tempos medidos, a GPU nao superou a CPU. O tempo medio da soma foi
`0.108146763s` na CPU e `0.125197220s` na GPU, resultando em speedup de `0.864x`.
Isso indica que, para esta implementacao e este tamanho de problema, o custo de
offload e transferencia de dados foi maior que o ganho de executar a soma no
dispositivo.

O resultado demonstra um ponto importante da programacao GPU: nem todo codigo
paralelo simples fica automaticamente mais rapido ao usar offload. Operacoes com
pouco calculo por dado transferido, como adicao de vetores, podem ser limitadas pelo
custo de movimentacao de memoria. Para obter melhor aproveitamento da GPU, seria
necessario aumentar a quantidade de trabalho por transferencia, reutilizar dados ja
residentes no dispositivo ou medir regioes maiores mantendo os vetores mapeados por
mais tempo.

## Codigos

### `vadd_cpu.c`

```c
#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#define DEFAULT_N 100000000L
#define DEFAULT_REPEATS 5
#define TOL 1.0e-5f

static long parse_long_arg(int argc, char **argv, int index, long fallback)
{
    if (argc <= index) {
        return fallback;
    }

    char *end = NULL;
    long value = strtol(argv[index], &end, 10);
    if (end == argv[index] || value <= 0) {
        fprintf(stderr, "Invalid numeric argument: %s\n", argv[index]);
        exit(2);
    }
    return value;
}

int main(int argc, char **argv)
{
    const long n = parse_long_arg(argc, argv, 1, DEFAULT_N);
    const int repeats = (int)parse_long_arg(argc, argv, 2, DEFAULT_REPEATS);

    float *a = (float *)malloc((size_t)n * sizeof(float));
    float *b = (float *)malloc((size_t)n * sizeof(float));
    float *c = (float *)malloc((size_t)n * sizeof(float));

    if (a == NULL || b == NULL || c == NULL) {
        fprintf(stderr, "Memory allocation failed for n=%ld\n", n);
        free(a);
        free(b);
        free(c);
        return 1;
    }

    double init_time = -omp_get_wtime();
#pragma omp parallel for
    for (long i = 0; i < n; i++) {
        a[i] = (float)i;
        b[i] = 2.0f * (float)i;
        c[i] = 0.0f;
    }
    init_time += omp_get_wtime();

    double best_compute = 1.0e30;
    double sum_compute = 0.0;

    double warmup = -omp_get_wtime();
#pragma omp parallel for
    for (long i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
    warmup += omp_get_wtime();
    (void)warmup;

    for (int r = 0; r < repeats; r++) {
        double t0 = omp_get_wtime();
#pragma omp parallel for
        for (long i = 0; i < n; i++) {
            c[i] = a[i] + b[i];
        }
        double elapsed = omp_get_wtime() - t0;
        if (elapsed < best_compute) {
            best_compute = elapsed;
        }
        sum_compute += elapsed;
    }

    int errors = 0;
    double verify_time = -omp_get_wtime();
#pragma omp parallel for reduction(+ : errors)
    for (long i = 0; i < n; i++) {
        float expected = a[i] + b[i];
        float limit = TOL * fmaxf(1.0f, fabsf(expected));
        if (fabsf(c[i] - expected) > limit) {
            errors++;
        }
    }
    verify_time += omp_get_wtime();

    printf("cpu,host,%ld,%d,%.9f,%.9f,%.9f,%.9f,%d,%d,%d\n",
           n,
           repeats,
           best_compute,
           sum_compute / repeats,
           init_time,
           verify_time,
           errors,
           omp_get_max_threads(),
           omp_get_num_devices());

    free(a);
    free(b);
    free(c);
    return errors == 0 ? 0 : 1;
}
```

### `vadd_gpu.c`

```c
#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#define DEFAULT_N 100000000L
#define DEFAULT_REPEATS 5
#define TOL 1.0e-5f

static long parse_long_arg(int argc, char **argv, int index, long fallback)
{
    if (argc <= index) {
        return fallback;
    }

    char *end = NULL;
    long value = strtol(argv[index], &end, 10);
    if (end == argv[index] || value <= 0) {
        fprintf(stderr, "Invalid numeric argument: %s\n", argv[index]);
        exit(2);
    }
    return value;
}

int main(int argc, char **argv)
{
    const long n = parse_long_arg(argc, argv, 1, DEFAULT_N);
    const int repeats = (int)parse_long_arg(argc, argv, 2, DEFAULT_REPEATS);

    float *a = (float *)malloc((size_t)n * sizeof(float));
    float *b = (float *)malloc((size_t)n * sizeof(float));
    float *c = (float *)malloc((size_t)n * sizeof(float));

    if (a == NULL || b == NULL || c == NULL) {
        fprintf(stderr, "Memory allocation failed for n=%ld\n", n);
        free(a);
        free(b);
        free(c);
        return 1;
    }

    double init_time = -omp_get_wtime();
#pragma omp parallel for
    for (long i = 0; i < n; i++) {
        a[i] = (float)i;
        b[i] = 2.0f * (float)i;
        c[i] = 0.0f;
    }
    init_time += omp_get_wtime();

    double warmup = -omp_get_wtime();
#pragma omp target map(to : a[0:n], b[0:n]) map(from : c[0:n])
#pragma omp loop
    for (long i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
    warmup += omp_get_wtime();
    (void)warmup;

    double best_compute = 1.0e30;
    double sum_compute = 0.0;

    for (int r = 0; r < repeats; r++) {
        double t0 = omp_get_wtime();
#pragma omp target map(to : a[0:n], b[0:n]) map(from : c[0:n])
#pragma omp loop
        for (long i = 0; i < n; i++) {
            c[i] = a[i] + b[i];
        }
        double elapsed = omp_get_wtime() - t0;
        if (elapsed < best_compute) {
            best_compute = elapsed;
        }
        sum_compute += elapsed;
    }

    int errors = 0;
    double verify_time = -omp_get_wtime();
#pragma omp parallel for reduction(+ : errors)
    for (long i = 0; i < n; i++) {
        float expected = a[i] + b[i];
        float limit = TOL * fmaxf(1.0f, fabsf(expected));
        if (fabsf(c[i] - expected) > limit) {
            errors++;
        }
    }
    verify_time += omp_get_wtime();

    printf("gpu,openmp-target,%ld,%d,%.9f,%.9f,%.9f,%.9f,%d,%d,%d\n",
           n,
           repeats,
           best_compute,
           sum_compute / repeats,
           init_time,
           verify_time,
           errors,
           omp_get_max_threads(),
           omp_get_num_devices());

    free(a);
    free(b);
    free(c);
    return errors == 0 ? 0 : 1;
}
```
