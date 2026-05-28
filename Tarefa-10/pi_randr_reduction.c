/*
 * Tarefa 10 - Versao 5: rand_r() + reduction(+:count)
 *
 * OpenMP gera acumuladores privados e combina os resultados ao final
 * do loop, sem necessidade de critical nem atomic no codigo-fonte.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_randr_reduction pi_randr_reduction.c -lm
 * Executar: ./pi_randr_reduction [N]
 */

#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "portable_rand_r.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int main(int argc, char *argv[]) {
    long N = 10000000L;
    if (argc > 1) {
        N = atol(argv[1]);
    }

    long count       = 0;
    int threads_used = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL))
                          ^ (unsigned int)(omp_get_thread_num() * 2654435761u);

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static) reduction(+:count)
        for (long i = 0; i < N; i++) {
            double x = (double)rand_r(&seed) / (double)RAND_MAX;
            double y = (double)rand_r(&seed) / (double)RAND_MAX;
            if (x * x + y * y <= 1.0) {
                count++;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    double pi      = 4.0 * (double)count / (double)N;
    double error   = fabs(pi - M_PI);

    printf("CONFIG program=reduction n=%ld threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%ld total=%ld error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
