/*
 * Tarefa 8 - Versao 1: rand() + variavel privada + #pragma omp critical
 *
 * Cada thread acumula seus acertos em uma variavel local (privada).
 * Ao final do laco paralelo, usa #pragma omp critical para somar o
 * total local na variavel global 'count'.
 *
 * Usa rand(), que nao e thread-safe: em muitas implementacoes a funcao
 * protege seu estado interno com um mutex global, o que provoca
 * serializacao implicita entre threads e degrada o desempenho.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_rand_critical pi_rand_critical.c -lm
 * Executar: ./pi_rand_critical [N]
 */

#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int main(int argc, char *argv[]) {
    long N = 10000000L;
    if (argc > 1) N = atol(argv[1]);

    long count = 0;
    int threads_used = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        long local_count = 0;

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (long i = 0; i < N; i++) {
            double x = (double)rand() / RAND_MAX;
            double y = (double)rand() / RAND_MAX;
            if (x * x + y * y <= 1.0)
                local_count++;
        }

        #pragma omp critical
        count += local_count;
    }

    double elapsed = omp_get_wtime() - t0;
    double pi      = 4.0 * (double)count / (double)N;
    double error   = fabs(pi - M_PI);

    printf("CONFIG program=rand_critical n=%ld threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%ld total=%ld error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
