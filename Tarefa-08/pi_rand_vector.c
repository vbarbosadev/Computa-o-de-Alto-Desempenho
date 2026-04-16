/*
 * Tarefa 8 - Versao 2: rand() + vetor compartilhado (falso compartilhamento)
 *
 * Cada thread escreve seus acertos em uma posicao exclusiva do vetor
 * 'hits[tid]'. Apos a regiao paralela, um laco serial soma os acertos.
 *
 * Problema de falso compartilhamento (false sharing):
 *   Um cache line tipico tem 64 bytes. Como 'hits' e um array de long
 *   (8 bytes cada), ate 8 posicoes vizinhas compartilham o mesmo cache
 *   line. Quando uma thread modifica hits[tid], invalida a linha inteira
 *   para as demais threads, forcando recargas constantes — mesmo que cada
 *   thread acesse apenas a sua posicao.
 *
 * Usa rand(), que tambem serializa as threads internamente via mutex
 * global do estado do gerador.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_rand_vector pi_rand_vector.c -lm
 * Executar: ./pi_rand_vector [N]
 */

#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define MAX_THREADS 256

int main(int argc, char *argv[]) {
    long N = 10000000L;
    if (argc > 1) N = atol(argv[1]);

    /* vetor compartilhado — posicoes adjacentes no mesmo cache line */
    long hits[MAX_THREADS];
    memset(hits, 0, sizeof(hits));

    int threads_used = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (long i = 0; i < N; i++) {
            double x = (double)rand() / RAND_MAX;
            double y = (double)rand() / RAND_MAX;
            if (x * x + y * y <= 1.0)
                hits[tid]++;   /* false sharing: mesmo cache line que hits[tid±1] */
        }
    }

    /* acumulacao serial apos a regiao paralela */
    long count = 0;
    for (int t = 0; t < threads_used; t++)
        count += hits[t];

    double elapsed = omp_get_wtime() - t0;
    double pi      = 4.0 * (double)count / (double)N;
    double error   = fabs(pi - M_PI);

    printf("CONFIG program=rand_vector n=%ld threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%ld total=%ld error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
