/*
 * Tarefa 8 - Versao 4: rand_r() + vetor compartilhado (falso compartilhamento)
 *
 * Combina o gerador reentrante rand_r() (sem lock interno) com a
 * estrategia de armazenar os acertos em posicoes distintas de um vetor
 * compartilhado 'hits[tid]'.
 *
 * O falso compartilhamento (false sharing) continua presente: posicoes
 * vizinhas do vetor estao no mesmo cache line (64 bytes / 8 bytes por
 * long = 8 posicoes por linha). Cada escrita em hits[tid] invalida a
 * linha para as demais threads, gerando trafego desnecessario de
 * coerencia de cache — mesmo sem nenhuma corrida de dados real.
 *
 * Diferenca em relacao a versao rand_vector:
 *   - rand() foi substituido por rand_r(): o gargalo do mutex global
 *     do RNG desaparece, tornando o efeito do false sharing mais
 *     visivel no perfil de desempenho.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_randr_vector pi_randr_vector.c -lm
 * Executar: ./pi_randr_vector [N]
 */

#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define MAX_THREADS 256

int main(int argc, char *argv[]) {
    long N = 10000000L;
    if (argc > 1) N = atol(argv[1]);

    /* vetor compartilhado — false sharing entre posicoes adjacentes */
    long hits[MAX_THREADS];
    memset(hits, 0, sizeof(hits));

    int threads_used = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();

        /* seed privada por thread */
        unsigned int seed = (unsigned int)(time(NULL)) ^ (unsigned int)(tid * 2654435761u);

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (long i = 0; i < N; i++) {
            double x = (double)rand_r(&seed) / RAND_MAX;
            double y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0)
                hits[tid]++;   /* false sharing: invalida o cache line vizinho */
        }
    }

    /* acumulacao serial apos a regiao paralela */
    long count = 0;
    for (int t = 0; t < threads_used; t++)
        count += hits[t];

    double elapsed = omp_get_wtime() - t0;
    double pi      = 4.0 * (double)count / (double)N;
    double error   = fabs(pi - M_PI);

    printf("CONFIG program=randr_vector n=%ld threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%ld total=%ld error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
